"""Write small JSON files that a web page or a phone app can read: docs/api/v1/.

WHAT IT WRITES (GitHub Pages serves docs/, so these are public at
https://augers-co.github.io/pacifica-beach-water/api/v1/)
  Daily (the default; no database needed):
    forecast.json        the latest issue in open-data/forecast_log.csv: seven
                         days, each with its level, chance and inputs
    levels.json          the four levels, their chance ranges and the odds
                         seen for each in the 2022-2026 record (held out)
    meta.json            what each file holds, links, and a note on the address
  Weekly (--weekly; needs data/pacifica.db, and skips cleanly without it):
    latest_results.json  the most recent county result for each county series
                         the public page already shows
    track_record.json    each scored test from open-data/forecast_scored.csv
                         beside the forecasts logged for it, with a summary
The two modes write different files, so the daily and weekly workflows never
commit the same file and their pushes cannot collide.

Every file carries "schema": 1, "generated_at" (UTC) and "rule_version".
Within schema 1, fields are only ever added, never renamed or removed. Output
is deterministic (fixed key order and decimals, trailing newline). A file is
left untouched when nothing but generated_at would change, so a re-run makes
no commit.

THE FORECAST IS EXPERIMENTAL. It is not an official advisory, none of the
levels means the water is safe, and it estimates the chance that a county test
fails; it does not predict illness.

Run from the repo root:
    python3 pipeline/export_api.py                     # daily files
    python3 pipeline/export_api.py --weekly            # weekly files
    python3 pipeline/export_api.py --today 2026-11-20  # check only: act as if
        # it were that Pacific date (to see "stale" work); writes nothing
Needs pandas (and numpy, through forecast_rule).
"""

import argparse
import csv
import json
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # find forecast_rule even under python -I
import forecast_rule as fr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
OPEN = ROOT / "open-data"
LOG = OPEN / "forecast_log.csv"
SCORED = OPEN / "forecast_scored.csv"
FROZEN = OPEN / "rule_v0_1_worked.csv"
MODEL = ROOT / "models" / "forecast_v0_1.json"
OUT = ROOT / "docs" / "api" / "v1"

SCHEMA = 1
TZ_NAME = "America/Los_Angeles"
BASE_URL = "https://augers-co.github.io/pacifica-beach-water/api/v1/"
REPO_URL = "https://github.com/augers-co/pacifica-beach-water"
COUNTY_ADVISORIES = "https://www.smchealth.org/beaches"

LEVEL_KEYS = {"lower than usual": "lower", "usual": "usual", "high": "high", "very high": "very_high"}
CAVEATS = [
    "This forecast is experimental.",
    "It is not an official advisory.",
    "None of the levels means the water is safe.",
    "It estimates the chance that a county test fails; it does not predict illness.",
]
# "beyond_experience" uses two range checks against the frozen fitted record
# (see beyond()). A third check, "rain3 over 10 mm with ground index under 50",
# was considered and left out: 5 of the 243 fitted tests have exactly that.
WEATHER_TEXT = {"rain_day0_src", "rain_day1_src", "rain_day2_src", "weather_source"}
SCORED_LEADS = (0, 1, 3)
SAMPLED_BY = "San Mateo County Environmental Health"

# The county series the public page (pipeline/export_ledger.py) already shows,
# with the same station and analyte filters, and the standard the page draws
# for each. The Coalition and Surfrider series on the page are left out here:
# pipeline/export_open.py holds them back from reuse.
SERIES = [
    dict(key="lm5_enterococcus", station="Beach at creek mouth (county station LM5)",
         station_like="%#5%", analyte="enterococcus", analyte_like="%Enterococcus%", standard=104),
    dict(key="lm5_e_coli", station="Beach at creek mouth (county station LM5)",
         station_like="%#5%", analyte="E. coli", analyte_like="%E. coli%", standard=320),
    dict(key="creek_e_coli", station="San Pedro Creek (county creek station)",
         station_like="%San Pedro Creek%", analyte="E. coli", analyte_like="%E. coli%", standard=320),
    dict(key="creek_enterococcus", station="San Pedro Creek (county creek station)",
         station_like="%San Pedro Creek%", analyte="enterococcus", analyte_like="%Enterococcus%", standard=110),
]


# ------------------------------------------------------------------ helpers
def number(text):
    """A number from a CSV cell (int if it has no decimal point), or None if blank."""
    if text is None or text == "":
        return None
    return float(text) if "." in text else int(text)


def model_levels():
    """{level name: held-out row} from the model file, in the rule's order."""
    model = json.loads(MODEL.read_text())
    return {r["level"]: r for r in model["held_out"]["level_table"]}


