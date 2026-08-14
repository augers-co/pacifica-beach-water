"""First cross-analysis: bacteria exceedance vs antecedent rainfall.

Reads data/pacifica.db (built by fetch.py), builds a unified sample table with
rain features, and reports exceedance rates by antecedent-rain condition.

Exceedance thresholds (single-sample):
  Ocean stations (AB411): enterococcus >104, fecal coliform >400,
    total coliform >10,000 MPN/100mL
  Creek station (EPA 2012 RWQC freshwater STV): E. coli >320,
    enterococcus >110 MPN/100mL
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"

OCEAN = {"ent": 104, "fc": 400, "tc": 10000}
CREEK = {"ecoli": 320, "ent": 110}

RAIN_BINS = [-0.01, 0.099, 5, 15, 40, np.inf]
RAIN_LABELS = ["dry (0)", "0.1-5mm", "5-15mm", "15-40mm", ">40mm"]


def norm_analyte(name):
    n = str(name).lower()
    if "enterococcus" in n:
        return "ent"
    if "e. coli" in n or "escherichia" in n:
        return "ecoli"
    if "fecal" in n:
        return "fc"
    if "total" in n:
        return "tc"
    return None


def norm_station(name):
    n = str(name)
    if "#5" in n:
        return "LM5"
    if "#6" in n:
        return "LM6"
    if "San Pedro Creek" in n:
        return "CREEK"
    return None


def load_samples(con):
    df = pd.read_sql("SELECT * FROM ceden_raw", con)
    df["station"] = df["StationName"].map(norm_station)
    df["analyte"] = df["Analyte"].map(norm_analyte)
    df["date"] = pd.to_datetime(df["SampleDate"], errors="coerce").dt.normalize()
    df["value"] = pd.to_numeric(df["Result"], errors="coerce")
    df = df.dropna(subset=["station", "analyte", "date", "value"])
    # replicates / era-boundary duplicates: keep the max reading per station-date-analyte
    df = (
        df.groupby(["station", "date", "analyte"], as_index=False)
        .agg(value=("value", "max"))
    )
    return df


def rain_features(con):
    wx = pd.read_sql("SELECT * FROM weather_daily", con)
    wx["date"] = pd.to_datetime(wx["date"])
    wx = wx.set_index("date").sort_index()
    p = wx["precip_mm"].astype(float)
    f = pd.DataFrame(index=p.index)
    f["day0"] = p
    f["prev1"] = p.shift(1)
    for w in (3, 7, 14, 30):
        f[f"prev{w}"] = p.shift(1).rolling(w, min_periods=w).sum()
    # water-year cumulative through yesterday (proxy for shallow groundwater state)
    wy = (p.index - pd.DateOffset(months=9)).year  # Oct 1 starts the water year
    f["season_cum"] = p.groupby(wy).cumsum().shift(1)
    return f


def exceed(row):
    thr = CREEK if row["station"] == "CREEK" else OCEAN
    t = thr.get(row["analyte"])
    return None if t is None else row["value"] > t


def auc_mannwhitney(x, y):
    """AUC of feature x for binary outcome y via rank statistic."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=bool)
    ok = ~np.isnan(x)
    x, y = x[ok], y[ok]
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    ranks = pd.Series(x).rank().to_numpy()
    return (ranks[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())


def rate(g):
    return f"{g['exceed'].mean() * 100:5.1f}%  (n={len(g)})"


def main():
    con = sqlite3.connect(DB)
    samples = load_samples(con)
    feats = rain_features(con)
    con.close()

    df = samples.join(feats, on="date")
    df["exceed"] = df.apply(exceed, axis=1)
    df = df.dropna(subset=["exceed"])
    df["exceed"] = df["exceed"].astype(bool)
    df["rain_bin"] = pd.cut(df["prev3"], RAIN_BINS, labels=RAIN_LABELS)
    df["month"] = df["date"].dt.month
    df["wet_season"] = df["month"].isin([10, 11, 12, 1, 2, 3, 4])

    print("=" * 70)
    print("COVERAGE")
    for (st, an), g in df.groupby(["station", "analyte"]):
        print(
            f"  {st:5s} {an:5s} {g['date'].min().date()} .. {g['date'].max().date()}"
            f"  n={len(g)}"
        )

    headline = df[
        ((df["station"] == "CREEK") & (df["analyte"] == "ecoli"))
        | ((df["station"].isin(["LM5", "LM6"])) & (df["analyte"] == "ent"))
    ].copy()

    print("=" * 70)
    print("EXCEEDANCE RATES (headline analytes: beach=enterococcus, creek=E.coli)")
    for st, g in headline.groupby("station"):
        print(f"  {st}: overall {rate(g)}")
        g24 = g[g["date"] >= "2020-01-01"]
        if len(g24):
            print(f"       2020+   {rate(g24)}")

    print("=" * 70)
    print("EXCEEDANCE BY ANTECEDENT 72H RAIN (prev3)")
    for st, g in headline.groupby("station"):
        print(f"  {st}:")
        for b, gb in g.groupby("rain_bin", observed=False):
            if len(gb):
                print(f"    {b:10s} {rate(gb)}")

    print("=" * 70)
    print("TRUE-DRY BASELINE (zero rain in prior 30 days)")
    for st, g in headline.groupby("station"):
        dry = g[g["prev30"] == 0]
        if len(dry):
            print(f"  {st}: {rate(dry)}")

    print("=" * 70)
    print("SEASONALITY (wet=Oct-Apr / dry=May-Sep)")
    for st, g in headline.groupby("station"):
        w, d = g[g["wet_season"]], g[~g["wet_season"]]
        print(f"  {st}: wet {rate(w)}   dry {rate(d)}")

    print("=" * 70)
    print("PREDICTIVE POWER (AUC of rain features for exceedance)")
    for st, g in headline.groupby("station"):
        aucs = {
            c: auc_mannwhitney(g[c], g["exceed"])
            for c in ["day0", "prev1", "prev3", "prev7", "prev14", "prev30", "season_cum"]
        }
        best = max(aucs, key=lambda k: aucs[k] if not np.isnan(aucs[k]) else 0)
        line = "  ".join(f"{k}={v:.2f}" for k, v in aucs.items())
        print(f"  {st}: {line}   best={best}")

    out = ROOT / "data" / "samples_with_features.csv"
    df.to_csv(out, index=False)
    print(f"\nfeature table -> {out}  ({len(df)} rows)")


if __name__ == "__main__":
    main()
