"""A simple rule for how likely a test at Linda Mar beach is to fail (version 0.1).

WHAT IT IS FOR
San Mateo County tests the ocean water at the mouth of San Pedro Creek
(station LM5) for enterococcus bacteria, about once a week. A test "fails"
when the result is over 104 MPN per 100 mL, and is "far over" when it is over
312 (three times the standard). The results reach the state's public database
weeks after the sample. This rule gives a rough chance that a test taken on a given day would
fail, using only two things that are known beforehand:

  R3  total rain (mm) on the day and the two days before it
  G   the site's ground-wetness index, as known through the day before
      (rain_context.ground_idx, floored at 1); it is built from rain alone and
      stands in for how wet the valley's soil and water table are

The equation is an ordinary logistic regression:

    z = b0 + b1 * ln(1 + R3) + b2 * log10(G)
    chance of failing  P = 1 / (1 + exp(-z))

Drier ground means HIGHER risk (b2 is negative). In this record the ground is
driest late in the dry season, when the weather is also warm and the creek is
low. The rule uses the ground reading as its signal for that season; it cannot
say which of those conditions is behind the rise, and it is not evidence that
wet ground carries pollution. P is turned into four plain-language levels:
"lower than usual" (P < 0.50), "usual" (0.50 to 0.70), "high" (0.70 to 0.85)
and "very high" (0.85 or more).

HOW TO READ THE SCORES
The script fits the equation on every test since 2022, then checks it two
ways: (1) predict each calendar year from a fit on the other four years, and
(2) predict 2024, 2025 and 2026 from earlier years only. It reports the
ranking score (AUC: the chance that a randomly chosen failing test was given a
higher P than a randomly chosen passing one; 0.5 is a coin flip) and the Brier
score (mean squared error of P; lower is better).

CAVEATS, PLAINLY
- The two inputs and the rain window were chosen after looking at the whole
  record, so the held-out scores above are somewhat flattering. A truly
  untouched test would likely score lower.
- With about 240 tests and five years, the coefficients are rough.
- Nothing here says the water is ever safe. A "lower than usual" day still
  failed more than a third of the time in the record. Weekly tests sample one
  moment at one spot, and bacteria levels change within hours.

By default it reads ONE file, open-data/rule_v0_1_worked.csv: the frozen record
of the 243 tests (2022-01-03 to 2026-10-19) and the inputs as they were when
version 0.1 was fixed. That file never changes, so this run prints the same
numbers on every machine, forever, with no database and nothing but numpy and
pandas. Run from the repo root:
    python3 pipeline/forecast_rule.py
With --refit it repeats the same method on CURRENT data (data/pacifica.db if it
is there, otherwise open-data/county_ocean_tests.csv and
open-data/daily_rain_and_ground.csv; add --from-open-data to force the CSVs),
prints the same report labelled as a refit, and shows the frozen coefficients
beside the refitted ones. The recent rain is revised by its source and new tests
keep arriving, so a refit moves a little each week; it is not version 0.1.
It never writes models/forecast_v0_1.json unless given --write-model (which
cannot be combined with --refit, and leaves the file alone when only its
"fitted" date would change).
Other code can import `chance(rain3_mm, ground_idx)` and `level(p)`.
"""

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
OPEN = ROOT / "open-data"
OUT = ROOT / "models" / "forecast_v0_1.json"

VERSION = "0.1"
START = "2022-01-01"
STANDARD = 104.0                      # MPN per 100 mL, single-sample standard
FAR_OVER = 3 * STANDARD               # "far over" = three times the standard
LEVELS = [                            # (name, lowest P in the level)
    ("lower than usual", 0.0),
    ("usual", 0.50),
    ("high", 0.70),
    ("very high", 0.85),
]
FORWARD_YEARS = (2024, 2025, 2026)

# Coefficients of the frozen equation (version 0.1). They never change.
COEF = (2.051, 0.770, -1.363)