def header(rule_version, now):
    return {"schema": SCHEMA, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rule_version": rule_version}


def write(name, data, dry_run=False):
    """Write one file, unless nothing but generated_at would change."""
    path = OUT / name
    text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if dry_run:
        print(f"--- {name} (not written)")
        print(text, end="")
        return
    try:
        old = json.loads(path.read_text())
    except (OSError, ValueError):
        old = None
    if old is not None and {**old, "generated_at": None} == {**json.loads(text), "generated_at": None}:
        print(f"unchanged {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


# ------------------------------------------------------------------ daily files
def fitted_range():
    """The largest rain3 and ground index among the tests the rule was fitted on."""
    f = pd.read_csv(FROZEN, float_precision="round_trip")
    return float(f.rain3_mm.max()), float(f.ground_idx.max()), len(f)


def beyond(rain3, ground, rng):
    max_rain3, max_ground, n = rng
    reasons = []
    if rain3 > max_rain3:
        reasons.append(f"Rain over three days ({rain3:.1f} mm) is more than in any of the {n} tests "
                       f"the rule was fitted on (most was {max_rain3:.1f} mm).")
    if ground > max_ground:
        reasons.append(f"The ground index ({ground:.1f}) is higher than in any of the {n} tests "
                       f"the rule was fitted on (highest was {max_ground:.1f}).")
    return bool(reasons), (" ".join(reasons) or None)


def forecast_file(today, now):
    with open(LOG, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"{LOG.relative_to(ROOT)} has no rows; no forecast to export.")
    issue = max(r["issue_date"] for r in rows)
    latest = sorted((r for r in rows if r["issue_date"] == issue), key=lambda r: int(r["lead_days"]))
    if len(latest) != 7 or [int(r["lead_days"]) for r in latest] != list(range(7)):
        raise SystemExit(f"issue {issue} does not have exactly one row for each lead 0 to 6")
    versions = {r["rule_version"] for r in latest}
    if len(versions) != 1:
        raise SystemExit(f"issue {issue} mixes rule versions {sorted(versions)}")
    odds = model_levels()
    rng = fitted_range()
    weather_cols = list(latest[0].keys())[list(latest[0].keys()).index("rule_version") + 1:]

    days = []
    for r in latest:
        rain3, ground = float(r["rain3_mm"]), float(r["ground_idx"])
        out_of_range, reason = beyond(rain3, ground, rng)
        name = r["level"]
        days.append({
            "date": r["target_date"],
            "lead_days": int(r["lead_days"]),
            "level": name,
            "level_key": LEVEL_KEYS[name],
            "chance": round(float(r["chance"]), 3),
            "fail_share": round(odds[name]["pct_fail"], 3),
            "far_over_share": round(odds[name]["pct_far_over"], 3),
            "inputs": {"rain3_mm": round(rain3, 2), "rain3_forecast_mm": round(float(r["rain3_forecast_mm"]), 2),
                       "ground_idx": round(ground, 3)},
            "weather": {c: (r[c] or None) if c in WEATHER_TEXT else number(r[c]) for c in weather_cols},
            "beyond_experience": out_of_range,
            "beyond_reason": reason,
        })
    return {**header(versions.pop(), now),
            "issue_date": issue,
            "issued_at_utc": latest[0]["issued_at_utc"],
            "stale": issue != today.isoformat(),
            "caveats": CAVEATS,
            "days": days}


def levels_file(now):
    odds = model_levels()
    out = []
    for i, (name, lo) in enumerate(fr.LEVELS):
        hi = fr.LEVELS[i + 1][1] if i + 1 < len(fr.LEVELS) else 1.0
        o = odds[name]
        out.append({"key": LEVEL_KEYS[name], "name": name, "chance_min": lo, "chance_max": hi,
                    "tests": o["n"], "fail_share": round(o["pct_fail"], 3),
                    "far_over_share": round(o["pct_far_over"], 3)})
    return {**header(fr.VERSION, now),
            "standard": {"analyte": "enterococcus", "unit": "MPN per 100 mL", "single_sample": fr.STANDARD,
                         "far_over_above": fr.FAR_OVER,
                         "text": "A test fails when it is over 104 MPN per 100 mL (single sample); "
                                 "far over means above 312."},
            "levels_note": "chance_min is included in the level and chance_max is not (except 1.0). "
                           "tests, fail_share and far_over_share come from the 2022-2026 record, each "
                           "year predicted from a fit on the other years; they are not a promise.",
            "levels": out,
            "caveats": CAVEATS}


def meta_file(now):
    return {**header(fr.VERSION, now),
            "files": [
                {"name": "forecast.json", "updated": "daily",
                 "holds": "The latest forecast: seven days, each with its level, chance, inputs and logged weather."},
                {"name": "levels.json", "updated": "when the rule changes",
                 "holds": "The four levels, their chance ranges, the odds seen for each, the standard and the caveats."},
                {"name": "meta.json", "updated": "when the files change",
                 "holds": "This list, the links, and the note on the address."},
                {"name": "latest_results.json", "updated": "weekly",
                 "holds": "The most recent county test result for each county series the project's page shows."},
                {"name": "track_record.json", "updated": "weekly",
                 "holds": "Each county test that had a forecast logged for it, the forecasts, and a summary by level."},
            ],
            "links": {"repository": REPO_URL,
                      "open_data_guide": REPO_URL + "/tree/main/open-data",
                      "api_guide": REPO_URL + "/tree/main/docs/api",
                      "county_beach_advisories": COUNTY_ADVISORIES},
            "base_address": BASE_URL,
            "address_note": "The address of these files may move to another domain later. "
                            "Keep the base address configurable rather than built into your code.",
            "caveats": CAVEATS}


# ------------------------------------------------------------------ weekly files
def latest_results_file(con, today, now):
    out = []
    for s in SERIES:
        df = pd.read_sql("""SELECT SampleDate, Result FROM ceden_raw
                            WHERE StationName LIKE ? AND Analyte LIKE ?""",
                         con, params=[s["station_like"], s["analyte_like"]])
        df["date"] = pd.to_datetime(df.SampleDate).dt.tz_localize(None).dt.normalize()
        df["v"] = pd.to_numeric(df.Result, errors="coerce")
        df = df.dropna(subset=["v"]).groupby("date", as_index=False).v.max().sort_values("date")
        if df.empty:
            continue
        last = df.iloc[-1]
        d = last.date.date()
        v = float(last.v)
        out.append({"series": s["key"], "station": s["station"], "sampled_by": SAMPLED_BY,
                    "analyte": s["analyte"], "date": d.isoformat(),
                    "result_mpn": int(v) if v.is_integer() else round(v, 1),
                    "unit": "MPN per 100 mL", "standard_mpn": s["standard"],
                    "compared_to_standard": "over" if v > s["standard"] else "under",
                    "days_old": (today - d).days})
    return {**header(fr.VERSION, now),
            "note": "County results reach the state's public database weeks after the sample, so these "
                    "are not current conditions. For current postings see the county's beach page.",
            "county_beach_advisories": COUNTY_ADVISORIES,
            "results": out,
            "caveats": CAVEATS}


def track_record_file(now):
    base = {**header(fr.VERSION, now)}
    if not SCORED.exists():
        return {**base, "note": "No county results have arrived yet for a forecast date.",
                "tests": [], "summary": [], "caveats": CAVEATS}
    with open(SCORED, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {**base, "note": "No county results have arrived yet for a forecast date.",
                "tests": [], "summary": [], "caveats": CAVEATS}
    tests = []
    for r in rows:
        v = float(r["result_mpn"])
        fc = {}
        for k in SCORED_LEADS:
            name = r[f"level_lead{k}"]
            fc[f"lead{k}"] = ({"level": name, "level_key": LEVEL_KEYS[name],
                               "chance": round(float(r[f"chance_lead{k}"]), 3)} if name else None)
        tests.append({"date": r["target_date"], "result_mpn": int(v) if v.is_integer() else round(v, 1),
                      "compared_to_standard": "over" if v > fr.STANDARD else "under",
                      "far_over": v > fr.FAR_OVER, "forecasts": fc})
    odds = model_levels()
    summary = []
    for k in SCORED_LEADS:
        for name, _ in fr.LEVELS:
            g = [t for t in tests if t["forecasts"][f"lead{k}"] and t["forecasts"][f"lead{k}"]["level"] == name]
            over = sum(t["compared_to_standard"] == "over" for t in g)
            summary.append({"lead_days": k, "level": name, "level_key": LEVEL_KEYS[name],
                            "tests": len(g), "over": over,
                            "over_share": round(over / len(g), 3) if g else None,
                            "stated_fail_share": round(odds[name]["pct_fail"], 3),
                            "stated_tests": odds[name]["n"]})
    return {**base, "note": "Each county test that had a forecast logged for it. The stated shares come "
                            "from the 2022-2026 record; with few tests, the shares here will swing a lot.",
            "tests": tests, "summary": summary, "caveats": CAVEATS}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Write the JSON files in docs/api/v1/.")
    ap.add_argument("--weekly", action="store_true", help="write the weekly files (needs data/pacifica.db)")
    ap.add_argument("--today", help="check only: act as if this were the Pacific date (YYYY-MM-DD); writes nothing")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo(TZ_NAME)).date()
    dry = bool(args.today)
    if args.today:
        try:
            today = date.fromisoformat(args.today)
        except ValueError:
            ap.error("--today must look like YYYY-MM-DD")

    if not args.weekly:
        write("forecast.json", forecast_file(today, now), dry)
        write("levels.json", levels_file(now), dry)
        write("meta.json", meta_file(now), dry)
        return 0

    if not DB.exists():
        print(f"No database at {DB.relative_to(ROOT)}; the weekly files need it. Skipped, nothing written.")
        return 0
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        latest = latest_results_file(con, today, now)
    finally:
        con.close()
    write("latest_results.json", latest, dry)
    write("track_record.json", track_record_file(now), dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
