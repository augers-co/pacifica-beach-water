"""Write small JSON files that a web page or a phone app can read: docs/api/v1/.

WHAT IT WRITES (GitHub Pages serves docs/, so these are public at
https://augers-co.github.io/pacifica-beach-water/api/v1/)
  Daily (the default; no database needed):
    forecast.json        the latest issue in open-data/forecast_log.csv: seven
                         days, each with its level, chance and inputs, how each
                         input moves the rule's chance, and the ground index
                         beside its normal for the date
    conditions.json      rain, the two wetness indexes and the estimated creek
                         temperature for the 13 days before today, today and
                         the 6 days after, plus the last 30 days' rain and
                         storms. Fetched from Open-Meteo by this script (as
                         pipeline/forecast_log.py does); if the fetch fails the
                         old file is left as it is and the run still succeeds
    levels.json          the four levels, their chance ranges and the odds
                         seen for each in the 2022-2026 record (held out)
    meta.json            what each file holds, links, and a note on the address
  Weekly (--weekly; needs data/pacifica.db, and skips cleanly without it):
    latest_results.json  the most recent county result for each county series
                         the public page already shows, the last eight county
                         ocean tests, and the latest Surfrider result at the
                         creek mouth (latest only; Surfrider's data is not
                         redistributed here, see bwtf.surfrider.org)
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
import forecast_log as fl  # noqa: E402  (the same Open-Meteo calls and index recurrence)

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
OPEN = ROOT / "open-data"
LOG = OPEN / "forecast_log.csv"
SCORED = OPEN / "forecast_scored.csv"
FROZEN = OPEN / "rule_v0_1_worked.csv"
DAILY_CSV = OPEN / "daily_rain_and_ground.csv"
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
COUNTY_SOURCE = "https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results"

# Surfrider's creek-mouth site. Only the latest result is published here; the
# standard is the freshwater 110 the public page already uses for this series
# (docs/inferences.md section 8: the brackish mouth is judged as fresh water).
SURFRIDER = dict(key="surfrider_creek_mouth_enterococcus",
                 station="Beach at creek mouth (Surfrider site Linda Mar Beach/San Pedro Creek)",
                 site_name="Linda Mar Beach/San Pedro Creek",
                 sampled_by="Surfrider Foundation Blue Water Task Force, San Mateo County chapter",
                 source_url="https://bwtf.surfrider.org/", analyte="enterococcus", standard=110)
RECENT_COUNTY_TESTS = 8

# Definitions used by the new fields (see docs/api/README.md).
HISTORY_BEFORE, HISTORY_AFTER = 13, 6      # conditions.json: 13 days before today .. 6 after
RAIN30_DAYS = 30                           # today and the 29 days before
RAIN_DAY_MM, STORM_DAY_MM = 1.0, 5.0       # pipeline/features.py: an event is a run of days
                                           # with >= 1 mm; a storm day has >= 5 mm
SHADOW_KEEP = 0.73                         # docs/inferences.md section 4 (rain shadow)
WATER_T = (-1.59, 1.05)                    # docs/inferences.md section 5; 7-day trailing mean air,
AIR_WINDOW, AIR_MIN_DAYS = 7, 3            # at least 3 days, as pipeline/export_ledger.py
TEMP_TREND_DAYS, TEMP_TREND_C = 3, 0.5     # water-temperature trend (needs the owner's approval)
NORMAL_FROM = "1998-10-01"                 # ground normal: skip the 1998 start-up months
NORMAL_BELOW, NORMAL_ABOVE = 70.0, 130.0   # per cent of normal; the cut-offs of inferences.md s. 11
PUSH_NONE, PUSH_CLEAR = 2.0, 10.0          # percentage points (needs the owner's approval)

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


def push_reference():
    """Median rain3 and ground index among the 243 tests the rule was fitted on."""
    f = pd.read_csv(FROZEN, float_precision="round_trip")
    return float(f.rain3_mm.median()), float(f.ground_idx.median()), len(f)


def push(rain3, ground, ref):
    """How far each input moves the rule's chance from what it would be if that
    one input were at its median in the fitted record (the other unchanged).
    Returns {input: {points, direction, size}}; points are percentage points."""
    med_r3, med_g, _ = ref
    p = fr.chance(rain3, ground)
    out = {}
    for name, alt in (("rain3", fr.chance(med_r3, ground)), ("ground", fr.chance(rain3, med_g))):
        pts = round(100 * (p - alt), 1)
        size = "none" if abs(pts) < PUSH_NONE else ("a_little" if abs(pts) < PUSH_CLEAR else "clear")
        out[name] = {"points": pts, "direction": "none" if size == "none" else ("up" if pts > 0 else "down"),
                     "size": size}
    return out


def water_day(d):
    """Day of the water year (Oct 1 = 1), exactly as pipeline/features.py."""
    doy = d.timetuple().tm_yday
    return doy - 273 if doy >= 274 else doy + 92


def ground_normals():
    """{day of water year: (mean ground index, years)} from open-data/daily_rain_and_ground.csv,
    from NORMAL_FROM on. The file is in the repository, so both workflows have it."""
    d = pd.read_csv(DAILY_CSV, float_precision="round_trip")
    d["date"] = pd.to_datetime(d.date)
    d = d[d.date >= NORMAL_FROM].dropna(subset=["ground_idx"])
    d["wd"] = [water_day(x) for x in d.date]
    g = d.groupby("wd").ground_idx.agg(["mean", "count"])
    first, last = d.date.min().date().isoformat(), d.date.max().date().isoformat()
    return {int(k): (float(r["mean"]), int(r["count"])) for k, r in g.iterrows()}, first, last


def ground_vs_normal(day, g, normals):
    table, first, last = normals
    m = table.get(water_day(date.fromisoformat(day)))
    if not m or m[0] <= 0:
        return None
    pct = 100 * g / m[0]
    return {"normal_idx": round(m[0], 3), "pct_of_normal": round(pct, 1),
            "compared_to_normal": "below" if pct < NORMAL_BELOW else ("above" if pct > NORMAL_ABOVE else "near"),
            "years": m[1], "normal_from": first, "normal_to": last}


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
    ref = push_reference()
    normals = ground_normals()
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
            "push": push(rain3, ground, ref),
            "ground_normal": ground_vs_normal(r["target_date"], ground, normals),
        })
    return {**header(versions.pop(), now),
            "issue_date": issue,
            "issued_at_utc": latest[0]["issued_at_utc"],
            "stale": issue != today.isoformat(),
            "caveats": CAVEATS,
            "push_reference": {"rain3_mm": round(ref[0], 2), "ground_idx": round(ref[1], 3), "tests": ref[2]},
            "days": days}


GAUGES = [("US1CASM0001", "Pacifica 0.3 W"), ("US1CASM0033", "Pacifica 1.9 S")]
GAUGE_URL = "https://data.rcc-acis.org/StnData"


def gauge_daily(sid, first, last):
    """One gauge's daily rain in inches from NOAA ACIS, [{"date", "inches"}], first to last date.
    T (trace) is 0; M (missing) and values ending in A or S (multi-day accumulation) are null.
    The fetched content is treated as data only. Raises if the fetch or parse fails."""
    import requests
    r = requests.get(GAUGE_URL, params={"sid": sid, "sdate": first.isoformat(),
                                        "edate": last.isoformat(), "elems": "pcpn",
                                        "output": "json"}, timeout=30)
    r.raise_for_status()
    daily = []
    for row in r.json()["data"]:
        dt, v = str(row[0]), str(row[1]).strip()
        if v == "T":
            inches = 0.0
        elif v == "M" or v.endswith("A") or v.endswith("S"):
            inches = None
        else:
            inches = float(v)
        daily.append({"date": dt, "inches": inches})
    return daily


def gauge_block(today):
    """Daily rain from two CoCoRaHS volunteer gauges via NOAA ACIS, last 7 dates.
    Returns None if the fetch fails."""
    try:
        first = today - pd.Timedelta(days=6).to_pytimedelta()
        stations = [{"sid": sid, "name": name, "daily": gauge_daily(sid, first, today)}
                    for sid, name in GAUGES]
        return {"source": "CoCoRaHS volunteer gauges via NOAA ACIS",
                "source_url": "https://data.rcc-acis.org/",
                "note": "Each report covers the 24 hours to about 7am on its date.",
                "stations": stations}
    except Exception as e:  # a failed gauge fetch must not fail the export
        print(f"note: rain gauge fetch failed ({e})", file=sys.stderr)
        return None


def gauge_72h(dates):
    """{test date: (inches, gauge name)} for each date in `dates` (ISO strings): the sum of the
    reports dated that day and the two before, from the first of 'Pacifica 1.9 S' then
    'Pacifica 0.3 W' that has all three. Missing entries are (None, None); a failed fetch
    leaves everything null and never fails the export."""
    out = {d: (None, None) for d in dates}
    if not dates:
        return out
    order = [("US1CASM0033", "Pacifica 1.9 S"), ("US1CASM0001", "Pacifica 0.3 W")]
    try:
        first = date.fromisoformat(min(dates)) - pd.Timedelta(days=2).to_pytimedelta()
        last = date.fromisoformat(max(dates))
        series = []
        for sid, name in order:
            try:
                series.append((name, {x["date"]: x["inches"] for x in gauge_daily(sid, first, last)}))
            except Exception as e:
                print(f"note: rain gauge {sid} fetch failed ({e})", file=sys.stderr)
                series.append((name, {}))
        for d in dates:
            day = date.fromisoformat(d)
            keys = [(day - pd.Timedelta(days=i).to_pytimedelta()).isoformat() for i in (0, 1, 2)]
            for name, by_date in series:
                vals = [by_date.get(k) for k in keys]
                if all(v is not None for v in vals):
                    out[d] = (round(sum(vals), 2), name)
                    break
    except Exception as e:
        print(f"note: rain gauge sums failed ({e})", file=sys.stderr)
    return out


def conditions_file(today, now):
    """Rain, flow, ground, rain shadow and estimated creek temperature around today,
    from Open-Meteo through pipeline/forecast_log.py's own fetch functions.
    Raises fl.LogError if the rain cannot be had."""
    fc = fl.get_forecast()
    rain, src = fl.get_rain(today, fc)
    days = sorted(rain)
    flow, ground = fl.ground_index(rain, days)
    shadow, s = {}, 0.0
    for d in days:
        s = SHADOW_KEEP * s + rain[d]
        shadow[d] = s

    # air temperature: the archive for past days, the forecast call where the archive has none
    first = today - pd.Timedelta(days=HISTORY_BEFORE + AIR_WINDOW).to_pytimedelta()
    last = today + pd.Timedelta(days=HISTORY_AFTER).to_pytimedelta()
    real_yesterday = datetime.now(ZoneInfo(TZ_NAME)).date() - pd.Timedelta(days=1).to_pytimedelta()
    air = {}
    try:
        arch, _ = fl.daily_values(fl.ARCHIVE_URL, {"start_date": first.isoformat(),
                                                   "end_date": min(last, real_yesterday).isoformat()},
                                  ["temperature_2m_mean"])
        air.update({d: v for d, v in arch["temperature_2m_mean"].items() if v is not None})
    except fl.LogError as e:
        print(f"note: archive temperature call failed ({e})", file=sys.stderr)
    for d, v in ((fc or {}).get("temperature_2m_mean") or {}).items():
        if d not in air and v is not None:
            air[d] = v
    span = [first + pd.Timedelta(days=i).to_pytimedelta() for i in range((last - first).days + 1)]

    def water_t(d):
        w = [air[x] for x in span if d - pd.Timedelta(days=AIR_WINDOW - 1).to_pytimedelta() <= x <= d and x in air]
        return WATER_T[0] + WATER_T[1] * (sum(w) / len(w)) if len(w) >= AIR_MIN_DAYS else None

    out_days = []
    for i in range(-HISTORY_BEFORE, HISTORY_AFTER + 1):
        d = today + pd.Timedelta(days=i).to_pytimedelta()
        wt = water_t(d)
        out_days.append({"date": d.isoformat(), "rain_mm": round(rain[d], 2), "rain_src": src[d],
                         "flow_idx": round(flow[d], 3), "ground_idx": round(ground[d], 3),
                         "rain_shadow": round(shadow[d], 2),
                         "air_temp_mean_c": round(air[d], 1) if d in air else None,
                         "water_temp_est_c": round(wt, 1) if wt is not None else None})

    # the last 30 days' rain (today included) and the storms in it
    win = [today - pd.Timedelta(days=k).to_pytimedelta() for k in range(RAIN30_DAYS - 1, -1, -1)]
    storms, cur = [], None
    for d in days:
        if d > today:
            break
        if rain[d] >= RAIN_DAY_MM:
            if cur is None:
                cur = {"start": d, "end": d, "total": 0.0, "peak": 0.0, "fc": False}
            cur["end"], cur["total"] = d, cur["total"] + rain[d]
            cur["peak"] = max(cur["peak"], rain[d])
            cur["fc"] = cur["fc"] or src[d] == "forecast"
            cur.setdefault("storm_in_window", False)
            if rain[d] >= STORM_DAY_MM and d >= win[0]:
                cur["storm_in_window"] = True
        elif cur is not None:
            storms.append(cur); cur = None
    if cur is not None:
        storms.append(cur)
    storms = [{"start": e["start"].isoformat(), "end": e["end"].isoformat(), "total_mm": round(e["total"], 2),
               "wettest_day_mm": round(e["peak"], 2), "includes_forecast": e["fc"]}
              for e in storms if e.get("storm_in_window")]

    t0 = water_t(today)
    tn = water_t(today + pd.Timedelta(days=TEMP_TREND_DAYS).to_pytimedelta())
    trend = None
    if t0 is not None and tn is not None:
        trend = "steady" if abs(tn - t0) < TEMP_TREND_C else ("rising" if tn > t0 else "falling")
    yday, tmrw = today - pd.Timedelta(days=1).to_pytimedelta(), today + pd.Timedelta(days=1).to_pytimedelta()
    f0, f_1, f1 = flow[today], flow[yday], flow[tmrw]
    flow_trend = "peak" if f0 >= f_1 and f0 >= f1 else ("rising" if f1 > f0 else "falling")

    return {**header(fr.VERSION, now),
            "as_of": today.isoformat(),
            "source": fl.WEATHER_SOURCE + "; ERA5 archive for past days",
            "point": {"lat": fl.WX_LAT, "lon": fl.WX_LON},
            "note": "Rain is a weather-model estimate, not a gauge. flow_idx, ground_idx and rain_shadow are "
                    "indexes built from rain alone (no units). water_temp_est_c is an estimate of creek water "
                    "temperature from air temperature, not a measurement; treat it as +/- 2 degrees C at best.",
            "days": out_days,
            "rain_30d": {"from": win[0].isoformat(), "to": today.isoformat(),
                         "total_mm": round(sum(rain[d] for d in win), 2),
                         "forecast_mm": round(sum(rain[d] for d in win if src[d] == "forecast"), 2),
                         "storms": storms},
            "water_temp_trend": trend,
            "flow_trend": flow_trend,
            "gauge": gauge_block(today),
            "caveats": CAVEATS}


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
                {"name": "conditions.json", "updated": "daily",
                 "holds": "Rain, the wetness indexes and the estimated creek temperature for the 13 days before "
                          "today to 6 days after, and the last 30 days' rain and storms."},
                {"name": "levels.json", "updated": "when the rule changes",
                 "holds": "The four levels, their chance ranges, the odds seen for each, the standard and the caveats."},
                {"name": "meta.json", "updated": "when the files change",
                 "holds": "This list, the links, and the note on the address."},
                {"name": "latest_results.json", "updated": "weekly",
                 "holds": "The most recent county test result for each county series the project's page shows, "
                          "the last eight county ocean tests, and the latest Surfrider result at the creek mouth."},
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
    recent = None
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
        row = {"series": s["key"], "station": s["station"], "sampled_by": SAMPLED_BY,
               "analyte": s["analyte"], "date": d.isoformat(),
               "result_mpn": int(v) if v.is_integer() else round(v, 1),
               "unit": "MPN per 100 mL", "standard_mpn": s["standard"],
               "compared_to_standard": "over" if v > s["standard"] else "under",
               "days_old": (today - d).days, "source_url": COUNTY_SOURCE, "as_of": today.isoformat()}
        if s["key"] == "lm5_enterococcus":
            row["recent"] = [{"date": r.date.date().isoformat(),
                              "result_mpn": int(r.v) if float(r.v).is_integer() else round(float(r.v), 1),
                              "compared_to_standard": "over" if r.v > s["standard"] else "under"}
                             for r in df.tail(RECENT_COUNTY_TESTS).itertuples()]
        out.append(row)
    sr = surfrider_latest(con, today)
    if sr:
        out.append(sr)
    return {**header(fr.VERSION, now),
            "note": "County results reach the state's public database weeks after the sample, so these "
                    "are not current conditions. For current postings see the county's beach page.",
            "county_beach_advisories": COUNTY_ADVISORIES,
            "results": out,
            "caveats": CAVEATS}


def surfrider_latest(con, today):
    """The latest Surfrider enterococcus result at the creek mouth (highest of the
    day, as on the public page), or None. Nothing else from that table is published."""
    s = SURFRIDER
    try:
        df = pd.read_sql("""SELECT collection_date, entero FROM bwtf_lindamar WHERE "site name" = ?""",
                         con, params=[s["site_name"]])
    except Exception as e:  # table missing on a partial database
        print(f"note: no Surfrider results ({e})", file=sys.stderr)
        return None
    df["date"] = pd.to_datetime(df.collection_date, errors="coerce").dt.normalize()
    df["v"] = pd.to_numeric(df.entero, errors="coerce")
    df = df.dropna(subset=["date", "v"]).groupby("date", as_index=False).v.max().sort_values("date")
    if df.empty:
        return None
    last = df.iloc[-1]
    d, v = last.date.date(), float(last.v)
    return {"series": s["key"], "station": s["station"], "sampled_by": s["sampled_by"],
            "analyte": s["analyte"], "date": d.isoformat(),
            "result_mpn": int(v) if v.is_integer() else round(v, 1),
            "unit": "MPN per 100 mL", "standard_mpn": s["standard"],
            "compared_to_standard": "over" if v > s["standard"] else "under",
            "days_old": (today - d).days, "source_url": s["source_url"], "as_of": today.isoformat()}


def _track_extras(r, log_row, gauge):
    """The rain the forecast used, the rain recorded afterwards, the level the rule gives with
    the recorded rain, and the volunteer gauge's three-day sum. Null where not available."""
    assumed = number(log_row["rain3_mm"]) if log_row else None
    recorded = number(r.get("rain3_actual_mm", ""))
    lvl = r.get("level_actual_weather") or None
    return {"rain_assumed_mm": None if assumed is None else round(float(assumed), 1),
            "rain_recorded_mm": None if recorded is None else round(float(recorded), 1),
            "level_with_recorded_rain": lvl,
            "level_key_with_recorded_rain": LEVEL_KEYS.get(lvl) if lvl else None,
            "gauge_72h_inches": gauge[0], "gauge_name": gauge[1]}


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
    log0 = {}
    if LOG.exists():
        with open(LOG, encoding="utf-8", newline="") as f:
            for lr in csv.DictReader(f):
                if lr.get("lead_days") == "0":
                    log0.setdefault(lr["target_date"], lr)
    gauges = gauge_72h([r["target_date"] for r in rows])
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
                      "far_over": v > fr.FAR_OVER, "forecasts": fc}
                     | _track_extras(r, log0.get(r["target_date"]), gauges.get(r["target_date"], (None, None))))
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
        try:
            write("conditions.json", conditions_file(today, now), dry)
        except (fl.LogError, KeyError, TypeError, ValueError) as e:
            # The forecast log is already written by now; a failed fetch here must not stop
            # it being committed. The old conditions.json stays, and its as_of shows its age.
            print(f"note: conditions.json not updated ({e})", file=sys.stderr)
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