# ------------------------------------------------------------------ the rule
def _design(rain3_mm, ground_idx):
    rain3 = np.asarray(rain3_mm, dtype=float)
    ground = np.maximum(np.asarray(ground_idx, dtype=float), 1.0)
    return np.column_stack([np.ones(rain3.size), np.log1p(rain3.ravel()), np.log10(ground.ravel())])


def chance(rain3_mm, ground_idx, coef=None):
    """Chance (0 to 1) that a test fails, from rain in mm over the test day and
    the two days before, and the ground-wetness index through the day before."""
    b = np.asarray(COEF if coef is None else coef, dtype=float)
    p = 1.0 / (1.0 + np.exp(-(_design(rain3_mm, ground_idx) @ b)))
    return float(p[0]) if np.ndim(rain3_mm) == 0 and np.ndim(ground_idx) == 0 else p


def level(p):
    """Name of the level for a chance P."""
    name = LEVELS[0][0]
    for n, lo in LEVELS:
        if p >= lo:
            name = n
    return name


# ------------------------------------------------------------------ data
def county_series(con):
    """Every sampling day at LM5 (daily maximum), all years: columns date, value."""
    raw = pd.read_sql(
        """SELECT SampleDate, Result FROM ceden_raw
           WHERE StationName LIKE '%#5%' AND Analyte LIKE '%Enterococcus%'""", con)
    raw["date"] = pd.to_datetime(raw.SampleDate).dt.tz_localize(None).dt.normalize()
    raw["value"] = pd.to_numeric(raw.Result, errors="coerce")
    return (raw.dropna(subset=["value"]).groupby("date", as_index=False).value.max()
            .sort_values("date"))


def _attach(t, wx, rc):
    """Keep tests since START and attach the rain total and ground index.
    wx has columns date, precip_mm; rc has columns date, ground_idx."""
    t = t[t.date >= START].reset_index(drop=True)

    wx = wx.copy()
    wx["date"] = pd.to_datetime(wx.date)
    rain = wx.set_index("date").precip_mm.sort_index().fillna(0)
    t["rain3"] = sum(rain.reindex(t.date - pd.Timedelta(days=k)).to_numpy() for k in range(3))

    rc = rc.copy()
    rc["date"] = pd.to_datetime(rc.date)
    # rain_context rows are defined through the PRIOR day, so the row dated on
    # the test day is the value "as known through the day before".
    t["ground"] = rc.set_index("date").ground_idx.reindex(t.date).to_numpy()

    t = t.dropna(subset=["rain3", "ground"]).reset_index(drop=True)
    t["fail"] = (t.value > STANDARD).astype(int)
    t["far"] = (t.value > FAR_OVER).astype(int)
    t["year"] = t.date.dt.year
    return t


def load_tests(con):
    """One row per sampling day at LM5 (daily maximum), since START, with the
    rain total and ground index attached."""
    wx = pd.read_sql("SELECT date, precip_mm FROM weather_daily", con)
    rc = pd.read_sql("SELECT date, ground_idx FROM rain_context", con)
    return _attach(county_series(con), wx, rc)


def load_tests_frozen():
    """The frozen record of the version-0.1 fit: one file, nothing else."""
    f = pd.read_csv(OPEN / "rule_v0_1_worked.csv", float_precision="round_trip")
    return pd.DataFrame({
        "date": pd.to_datetime(f.date), "value": f.result_mpn,
        "rain3": f.rain3_mm, "ground": f.ground_idx,
        "fail": (f.result_mpn > STANDARD).astype(int),
        "far": (f.result_mpn > FAR_OVER).astype(int),
        "year": pd.to_datetime(f.date).dt.year})


