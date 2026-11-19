"""Record each day's forecast (rule version 0.1) before the outcome is known.

WHAT IT DOES
Once a day this script works out, for today and each of the next six days, the
chance that the county's weekly ocean test at the creek mouth (station LM5)
would fail, using the frozen rule in pipeline/forecast_rule.py, and appends
those seven rows to open-data/forecast_log.csv. The log exists so the public can
later see how often the rule was right, and so the rule can be tuned against a
record that was written down in advance.

THE LOG IS APPEND-ONLY
- Rows are only ever added at the end of the file. Nothing here reads a row
  back and rewrites it.
- If rows for today's issue_date are already in the file, nothing is written.
- --date (a back-test of the arithmetic) is refused unless --dry-run is also
  given, so the real log can never be back-dated.
- Any missing or odd value stops the run with a non-zero exit and nothing is
  written.
Nothing in this script says the water is ever safe. The rule gives a chance of
a failed test; a low chance is still a chance.

WHERE THE RAIN COMES FROM
The same place and the same source as pipeline/fetch.py (which builds
weather_daily): Open-Meteo, at the San Pedro Creek watershed point
(37.585, -122.47), daily precipitation_sum, timezone America/Los_Angeles. No
key, and nothing is sent beyond those parameters.
  - Past days: the ERA5 archive endpoint, from 400 days back through yesterday.
    The archive trails real time by several days; days it does not have yet are
    filled from the forecast endpoint's recent past (past_days), which holds
    the model's own estimate for those days.
  - Today and the next six days: the forecast endpoint.
The rain is NOT identical to what a later archive refresh will say; recent
days get revised. That is part of what the log records.

THE INPUTS TO THE RULE
  R3  rain on the target day plus the two days before it. Past days use
      measured (archive) rain, today and later use forecast rain.
      rain3_forecast_mm is the part of R3 that is forecast.
  G   the ground-wetness index for the target day, i.e. as known through the
      day before, rebuilt here with the exact recurrence from
      pipeline/features.py, starting from zero 400 days back:
          F_t = 0.90 F_{t-1} + 0.5 P_t + 0.5 P_{t-1}
          G_t = 0.97 G_{t-1} + 0.10 F_{t-1}
      For a target day ahead of today, the days between are filled with
      forecast rain. The store has a memory of weeks, so 400 days from zero
      leaves only a tiny trace of the starting point.
It does not need the database. If data/pacifica.db happens to be present, the
script compares its ground index with rain_context.ground_idx on the dates
they share and prints the largest difference.

VALUES IN THE FILE
The inputs are rounded first (rain3_mm to 2 decimals, ground_idx to 3), then
chance is computed from the rounded inputs and rounded to 3 decimals, and
level from the rounded chance, so every row can be recomputed from the file
alone with forecast_rule.chance() and forecast_rule.level().

Usage (from the repo root):
    python3 pipeline/forecast_log.py                       # append today's rows
    python3 pipeline/forecast_log.py --dry-run             # print them, write nothing
    python3 pipeline/forecast_log.py --dry-run --date 2026-08-10
        # arithmetic back-test: treats that date as "today". Rain for the
        # "forecast" days is the archived actual, so it is NOT a real forecast.
Needs numpy, pandas and requests (pipeline/requirements.txt).
"""

import argparse
import csv
import io
import math
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))  # find forecast_rule even under python -I
import forecast_rule  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
LOG = ROOT / "open-data" / "forecast_log.csv"

# Same point and parameters as pipeline/fetch.py (fetch_weather).
WX_LAT, WX_LON = 37.585, -122.47
TZ_NAME = "America/Los_Angeles"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HISTORY_DAYS = 400    # rain history, and the days the indices run from zero
PAST_FILL_DAYS = 14   # recent past asked of the forecast endpoint to cover the archive's lag
HORIZON_DAYS = 6      # today plus this many days ahead
BURN_IN_DAYS = 150    # the database comparison skips the first days, where starting from zero shows
MAX_DAILY_MM = 1000.0  # anything above this is treated as a bad value

COLUMNS = ["issued_at_utc", "issue_date", "target_date", "lead_days", "rain3_mm",
           "rain3_forecast_mm", "ground_idx", "chance", "level", "rule_version"]


class LogError(Exception):
    """Anything that must stop the run with nothing written."""


# ------------------------------------------------------------------ rain
def get_json(url, params):
    """GET with a few retries, like fetch.py's CKAN helper. Only the given
    parameters are sent."""
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == 2:
                raise LogError(f"fetch failed: {url}: {e}")
            print(f"    retry {attempt + 1} after {e}", file=sys.stderr)
            time.sleep(5)


