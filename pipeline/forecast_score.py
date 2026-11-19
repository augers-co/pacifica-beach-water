"""Compare the logged forecasts with the county's test results.

Takes the county's LM5 enterococcus test series exactly as pipeline/forecast_rule.py
builds it (load_tests), matches each test date to the forecasts logged for that
date in open-data/forecast_log.csv (one per lead, 0 to 6 days ahead), and writes
open-data/forecast_scored.csv. That file is derived: it is rebuilt from the log
and the database every time and may be regenerated at any time. The log itself
is never touched by this script.

Columns: target_date, result_mpn, failed (1 if over 104), far_over (1 if over
312), chance_lead0 .. chance_lead6, level_lead0 .. level_lead6 (blank where no
forecast was logged at that lead), then what actually happened, from the
database as it stands when this is run (the rain archive revises past rain a
little, so these can drift):
  rain3_actual_mm, ground_actual    rain over the test day and two days before,
                                    and the ground index, from weather_daily
                                    and rain_context
  chance_actual_weather,            what the rule gives when fed those actual
  level_actual_weather              values
  rain3_error_mm_lead0/1/3          logged rain3_mm minus actual
  temp_mean_c_lead1,                the temperature and sunshine forecast logged
  temp_mean_actual_c,               one day ahead, beside the values in
  sun_mj_m2_lead1, sun_actual_mj_m2 wx_extra_daily (blank if not available)

Then prints a plain summary: the number of tests scored so far; for leads 0, 1
and 3, how many tests fell in each level and the share that failed, beside the
odds in models/forecast_v0_1.json (those odds come from the 2022-2026 record,
held out; they are not a promise); and a ranking score (AUC) once at least 20
tests at that lead have both outcomes. A test is "scored" once at least one
forecast for its date is in the log.

The summary ends with "Was it the rule or the weather forecast?": for leads 0,
1 and 3, how many tests changed level between the forecast as issued and the
same rule fed the actual weather, the typical size of the rain error, and the
share that failed at each level both ways. A change to the rule is to be
judged on the rule fed the actual weather; the weather forecast's own error is
reported separately. Nothing here says the water is ever safe.

Needs the database (data/pacifica.db), numpy and pandas. Run from the repo root:
    python3 pipeline/forecast_score.py
"""

import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # find forecast_rule even under python -I
import forecast_rule as fr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
LOG = ROOT / "open-data" / "forecast_log.csv"
OUT = ROOT / "open-data" / "forecast_scored.csv"
MODEL = ROOT / "models" / "forecast_v0_1.json"

LEADS = range(7)
SUMMARY_LEADS = (0, 1, 3)
MIN_TESTS_FOR_AUC = 20
ERROR_LEADS = (0, 1, 3)
# Columns this script reads from the log; the log may have more (the weather
# forecast columns), and the weather ones are optional.
LOG_COLUMNS = ["issued_at_utc", "issue_date", "target_date", "lead_days", "rain3_mm",
               "rain3_forecast_mm", "ground_idx", "chance", "level", "rule_version"]