def load_tests_open():
    """The same table, built from the published files in open-data/ instead of
    the database."""
    t = pd.read_csv(OPEN / "county_ocean_tests.csv", float_precision="round_trip")
    t = pd.DataFrame({"date": pd.to_datetime(t.date), "value": t.result_mpn})
    d = pd.read_csv(OPEN / "daily_rain_and_ground.csv", float_precision="round_trip")
    return _attach(t.sort_values("date"), d[["date", "rain_mm"]].rename(columns={"rain_mm": "precip_mm"}),
                   d[["date", "ground_idx"]])


# ------------------------------------------------------------------ fitting
def fit_logistic(X, y, iters=100):
    """Ordinary (unpenalised) logistic regression by Newton / IRLS."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(X @ b)))
        step = np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]), X.T @ (y - p))
        b = b + step
        if np.max(np.abs(step)) < 1e-12:
            break
    return b


def predict(X, b):
    return 1.0 / (1.0 + np.exp(-(X @ b)))


def auc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, bool)
    n1, n0 = y.sum(), (~y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(score).rank().to_numpy()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def held_out(X, y, year, cols, forward=False):
    """Held-out chances. Default: each year from a fit on the other years.
    forward=True: FORWARD_YEARS each from earlier years only (others NaN)."""
    p = np.full(len(y), np.nan)
    for t in (FORWARD_YEARS if forward else sorted(set(year))):
        te = year == t
        tr = (year < t) if forward else ~te
        b = fit_logistic(X[tr][:, cols], y[tr])
        p[te] = predict(X[te][:, cols], b)
    return p


def scores(p, y, y3):
    ok = ~np.isnan(p)
    return {"auc_fail": auc(p[ok], y[ok]), "auc_far": auc(p[ok], y3[ok]),
            "brier": float(np.mean((p[ok] - y[ok]) ** 2)), "n": int(ok.sum())}


def level_table(p, y, y3):
    rows = []
    for i, (name, lo) in enumerate(LEVELS):
        hi = LEVELS[i + 1][1] if i + 1 < len(LEVELS) else 1.01
        g = (p >= lo) & (p < hi)
        rows.append({"level": name, "from_p": lo, "n": int(g.sum()),
                     "pct_fail": float(y[g].mean()) if g.any() else None,
                     "pct_far_over": float(y3[g].mean()) if g.any() else None})
    return rows


# ------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    refit = "--refit" in args
    if refit and "--write-model" in args:
        raise SystemExit("--write-model cannot be combined with --refit: the model file records version 0.1.")
    if not refit:
        t = load_tests_frozen()
    elif "--from-open-data" in args or not DB.exists():
        t = load_tests_open()
    else:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            t = load_tests(con)
        finally:
            con.close()
    y, y3, year = t.fail.to_numpy(float), t.far.to_numpy(float), t.year.to_numpy()
    X = _design(t.rain3.to_numpy(), t.ground.to_numpy())
    both, rain_only, ground_only = [0, 1, 2], [0, 1], [0, 2]

    if refit:
        print(f"REFIT on current data, not version 0.1: {len(t)} tests through {t.date.max().date()}")
    print(f"LM5 enterococcus, one value per day (daily max), {t.date.min().date()} to {t.date.max().date()}")
    print(f"n = {len(t)} tests; {int(y.sum())} fail (over {STANDARD:.0f}); {int(y3.sum())} far over (over {FAR_OVER:.0f})\n")

    b = fit_logistic(X, y)
    print(f"z = {b[0]:+.3f} {b[1]:+.3f}*ln(1+R3) {b[2]:+.3f}*log10(G)   P = 1/(1+exp(-z))\n")
    if refit:
        print(f"Frozen version 0.1 coefficients, for comparison: {COEF[0]:+.3f} {COEF[1]:+.3f} {COEF[2]:+.3f}\n")

    p_all = held_out(X, y, year, both)
    p_fwd = held_out(X, y, year, both, forward=True)
    s_all, s_fwd = scores(p_all, y, y3), scores(p_fwd, y, y3)
    print("Held-out scores            AUC fails   AUC far over   Brier    n")
    print(f"  each year from the other four   {s_all['auc_fail']:.3f}   {s_all['auc_far']:.3f}   {s_all['brier']:.3f}   {s_all['n']}")
    print(f"  2024-26 from earlier years only {s_fwd['auc_fail']:.3f}   {s_fwd['auc_far']:.3f}   {s_fwd['brier']:.3f}   {s_fwd['n']}\n")

    print("By year (each year from the other four): AUC fails / AUC far over / n")
    by_year = {}
    for yr in sorted(set(year)):
        m = year == yr
        by_year[int(yr)] = {"auc_fail": auc(p_all[m], y[m]), "auc_far": auc(p_all[m], y3[m]), "n": int(m.sum())}
        print(f"  {yr}: {by_year[int(yr)]['auc_fail']:.3f} / {by_year[int(yr)]['auc_far']:.3f} / {m.sum()}")

    # "no forecast": always predict the share of failures in the other years
    p_base = np.full(len(y), np.nan)
    for yr in sorted(set(year)):
        te = year == yr
        p_base[te] = y[~te].mean()
    print(f"\nNo-forecast baseline Brier (always the other years' average): {np.mean((p_base - y) ** 2):.3f}"
          f"   (equation: {s_all['brier']:.3f})")

    print("\nSingle-input versions, held out (each year from other four | 2024-26 from earlier years):")
    singles = {}
    for lab, cols in (("rain only", rain_only), ("ground only", ground_only)):
        a = scores(held_out(X, y, year, cols), y, y3)
        f = scores(held_out(X, y, year, cols, forward=True), y, y3)
        singles[lab] = {"each_year": a, "forward": f}
        print(f"  {lab:12} {a['auc_fail']:.3f} / {a['auc_far']:.3f} / Brier {a['brier']:.3f}  |  {f['auc_fail']:.3f} / {f['auc_far']:.3f}")

    table = level_table(p_all, y, y3)
    print("\nLevels on the held-out predictions (each year from the other four):")
    for r in table:
        if r["n"]:
            print(f"  {r['level']:17} n={r['n']:>3}  {r['pct_fail']:>4.0%} fail  {r['pct_far_over']:>4.0%} far over")
        else:
            print(f"  {r['level']:17} n=  0")

    if "--write-model" not in args:
        return
    OUT.parent.mkdir(exist_ok=True)
    result = ({
        "version": VERSION,
        "fitted": date.today().isoformat(),
        "data": {"station": "San Mateo County LM5 (San Pedro Creek mouth), enterococcus, daily maximum",
                 "first_test": str(t.date.min().date()), "last_test": str(t.date.max().date()),
                 "n": int(len(t)), "n_fail": int(y.sum()), "n_far_over": int(y3.sum()),
                 "fail_over": STANDARD, "far_over": FAR_OVER},
        "equation": "z = b0 + b1*ln(1+R3) + b2*log10(max(G,1)); P = 1/(1+exp(-z))",
        "coefficients": {"b0": round(float(b[0]), 3), "b1": round(float(b[1]), 3), "b2": round(float(b[2]), 3)},
        "levels": [{"name": n, "min_p": lo} for n, lo in LEVELS],
        "held_out": {"each_year_from_other_four": s_all, "forward_2024_26": s_fwd,
                     "by_year": by_year, "single_input": singles,
                     "level_table": table},
        "caveat": "Inputs were chosen after looking at the whole record, so held-out scores are somewhat flattering. Nothing here says the water is safe.",
    })
    # Leave the file alone when nothing but the date would change, so a re-run
    # does not make a pointless difference.
    try:
        old = json.loads(OUT.read_text())
    except (OSError, ValueError):
        old = None
    if old is not None and {**old, "fitted": None} == {**json.loads(json.dumps(result)), "fitted": None}:
        print(f"\nUnchanged {OUT.relative_to(ROOT)}")
    else:
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
