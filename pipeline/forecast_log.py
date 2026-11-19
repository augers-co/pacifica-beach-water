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

THE WEATHER FORECAST AS ISSUED (so that later tuning can tell "the rule was
wrong" from "the weather forecast was wrong", and can try other inputs)
Besides the two rule inputs, each row keeps what the services said when the row
was written:
  - the three daily rain values that add up to rain3_mm (rain_day0_mm is the
    target day, day1 the day before, day2 two days before), each with where it
    came from: "archive" (the ERA5 archive), "recent" (the forecast service's
    estimate for a past day the archive does not have yet) or "forecast";
  - the forecast for the target day from the same forecast call: chance of
    rain, mean / highest / lowest temperature, sunshine, top wind speed and
    wind direction (from the forecast endpoint's daily variables);
  - the sea state for the target day from Open-Meteo's marine forecast at the
    sea point the service returns for 37.60 N, 122.51 W (just offshore of
    Linda Mar beach): highest wave, longest wave period, wave direction, and
    the day's mean sea temperature from the hourly values. The point actually
    used is recorded in sea_lat and sea_lon;
  - weather_source, a fixed text naming the services (the responses do not
    name the forecast model).
Only the two rule inputs are required. If an extra weather or sea value is
missing, or the marine call fails, those cells are left blank, a note goes to
stderr, and the forecast is still logged. A blank cell means no value.

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
The inputs are rounded first (each daily rain and rain3_mm to 2 decimals,
ground_idx to 3; rain3_mm is the sum of the three rounded daily values), then
chance is computed from the rounded inputs and rounded to 3 decimals, and
level from the rounded chance, so every row can be recomputed from the file
alone with forecast_rule.chance() and forecast_rule.level(). Extra values
use fixed formats: temperatures, wind speed, wave period and sea temperature to
1 decimal; sunshine and wave height to 2; chance of rain and the directions in
whole numbers.

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
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
SEA_LAT, SEA_LON = 37.60, -122.51   # just offshore of Linda Mar beach
WEATHER_SOURCE = "Open-Meteo forecast API (best match, model not named in response); Open-Meteo marine API"

HISTORY_DAYS = 400    # rain history, and the days the indices run from zero
PAST_FILL_DAYS = 14   # recent past asked of the forecast endpoint to cover the archive's lag
HORIZON_DAYS = 6      # today plus this many days ahead
BURN_IN_DAYS = 150    # the database comparison skips the first days, where starting from zero shows
MAX_DAILY_MM = 1000.0  # anything above this is treated as a bad value

COLUMNS = ["issued_at_utc", "issue_date", "target_date", "lead_days", "rain3_mm",
           "rain3_forecast_mm", "ground_idx", "chance", "level", "rule_version",
           "rain_day0_mm", "rain_day1_mm", "rain_day2_mm",
           "rain_day0_src", "rain_day1_src", "rain_day2_src",
           "rain_prob_max_pct", "temp_mean_c", "temp_max_c", "temp_min_c", "sun_mj_m2",
           "wind_max_kmh", "wind_dir_deg",
           "wave_height_max_m", "wave_period_max_s", "wave_dir_deg", "sea_temp_c",
           "sea_lat", "sea_lon", "weather_source"]
FIRST_REQUIRED = 10   # the first ten columns (the rule's inputs and result) must have values

# Optional forecast values: column -> (Open-Meteo daily variable, decimals).
FORECAST_VARS = {
    "rain_prob_max_pct": ("precipitation_probability_max", 0),
    "temp_mean_c": ("temperature_2m_mean", 1),
    "temp_max_c": ("temperature_2m_max", 1),
    "temp_min_c": ("temperature_2m_min", 1),
    "sun_mj_m2": ("shortwave_radiation_sum", 2),
    "wind_max_kmh": ("wind_speed_10m_max", 1),
    "wind_dir_deg": ("wind_direction_10m_dominant", 0),
}
MARINE_VARS = {
    "wave_height_max_m": ("wave_height_max", 2),
    "wave_period_max_s": ("wave_period_max", 1),
    "wave_dir_deg": ("wave_direction_dominant", 0),
}


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


def daily_values(url, extra, variables, hourly=None):
    """Returns ({variable: {date: value or None}}, response) from an Open-Meteo
    response. Only coordinates and parameters are sent."""
    params = {"latitude": WX_LAT, "longitude": WX_LON, "daily": ",".join(variables),
              "timezone": TZ_NAME}
    params.update(extra)
    resp = get_json(url, params)
    d = resp.get("daily")
    if not d or "time" not in d or any(v not in d for v in variables):
        raise LogError(f"unexpected response from {url}")
    out = {}
    for v in variables:
        if len(d[v]) != len(d["time"]):
            raise LogError(f"mismatched lengths in response from {url}")
        out[v] = {date.fromisoformat(t): x for t, x in zip(d["time"], d[v])}
    return out, resp


def get_rain(issue, forecast_vars):
    """Daily rain (mm) and where each day came from, for every day from
    issue - 400 through issue + 6. Returns ({date: mm}, {date: source}).
    Raises LogError if any day is missing or implausible. forecast_vars is the
    forecast call's result ({variable: {date: value}}) or None if that call
    failed."""
    start, last = issue - timedelta(days=HISTORY_DAYS), issue + timedelta(days=HORIZON_DAYS)
    real_yesterday = datetime.now(ZoneInfo(TZ_NAME)).date() - timedelta(days=1)

    archive, _ = daily_values(ARCHIVE_URL, {"start_date": start.isoformat(),
                                            "end_date": min(last, real_yesterday).isoformat()},
                              ["precipitation_sum"])
    rain, src = {}, {}
    wanted = [start + timedelta(days=i) for i in range((last - start).days + 1)]
    for d, v in archive["precipitation_sum"].items():
        if v is not None and start <= d <= last:
            rain[d], src[d] = v, "archive"
    missing = [d for d in wanted if d not in rain]

    if missing:
        if forecast_vars is None:
            raise LogError("the forecast call failed and the archive does not cover every day")
        fc = forecast_vars["precipitation_sum"]
        for d in missing:
            if fc.get(d) is not None:
                rain[d] = fc[d]
                src[d] = "forecast" if d >= issue else "recent"
        missing = [d for d in wanted if d not in rain]
    if missing:
        raise LogError(f"rain missing for {len(missing)} day(s), first {missing[0]}, last {missing[-1]}")

    for d in wanted:
        v = rain[d]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) \
                or v < 0 or v > MAX_DAILY_MM:
            raise LogError(f"implausible rain value {v!r} on {d}")
    recent = [d for d in wanted if src[d] == "recent"]
    print(f"rain: {len(wanted)} days {start} .. {last}; "
          f"{len(recent)} recent past day(s) filled from the forecast endpoint"
          + (f" ({recent[0]} .. {recent[-1]})" if recent else ""))
    return {d: float(rain[d]) for d in wanted}, src


def get_forecast():
    """One call to the forecast endpoint: rain plus the optional daily
    variables. Returns {variable: {date: value}}, or None if the call failed
    (get_rain decides whether that matters)."""
    variables = ["precipitation_sum"] + [v for v, _ in FORECAST_VARS.values()]
    try:
        out, _ = daily_values(FORECAST_URL, {"past_days": PAST_FILL_DAYS,
                                             "forecast_days": HORIZON_DAYS + 1}, variables)
        return out
    except LogError as e:
        print(f"note: forecast call failed ({e}); extra weather cells will be blank", file=sys.stderr)
        return None


def get_marine():
    """Sea state from the marine forecast: ({column: {date: value}}, (lat, lon)
    the service used). Never raises; on any trouble returns ({}, None) and says
    so on stderr."""
    try:
        params = {"latitude": SEA_LAT, "longitude": SEA_LON, "timezone": TZ_NAME,
                  "daily": ",".join(v for v, _ in MARINE_VARS.values()),
                  "hourly": "sea_surface_temperature",
                  "past_days": PAST_FILL_DAYS, "forecast_days": HORIZON_DAYS + 1}
        resp = get_json(MARINE_URL, params)
        d, h = resp["daily"], resp["hourly"]
        out = {}
        for col, (var, _) in MARINE_VARS.items():
            out[col] = {date.fromisoformat(t): x for t, x in zip(d["time"], d[var])}
        by_day = {}
        for t, x in zip(h["time"], h["sea_surface_temperature"]):
            if x is not None:
                by_day.setdefault(date.fromisoformat(t[:10]), []).append(x)
        out["sea_temp_c"] = {day: sum(v) / len(v) for day, v in by_day.items() if len(v) >= 20}
        return out, (float(resp["latitude"]), float(resp["longitude"]))
    except (LogError, KeyError, TypeError, ValueError) as e:
        print(f"note: marine call failed ({e}); sea cells will be blank", file=sys.stderr)
        return {}, None


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
def fixed(v, decimals):
    """A number as fixed-decimal text, or "" if there is no usable value."""
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return ""
    return f"{v:.{decimals}f}"


def build_rows(issue, issued_at, rain, src, ground, fc, marine, sea_point):
    """Seven rows of text cells, in COLUMNS order. The first ten columns must
    have values; the extra weather and sea cells may be blank (noted on stderr)."""
    rows, blanks = [], []
    for lead in range(HORIZON_DAYS + 1):
        target = issue + timedelta(days=lead)
        window = [target - timedelta(days=k) for k in range(3)]
        day_mm = [round(rain[d], 2) for d in window]
        rain3 = round(sum(day_mm), 2)
        rain3_fc = round(sum(rain[d] for d in window if d >= issue), 2)
        g = round(ground[target], 3)
        p = round(float(forecast_rule.chance(rain3, g)), 3)
        required = [issued_at, issue.isoformat(), target.isoformat(), lead, rain3, rain3_fc, g,
                    p, forecast_rule.level(p), forecast_rule.VERSION]
        for name, v in zip(COLUMNS, required):
            if v is None or (isinstance(v, float) and not math.isfinite(v)) or v == "":
                raise LogError(f"missing value for {name} on {target}")
        if not 0.0 <= p <= 1.0:
            raise LogError(f"chance out of range on {target}: {p}")
        row = [issued_at, issue.isoformat(), target.isoformat(), str(lead), f"{rain3:.2f}",
               f"{rain3_fc:.2f}", f"{g:.3f}", f"{p:.3f}", forecast_rule.level(p),
               forecast_rule.VERSION]
        row += [f"{v:.2f}" for v in day_mm] + [src[d] for d in window]
        for col, (var, nd) in FORECAST_VARS.items():
            row.append(fixed((fc or {}).get(var, {}).get(target), nd))
        for col in ("wave_height_max_m", "wave_period_max_s", "wave_dir_deg", "sea_temp_c"):
            nd = MARINE_VARS[col][1] if col in MARINE_VARS else 1
            row.append(fixed(marine.get(col, {}).get(target), nd))
        row += [f"{sea_point[0]:.3f}" if sea_point else "", f"{sea_point[1]:.3f}" if sea_point else "",
                WEATHER_SOURCE]
        assert len(row) == len(COLUMNS)
        empty = [c for c, v in zip(COLUMNS, row) if v == ""]
        if empty:
            blanks.append(f"{target}: {', '.join(empty)}")
        rows.append(row)
    if blanks:
        print("note: blank (no value available) cells, left empty:", file=sys.stderr)
        for b in blanks:
            print(f"  {b}", file=sys.stderr)
    return rows


def format_rows(rows):
    """The rows exactly as they would be written, as CSV text."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
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
        issued_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        fc = get_forecast()
        rain, src = get_rain(issue, fc)
        days = sorted(rain)
        _, ground = ground_index(rain, days)
        compare_with_database(ground)
        marine, sea_point = get_marine()
        rows = build_rows(issue, issued_at, rain, src, ground, fc, marine, sea_point)
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