def daily_rain(url, extra):
    """Returns {date: mm or None} from an Open-Meteo daily response."""
    params = {"latitude": WX_LAT, "longitude": WX_LON, "daily": "precipitation_sum",
              "timezone": TZ_NAME}
    params.update(extra)
    d = get_json(url, params).get("daily")
    if not d or "time" not in d or "precipitation_sum" not in d:
        raise LogError(f"unexpected response from {url}")
    if len(d["time"]) != len(d["precipitation_sum"]):
        raise LogError(f"mismatched lengths in response from {url}")
    return {date.fromisoformat(t): v for t, v in zip(d["time"], d["precipitation_sum"])}


def get_rain(issue):
    """Daily rain (mm) for every day from issue - 400 through issue + 6.
    Raises LogError if any day is missing or implausible."""
    start, last = issue - timedelta(days=HISTORY_DAYS), issue + timedelta(days=HORIZON_DAYS)
    real_yesterday = datetime.now(ZoneInfo(TZ_NAME)).date() - timedelta(days=1)

    archive = daily_rain(ARCHIVE_URL, {"start_date": start.isoformat(),
                                       "end_date": min(last, real_yesterday).isoformat()})
    rain = {d: v for d, v in archive.items() if v is not None and start <= d <= last}
    wanted = [start + timedelta(days=i) for i in range((last - start).days + 1)]
    missing = [d for d in wanted if d not in rain]

    filled = []
    if missing:
        fc = daily_rain(FORECAST_URL, {"past_days": PAST_FILL_DAYS,
                                       "forecast_days": HORIZON_DAYS + 1})
        for d in missing:
            if fc.get(d) is not None:
                rain[d] = fc[d]
                filled.append(d)
        missing = [d for d in wanted if d not in rain]
    if missing:
        raise LogError(f"rain missing for {len(missing)} day(s), first {missing[0]}, last {missing[-1]}")

    for d in wanted:
        v = rain[d]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) \
                or v < 0 or v > MAX_DAILY_MM:
            raise LogError(f"implausible rain value {v!r} on {d}")
    past_filled = [d for d in filled if d < issue]
    print(f"rain: {len(wanted)} days {start} .. {last}; "
          f"{len(past_filled)} recent past day(s) filled from the forecast endpoint"
          + (f" ({past_filled[0]} .. {past_filled[-1]})" if past_filled else ""))
    return {d: float(rain[d]) for d in wanted}


# ------------------------------------------------------------------ indices
def ground_index(rain, days):
    """The recurrence from pipeline/features.py, from zero on days[0].
    Returns ({date: flow_idx}, {date: ground_idx}); the value on a date is
    G_t, built from rain through the day before."""
    flow, ground = {}, {}
    F = G = 0.0
    prev_rain = 0.0
    for d in days:
        rain_today = rain[d]
        Fprev = F
        F = 0.90 * F + 0.5 * rain_today + 0.5 * prev_rain
        G = 0.97 * G + 0.10 * Fprev
        flow[d], ground[d] = F, G
        prev_rain = rain_today
    return flow, ground


def compare_with_database(ground):
    """If data/pacifica.db is present, compare with rain_context.ground_idx."""
    if not DB.exists():
        print("ground index check: no database here, skipped")
        return
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT date, ground_idx FROM rain_context").fetchall()
    except sqlite3.Error as e:
        print(f"ground index check: could not read rain_context ({e}), skipped")
        return
    finally:
        con.close()
    best_abs = best_rel = None
    n = 0
    for ds, g_db in rows:
        d = date.fromisoformat(str(ds)[:10])
        if d not in ground or g_db is None or d < min(ground) + timedelta(days=BURN_IN_DAYS):
            continue
        n += 1
        diff = abs(ground[d] - g_db)
        if best_abs is None or diff > best_abs[0]:
            best_abs = (diff, d, ground[d], g_db)
        if g_db >= 1.0:  # the rule floors G at 1, so smaller values do not matter
            rel = diff / g_db
            if best_rel is None or rel > best_rel[0]:
                best_rel = (rel, d, ground[d], g_db)
    if not n:
        print("ground index check: no dates in common with rain_context")
        return
    print(f"ground index check vs rain_context.ground_idx on {n} shared dates "
          f"(skipping the first {BURN_IN_DAYS} days, which still carry the zero start):")
    print(f"  largest absolute difference {best_abs[0]:.4f} on {best_abs[1]} "
          f"(here {best_abs[2]:.3f}, database {best_abs[3]:.3f})")
    if best_rel:
        print(f"  largest relative difference {best_rel[0]:.2%} on {best_rel[1]} "
              f"(here {best_rel[2]:.3f}, database {best_rel[3]:.3f}), dates with database value >= 1")