def read_log():
    """{(target_date, lead): the logged row as a dict}; the earliest logged row
    wins if a pair somehow appears twice."""
    if not LOG.exists():
        return {}
    out = {}
    with open(LOG, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or reader.fieldnames[:len(LOG_COLUMNS)] != LOG_COLUMNS:
            sys.exit(f"{LOG.name} does not have the expected header")
        for row in reader:
            key = (row["target_date"], int(row["lead_days"]))
            if key in out:
                print(f"warn: more than one row for {key}; keeping the first", file=sys.stderr)
                continue
            out[key] = row
    return out


def num(x):
    """A float from a log cell, or None if blank."""
    try:
        return float(x) if x not in ("", None) else None
    except ValueError:
        return None


def load_extra_actuals(con):
    """{date string: (temp_mean, solar_mj)} from wx_extra_daily, or {} if the
    table or its columns are not there."""
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(wx_extra_daily)")}
        if not {"date", "temp_mean", "solar_mj"} <= cols:
            return {}
        return {str(d)[:10]: (t, m) for d, t, m in
                con.execute("SELECT date, temp_mean, solar_mj FROM wx_extra_daily")}
    except sqlite3.Error:
        return {}


def fmt(v, nd):
    return "" if v is None else f"{v:.{nd}f}"


def share(rows, key):
    return f"{sum(r['failed'] for r in rows) / len(rows):.0%}" if rows else "-"


def main():
    if not DB.exists():
        print(f"No database at {DB.relative_to(ROOT)}; the county tests are read from it. Nothing scored.")
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tests = fr.load_tests(con)
        extra = load_extra_actuals(con)
    finally:
        con.close()
    log = read_log()

    rows = []
    for _, t in tests.iterrows():
        d = str(t.date.date())
        if not any((d, k) in log for k in LEADS):
            continue
        row = {"target_date": d, "result_mpn": f"{t.value:g}", "failed": int(t.fail), "far_over": int(t.far)}
        for k in LEADS:
            row[f"chance_lead{k}"] = f"{float(log[(d, k)]['chance']):.3f}" if (d, k) in log else ""
        for k in LEADS:
            row[f"level_lead{k}"] = log[(d, k)]["level"] if (d, k) in log else ""
        # what actually happened, and what the rule gives with it
        p_act = float(fr.chance(t.rain3, t.ground))
        row["rain3_actual_mm"] = f"{t.rain3:.2f}"
        row["ground_actual"] = f"{t.ground:.3f}"
        row["chance_actual_weather"] = f"{p_act:.3f}"
        row["level_actual_weather"] = fr.level(round(p_act, 3))
        for k in ERROR_LEADS:
            logged = num(log[(d, k)]["rain3_mm"]) if (d, k) in log else None
            row[f"rain3_error_mm_lead{k}"] = fmt(None if logged is None else logged - t.rain3, 2)
        l1 = log.get((d, 1), {})
        actual_t, actual_m = extra.get(d, (None, None))
        row["temp_mean_c_lead1"] = fmt(num(l1.get("temp_mean_c")), 1)
        row["temp_mean_actual_c"] = fmt(actual_t, 1)
        row["sun_mj_m2_lead1"] = fmt(num(l1.get("sun_mj_m2")), 2)
        row["sun_actual_mj_m2"] = fmt(actual_m, 2)
        rows.append(row)

    print(f"Tests scored so far: {len(rows)} "
          f"(county tests from {tests.date.min().date()} to {tests.date.max().date()} "
          f"in the database; {len(log)} forecasts in the log)")
    if not rows:
        print("No tests scored yet: none of the logged forecasts is for a date with a county result. "
              "Results reach the database weeks after the sample. No file written.")
        return 0

    columns = (["target_date", "result_mpn", "failed", "far_over"]
               + [f"chance_lead{k}" for k in LEADS] + [f"level_lead{k}" for k in LEADS]
               + ["rain3_actual_mm", "ground_actual", "chance_actual_weather", "level_actual_weather"]
               + [f"rain3_error_mm_lead{k}" for k in ERROR_LEADS]
               + ["temp_mean_c_lead1", "temp_mean_actual_c", "sun_mj_m2_lead1", "sun_actual_mj_m2"])
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT.relative_to(ROOT)}")

    stated = {r["level"]: r for r in json.loads(MODEL.read_text())["held_out"]["level_table"]}
    for k in SUMMARY_LEADS:
        sub = [r for r in rows if r[f"level_lead{k}"]]
        print(f"\nForecast {k} day(s) ahead: {len(sub)} tests")
        if not sub:
            print("  none yet")
            continue
        print(f"  {'level':17} {'tests':>5} {'share failed':>13}   odds stated in the model file")
        for name, _ in fr.LEVELS:
            g = [r for r in sub if r[f"level_lead{k}"] == name]
            s = stated.get(name, {})
            odds = f"{s['pct_fail']:.0%} failed (n={s['n']})" if s.get("pct_fail") is not None else "n/a"
            print(f"  {name:17} {len(g):>5} {share(g, 'failed'):>13}   {odds}")
        y = [r["failed"] for r in sub]
        if len(sub) >= MIN_TESTS_FOR_AUC and 0 < sum(y) < len(y):
            a = fr.auc([float(r[f"chance_lead{k}"]) for r in sub], y)
            print(f"  ranking score (AUC): {a:.3f}  (0.5 is a coin flip; {len(sub)} tests)")
        else:
            print(f"  ranking score (AUC): not shown until at least {MIN_TESTS_FOR_AUC} tests "
                  "with both outcomes exist")

    print("\nWas it the rule or the weather forecast?")
    print("  'As issued' is the forecast logged ahead of time. 'Actual weather' is the same rule fed the "
          "rain and ground index that the database now holds for the test day.")
    for k in SUMMARY_LEADS:
        sub = [r for r in rows if r[f"level_lead{k}"]]
        print(f"\n  Forecast {k} day(s) ahead: {len(sub)} tests")
        if not sub:
            print("    none yet")
            continue
        changed = sum(r[f"level_lead{k}"] != r["level_actual_weather"] for r in sub)
        print(f"    level changed between as issued and actual weather: {changed} of {len(sub)}")
        errs = [float(r[f"rain3_error_mm_lead{k}"]) for r in sub if r.get(f"rain3_error_mm_lead{k}", "") != ""]
        if errs:
            ordered = sorted(abs(e) for e in errs)
            median_abs = ordered[len(ordered) // 2] if len(ordered) % 2 else \
                (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
            print(f"    rain error (logged minus actual, mm over three days): median size {median_abs:.1f}, "
                  f"average {sum(errs) / len(errs):+.1f} (plus means more rain was forecast than fell)")
        print(f"    {'level':17} {'as issued':>22} {'actual weather':>22}")
        print(f"    {'':17} {'tests':>8} {'failed':>12} {'tests':>8} {'failed':>12}")
        for name, _ in fr.LEVELS:
            a = [r for r in sub if r[f"level_lead{k}"] == name]
            b = [r for r in sub if r["level_actual_weather"] == name]
            print(f"    {name:17} {len(a):>8} {share(a, 'failed'):>12} {len(b):>8} {share(b, 'failed'):>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
