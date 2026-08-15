"""Beach (LM5) nowcast model v1 — the user-facing product target.

Same discipline as the creek model (pipeline/model.py): log10 enterococcus,
vetted features only, expanding-window walk-forward. Adds what the beach
uniquely supports: lagged creek state (the vector) and tide stage at the
sampling moment (transport). Tier framing per the product reset: default is
"typical/borderline"; the forecast's job is flagging big-deal departures.
"""

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
STD = 104.0

FEATURES = [
    ("log_flow", "storm water reaching the surf (est. creek flow)"),
    ("log_ground", "ground wetness"),
    ("days_since_rain", "days since last rain"),
    ("log_event", "size of the most recent rain event"),
    ("temp7", "warmth of the past week"),
    ("doy_sin", "season"),
    ("doy_cos", "season"),
    ("trend", "long-term drift"),
    ("tide_h", "tide height at sampling"),
    ("tide_ebb", "ebb tide at sampling"),
    ("creek_prev", "last creek reading (the vector)"),
    ("beach_roll4", "recent beach baseline (last 4 readings)"),
]


def build():
    con = sqlite3.connect(DB)
    b = pd.read_sql(
        """SELECT SampleDate, CollectionTime, Result FROM ceden_raw
           WHERE StationName LIKE '%#5%' AND Analyte LIKE '%Enterococcus%'""", con)
    b["date"] = pd.to_datetime(b.SampleDate).dt.normalize()
    b["hhmm"] = pd.to_datetime(b.CollectionTime, errors="coerce").dt.strftime("%H:%M")
    b["value"] = pd.to_numeric(b.Result, errors="coerce")
    b = (b.dropna(subset=["value"]).groupby("date", as_index=False)
         .agg(hhmm=("hhmm", "first"), value=("value", "max")).sort_values("date"))
    b = b[b.date >= "2015-01-01"].copy()
    b["ts"] = pd.to_datetime(b.date.dt.strftime("%Y-%m-%d") + " " + b.hhmm.fillna("09:30"))

    rc = pd.read_sql("SELECT * FROM rain_context", con)
    rc["date"] = pd.to_datetime(rc.date)
    ex = pd.read_sql("SELECT * FROM wx_extra_daily", con)
    ex["date"] = pd.to_datetime(ex.date)
    ex = ex.set_index("date")
    tide = pd.read_sql("SELECT * FROM tide_hourly", con)
    tide["dt"] = pd.to_datetime(tide.dt)
    tide["height_m"] = pd.to_numeric(tide.height_m)
    tide = tide.sort_values("dt").reset_index(drop=True)
    tide["dh"] = tide.height_m.diff()
    ck = pd.read_sql(
        """SELECT SampleDate, Result FROM ceden_raw
           WHERE StationName LIKE '%San Pedro Creek%' AND Analyte LIKE '%E. coli%'""", con)
    con.close()
    ck["date"] = pd.to_datetime(ck.SampleDate).dt.normalize()
    ck["value"] = pd.to_numeric(ck.Result, errors="coerce")
    ck = ck.dropna(subset=["value"]).groupby("date", as_index=False).value.max().sort_values("date")
    ck["ck_logc"] = np.log10(ck.value.clip(lower=1))

    df = b.merge(rc, on="date", how="left")
    df["temp7"] = df.date.map(
        lambda d: ex.temp_mean.loc[d - pd.Timedelta(days=7): d - pd.Timedelta(days=1)].mean())
    df = pd.merge_asof(df.sort_values("ts"), tide[["dt", "height_m", "dh"]],
                       left_on="ts", right_on="dt", direction="nearest")
    df = pd.merge_asof(df.sort_values("date"),
                       ck[["date", "ck_logc"]].rename(columns={"date": "ck_date"}),
                       left_on="date", right_on="ck_date",
                       allow_exact_matches=False, tolerance=pd.Timedelta("10d"))
    df["logc"] = np.log10(df.value.clip(lower=1))
    df["log_flow"] = np.log10(df.flow_idx.clip(lower=0.5))
    df["log_ground"] = np.log10(df.ground_idx.clip(lower=1))
    df["log_event"] = np.log10(df.last_event_mm.clip(lower=0.5))
    df["days_since_rain"] = df.days_since_rain.clip(upper=120)
    doy = df.date.dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365)
    df["trend"] = df.date.dt.year + doy / 365 - 2015
    df["tide_h"] = df.height_m
    df["tide_ebb"] = (df.dh < -0.05).astype(float)
    df["creek_prev"] = df.ck_logc
    df["beach_roll4"] = df.logc.shift(1).rolling(4, min_periods=2).mean()
    df["exceed"] = df.value > STD
    df["rain_rule"] = df.prev3 > 0
    return df.dropna(subset=["logc", "log_flow", "temp7", "beach_roll4"]).reset_index(drop=True)


