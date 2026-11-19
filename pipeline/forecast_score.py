"""Compare the logged forecasts with the county's test results.

Takes the county's LM5 enterococcus test series exactly as pipeline/forecast_rule.py
builds it (load_tests), matches each test date to the forecasts logged for that
date in open-data/forecast_log.csv (one per lead, 0 to 6 days ahead), and writes
open-data/forecast_scored.csv. That file is derived: it is rebuilt from the log
and the database every time and may be regenerated at any time. The log itself
is never touched by this script.

Columns: target_date, result_mpn, failed (1 if over 104), far_over (1 if over
312), chance_lead0 .. chance_lead6, level_lead0 .. level_lead6 (blank where no
forecast was logged at that lead).

Then prints a plain summary: the number of tests scored so far; for leads 0, 1
and 3, how many tests fell in each level and the share that failed, beside the
odds in models/forecast_v0_1.json (those odds come from the 2022-2026 record,
held out; they are not a promise); and a ranking score (AUC) once at least 20
tests at that lead have both outcomes. A test is "scored" once at least one
forecast for its date is in the log. Nothing here says the water is ever safe.

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
LOG_COLUMNS = ["issued_at_utc", "issue_date", "target_date", "lead_days", "rain3_mm",
               "rain3_forecast_mm", "ground_idx", "chance", "level", "rule_version"]


def read_log():
    """{(target_date, lead): (chance, level)}; the earliest logged row wins if a
    pair somehow appears twice."""
    if not LOG.exists():
        return {}
    out = {}
    with open(LOG, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != LOG_COLUMNS:
            sys.exit(f"{LOG.name} does not have the expected header")
        for row in reader:
            key = (row["target_date"], int(row["lead_days"]))
            if key in out:
                print(f"warn: more than one row for {key}; keeping the first", file=sys.stderr)
                continue
            out[key] = (float(row["chance"]), row["level"])
    return out


def main():
    if not DB.exists():
        print(f"No database at {DB.relative_to(ROOT)}; the county tests are read from it. Nothing scored.")
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tests = fr.load_tests(con)
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
            row[f"chance_lead{k}"] = f"{log[(d, k)][0]:.3f}" if (d, k) in log else ""
        for k in LEADS:
            row[f"level_lead{k}"] = log[(d, k)][1] if (d, k) in log else ""
        rows.append(row)

    print(f"Tests scored so far: {len(rows)} "
          f"(county tests from {tests.date.min().date()} to {tests.date.max().date()} "
          f"in the database; {len(log)} forecasts in the log)")
    if not rows:
        print("No tests scored yet: none of the logged forecasts is for a date with a county result. "
              "Results reach the database weeks after the sample. No file written.")
        return 0

    columns = (["target_date", "result_mpn", "failed", "far_over"]
               + [f"chance_lead{k}" for k in LEADS] + [f"level_lead{k}" for k in LEADS])
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
            share = f"{sum(r['failed'] for r in g) / len(g):.0%}" if g else "-"
            print(f"  {name:17} {len(g):>5} {share:>13}   {odds}")
        y = [r["failed"] for r in sub]
        if len(sub) >= MIN_TESTS_FOR_AUC and 0 < sum(y) < len(y):
            a = fr.auc([float(r[f"chance_lead{k}"]) for r in sub], y)
            print(f"  ranking score (AUC): {a:.3f}  (0.5 is a coin flip; {len(sub)} tests)")
        else:
            print(f"  ranking score (AUC): not shown until at least {MIN_TESTS_FOR_AUC} tests "
                  "with both outcomes exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