# ------------------------------------------------------------------ forecast rows
def build_rows(issue, issued_at, rain, ground):
    rows = []
    for lead in range(HORIZON_DAYS + 1):
        target = issue + timedelta(days=lead)
        window = [target - timedelta(days=k) for k in range(3)]
        rain3 = round(sum(rain[d] for d in window), 2)
        rain3_fc = round(sum(rain[d] for d in window if d >= issue), 2)
        g = round(ground[target], 3)
        p = round(float(forecast_rule.chance(rain3, g)), 3)
        values = [issued_at, issue.isoformat(), target.isoformat(), lead, rain3, rain3_fc, g,
                  p, forecast_rule.level(p), forecast_rule.VERSION]
        for name, v in zip(COLUMNS, values):
            if v is None or (isinstance(v, float) and not math.isfinite(v)) or v == "":
                raise LogError(f"missing value for {name} on {target}")
        if not 0.0 <= p <= 1.0:
            raise LogError(f"chance out of range on {target}: {p}")
        rows.append(values)
    return rows


def format_rows(rows):
    """The rows exactly as they would be written, as CSV text."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in rows:
        w.writerow([f"{v:.3f}" if name in ("chance", "ground_idx")
                    else f"{v:.2f}" if name in ("rain3_mm", "rain3_forecast_mm") else v
                    for name, v in zip(COLUMNS, r)])
    return buf.getvalue()


# ------------------------------------------------------------------ the log
def check_existing_log(issue):
    """Returns True if rows for this issue_date are already in the log.
    Refuses (LogError) if the file is not in the expected shape."""
    if not LOG.exists() or LOG.stat().st_size == 0:
        return False
    text = LOG.read_bytes().decode("utf-8")
    if not text.endswith("\n"):
        raise LogError(f"{LOG.name} does not end with a newline; not appending")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if header != COLUMNS:
        raise LogError(f"{LOG.name} header is not the expected one; not appending")
    issue_dates = {r[1] for r in reader if r}
    if any(d > issue.isoformat() for d in issue_dates):
        raise LogError(f"{LOG.name} already has an issue_date after {issue}; not appending")
    return issue.isoformat() in issue_dates


def append_rows(text):
    """Add rows at the end of the file (the header first if the file is new or
    empty). One write, then flushed to disk."""
    new_file = not LOG.exists() or LOG.stat().st_size == 0
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8", newline="") as f:
        if new_file:
            f.write(",".join(COLUMNS) + "\n")
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Append today's forecast rows to open-data/forecast_log.csv.")
    ap.add_argument("--dry-run", action="store_true", help="print the rows, write nothing")
    ap.add_argument("--date", help="YYYY-MM-DD: act as if this were today (only with --dry-run)")
    args = ap.parse_args()

    now_utc = datetime.now(timezone.utc)
    today = now_utc.astimezone(ZoneInfo(TZ_NAME)).date()
    if args.date and not args.dry_run:
        ap.error("--date is only allowed together with --dry-run (the log is never back-dated)")
    try:
        issue = date.fromisoformat(args.date) if args.date else today
    except ValueError:
        ap.error("--date must look like YYYY-MM-DD")
    if issue > today:
        ap.error("--date cannot be in the future")

    try:
        if not args.dry_run and check_existing_log(issue):
            print(f"{LOG.name} already has rows for issue_date {issue}; nothing written.")
            return 0
        rain = get_rain(issue)
        days = sorted(rain)
        _, ground = ground_index(rain, days)
        compare_with_database(ground)
        issued_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = build_rows(issue, issued_at, rain, ground)
        text = format_rows(rows)
    except LogError as e:
        print(f"ERROR: {e}. Nothing written.", file=sys.stderr)
        return 1

    if args.dry_run:
        if args.date:
            print(f"NOTE: acting as {issue}. Rain from that date on is archived actual rain, "
                  "not a forecast; this is a check of the arithmetic only.")
        print("DRY RUN, nothing written. Rows that would be appended:")
        print(",".join(COLUMNS))
        print(text, end="")
        return 0

    try:
        if check_existing_log(issue):  # checked again just before writing
            print(f"{LOG.name} already has rows for issue_date {issue}; nothing written.")
            return 0
        append_rows(text)
    except (LogError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Appended {len(rows)} rows for issue_date {issue} to {LOG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