def ridge_fit(X, y, alpha=1.0):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    beta = np.linalg.solve(Z.T @ Z + alpha * np.diag([0] + [1] * X.shape[1]), Z.T @ y)
    sigma = (y - Z @ beta).std(ddof=Z.shape[1])
    return {"beta": beta, "mu": mu, "sd": sd, "sigma": sigma}


def ridge_predict(m, X):
    Z = np.hstack([np.ones((len(X), 1)), (X - m["mu"]) / m["sd"]])
    return Z @ m["beta"]


def auc(score, y):
    y = np.asarray(y, bool)
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    rk = pd.Series(score).rank().to_numpy()
    return (rk[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())


def main():
    df = build()
    cols = [f for f, _ in FEATURES]
    print(f"beach frame: n={len(df)}, {df.date.min().date()} -> {df.date.max().date()}")
    fill = df.creek_prev.mean()

    rows, oos = [], []
    for ty in range(2019, 2027):
        tr = df[df.date.dt.year < ty].copy()
        te = df[df.date.dt.year == ty].copy()
        if len(te) < 20 or len(tr) < 100:
            continue
        for d in (tr, te):
            d.loc[:, "creek_prev"] = d.creek_prev.fillna(tr.creek_prev.mean() if len(tr) else fill)
        m = ridge_fit(tr[cols].to_numpy(float), tr.logc.to_numpy())
        te = te.assign(pred=ridge_predict(m, te[cols].to_numpy(float)))
        oos.append(te)
        rows.append({"year": ty, "n": len(te),
                     "AUC_model": auc(te.pred, te.exceed),
                     "AUC_rain": auc(te.rain_rule.astype(float), te.exceed),
                     "AUC_bigdeal": auc(te.pred, te.value > 10 * STD)})
    rep = pd.DataFrame(rows)
    print("\n== WALK-FORWARD OOS BY YEAR ==")
    print(rep.round(2).to_string(index=False))

    o = pd.concat(oos)
    print(f"\n== POOLED OOS (n={len(o)}) ==")
    print(f"  AUC exceedance (>104)      = {auc(o.pred, o.exceed):.2f}")
    print(f"  AUC folk rain rule         = {auc(o.rain_rule.astype(float), o.exceed):.2f}")
    print(f"  AUC big-deal (>10x std)    = {auc(o.pred, o.value > 1040):.2f}   (n_pos={ (o.value>1040).sum() })")
    print(f"  AUC serious (>3x std)      = {auc(o.pred, o.value > 312):.2f}   (n_pos={ (o.value>312).sum() })")

    print("\n== TIER CALIBRATION (OOS, predicted concentration) ==")
    o = o.assign(predC=10 ** o.pred)
    for name, lo, hi in [("cleaner (<52)", 0, 52), ("typical (52-208)", 52, 208),
                         ("elevated (208-1040)", 208, 1040), ("high (>1040)", 1040, 1e9)]:
        g = o[(o.predC >= lo) & (o.predC < hi)]
        if len(g):
            print(f"  {name:20s} n={len(g):3d}  actual geo-mean {10**g.logc.mean():5.0f}  "
                  f">104: {(g.value>104).mean()*100:3.0f}%  >1040: {(g.value>1040).mean()*100:3.0f}%")

    df.loc[:, "creek_prev"] = df.creek_prev.fillna(fill)
    m = ridge_fit(df[cols].to_numpy(float), df.logc.to_numpy())
    print("\n== STANDARDIZED COEFFICIENTS (final fit) ==")
    for (f, label), bta in zip(FEATURES, m["beta"][1:]):
        print(f"  {f:15s} {bta:+.3f}  {label}")
    print(f"  residual sigma = {m['sigma']:.2f}")

    out = {"target": "log10 LM5 enterococcus, standard 104",
           "features": cols, "labels": dict(FEATURES),
           "beta": m["beta"].tolist(), "mu": m["mu"].tolist(), "sd": m["sd"].tolist(),
           "sigma": float(m["sigma"]), "creek_prev_fill": float(fill),
           "trained_through": str(df.date.max().date()), "n": int(len(df))}
    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "models" / "beach_v1.json").write_text(json.dumps(out, indent=1))
    print("\nsaved -> models/beach_v1.json")


if __name__ == "__main__":
    main()
