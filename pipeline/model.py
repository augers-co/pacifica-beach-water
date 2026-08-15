"""Creek nowcast model v1: ridge regression on log10 E. coli concentration.

Design (each choice traces to a finding):
  - Target: log10 concentration, not exceedance (v3/v4: threshold straddles the
    distribution; two labs flip the label 20% of the time).
  - Features: only individually-vetted terms (v2-v7). No kitchen sink.
  - Validation: expanding-window walk-forward by calendar year — every score is
    out-of-sample. Benchmarks: climatology, persistence, the folk rain rule.
  - P(exceed) = Phi((log320 - mu)/sigma) from the train-fold residual sigma, so
    probabilities come calibrated from the concentration model.
  - Attribution: standardized terms make each prediction decomposable into
    named contributions (the app's "why" layer).

Writes models/creek_v1.json (coefficients + scaling + sigma) for downstream use.
"""

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
STD = 320.0
RIDGE_ALPHA = 1.0

FEATURES = [
    ("log_flow", "storm water in the creek (est. flow)"),
    ("log_ground", "ground wetness (est. water table)"),
    ("days_since_rain", "days since last rain"),
    ("log_event", "size of the most recent rain event"),
    ("wy_pct", "winter-to-date rainfall vs normal"),
    ("temp7", "warmth of the past week"),
    ("hour", "sampling hour"),
    ("doy_sin", "season (annual cycle)"),
    ("doy_cos", "season (annual cycle)"),
    ("trend", "long-term drift"),
    ("prev_logc", "last creek reading (persistence)"),
    ("prev_stale", "staleness of last reading"),
    ("roll4", "recent creek baseline (last 4 readings)"),
]


def build_frame():
    con = sqlite3.connect(DB)
    ck = pd.read_sql(
        """SELECT SampleDate, CollectionTime, Result FROM ceden_raw
           WHERE StationName LIKE '%San Pedro Creek%' AND Analyte LIKE '%E. coli%'""",
        con,
    )
    ck["date"] = pd.to_datetime(ck.SampleDate).dt.normalize()
    ck["hour"] = pd.to_datetime(ck.CollectionTime, errors="coerce").dt.hour
    ck["value"] = pd.to_numeric(ck.Result, errors="coerce")
    ck = (
        ck.dropna(subset=["value"])
        .groupby("date", as_index=False)
        .agg(hour=("hour", "first"), value=("value", "max"))
        .sort_values("date")
    )
    rc = pd.read_sql("SELECT * FROM rain_context", con)
    rc["date"] = pd.to_datetime(rc.date)
    ex = pd.read_sql("SELECT * FROM wx_extra_daily", con)
    ex["date"] = pd.to_datetime(ex.date)
    ex = ex.set_index("date")
    con.close()

    df = ck.merge(rc, on="date", how="left")
    df["temp7"] = df.date.map(
        lambda d: ex.temp_mean.loc[d - pd.Timedelta(days=7): d - pd.Timedelta(days=1)].mean()
    )
    df["logc"] = np.log10(df.value.clip(lower=1))
    df["log_flow"] = np.log10(df.flow_idx.clip(lower=0.5))
    df["log_ground"] = np.log10(df.ground_idx.clip(lower=1))
    df["log_event"] = np.log10(df.last_event_mm.clip(lower=0.5))
    df["wy_pct"] = df.wy_pct_normal.fillna(100).clip(upper=300)
    df["days_since_rain"] = df.days_since_rain.clip(upper=120)
    doy = df.date.dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365)
    df["trend"] = df.date.dt.year + doy / 365 - 2015
    df["hour"] = df.hour.fillna(df.hour.median())
    # persistence: previous sample >= 1 day earlier
    df["prev_logc"] = df.logc.shift(1)
    df["prev_age"] = df.date.diff().dt.days
    stale = (df.prev_age > 14) | df.prev_logc.isna()
    df["prev_stale"] = stale.astype(float)
    df.loc[stale, "prev_logc"] = np.nan  # imputed with train mean per fold
    # trailing regime baseline: mean of the last 4 readings (the chronic level
    # moves on month scales — v3 persistence; this is what tracks it)
    df["roll4"] = df.logc.shift(1).rolling(4, min_periods=2).mean()
    df["exceed"] = df.value > STD
    df["rain_rule"] = df.prev3 > 0
    return df.dropna(subset=["logc", "log_flow", "temp7", "roll4"]).reset_index(drop=True)


def ridge_fit(X, y, alpha):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = (X - mu) / sd
    Z1 = np.hstack([np.ones((len(Z), 1)), Z])
    A = Z1.T @ Z1 + alpha * np.diag([0] + [1] * Z.shape[1])
    beta = np.linalg.solve(A, Z1.T @ y)
    resid = y - Z1 @ beta
    sigma = resid.std(ddof=Z1.shape[1])
    return {"beta": beta, "mu": mu, "sd": sd, "sigma": sigma}


def ridge_predict(m, X):
    Z = (X - m["mu"]) / m["sd"]
    return np.hstack([np.ones((len(Z), 1)), Z]) @ m["beta"]


def auc(score, y):
    y = np.asarray(y, bool)
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    rk = pd.Series(score).rank().to_numpy()
    return (rk[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())


def main():
    df = build_frame()
    cols = [f for f, _ in FEATURES]
    print(f"model frame: n={len(df)}, {df.date.min().date()} -> {df.date.max().date()}")

    rows, oos = [], []
    for test_year in range(2019, 2027):
        tr = df[df.date.dt.year < test_year].copy()
        te = df[df.date.dt.year == test_year].copy()
        if len(te) < 20 or len(tr) < 100:
            continue
        fill = tr.prev_logc.mean()
        for d in (tr, te):
            d.loc[:, "prev_logc"] = d.prev_logc.fillna(fill)
        m = ridge_fit(tr[cols].to_numpy(float), tr.logc.to_numpy(), RIDGE_ALPHA)
        pred = ridge_predict(m, te[cols].to_numpy(float))
        te = te.assign(pred=pred)
        te = te.assign(p_exc=1 - 0.5 * (1 + np.array(
            [math.erf((np.log10(STD) - p) / (m["sigma"] * np.sqrt(2))) for p in pred])))
        oos.append(te)
        ss_res = ((te.logc - te.pred) ** 2).sum()
        ss_clim = ((te.logc - tr.logc.mean()) ** 2).sum()
        ss_pers = ((te.logc - te.prev_logc) ** 2).sum()
        rows.append({
            "year": test_year, "n": len(te),
            "R2_model": 1 - ss_res / ss_clim,
            "R2_persist": 1 - ss_pers / ss_clim,
            "AUC_model": auc(te.p_exc, te.exceed),
            "AUC_rainrule": auc(te.rain_rule.astype(float), te.exceed),
        })

    rep = pd.DataFrame(rows)
    print("\n== WALK-FORWARD, OUT-OF-SAMPLE BY YEAR ==")
    print(rep.round(2).to_string(index=False))

    o = pd.concat(oos)
    ss_res = ((o.logc - o.pred) ** 2).sum()
    ss_tot = ((o.logc - o.logc.mean()) ** 2).sum()
    print(f"\n== POOLED OUT-OF-SAMPLE (n={len(o)}) ==")
    print(f"  R2 (logC)            = {1 - ss_res/ss_tot:.2f}")
    print(f"  AUC exceedance       = {auc(o.p_exc, o.exceed):.2f}")
    print(f"  AUC folk rain rule   = {auc(o.rain_rule.astype(float), o.exceed):.2f}")
    print(f"  AUC persistence only = {auc(o.prev_logc, o.exceed):.2f}")
    # classifier comparison at matched flag rate: flag same share of days as rain rule
    k = int(o.rain_rule.mean() * len(o))
    thr = np.sort(o.p_exc)[::-1][k - 1]
    flag = o.p_exc >= thr
    for name, fl in [("model (same # flags)", flag), ("folk rain rule", o.rain_rule)]:
        sens = (fl & o.exceed).sum() / o.exceed.sum()
        fpr = (fl & ~o.exceed).sum() / (~o.exceed).sum()
        print(f"  {name:22s} catches {sens*100:3.0f}% of bad days | wrongly kills {fpr*100:3.0f}% of good days")

    # tier framing: default = "typical/borderline"; the forecast's job is
    # flagging departures. Tiers on predicted concentration, verified OOS.
    print("\n== TIER CALIBRATION (out-of-sample): 'flag the big-deal days' ==")
    o = o.assign(predC=10 ** o.pred)
    tiers = [("cleaner (<160)", 0, 160), ("typical (160-640)", 160, 640),
             ("elevated (640-2000)", 640, 2000), ("high (>2000)", 2000, 1e9)]
    for name, lo, hi in tiers:
        g = o[(o.predC >= lo) & (o.predC < hi)]
        if len(g) == 0:
            continue
        gm = 10 ** g.logc.mean()
        print(f"  {name:20s} n={len(g):3d}  actual geo-mean {gm:6.0f}  "
              f">320: {(g.value>320).mean()*100:3.0f}%  >1000: {(g.value>1000).mean()*100:3.0f}%")
    print(f"  AUC for 'big-deal' days (>1000): {auc(o.pred, o.value>1000):.2f}")
    print(f"  AUC for extreme days (>3200):    {auc(o.pred, o.value>3200):.2f}")

    # final model on all data + attribution demo
    fill = df.prev_logc.mean()
    df.loc[:, "prev_logc"] = df.prev_logc.fillna(fill)
    m = ridge_fit(df[cols].to_numpy(float), df.logc.to_numpy(), RIDGE_ALPHA)
    print("\n== STANDARDIZED COEFFICIENTS (final fit, all data) ==")
    for (f, label), b in zip(FEATURES, m["beta"][1:]):
        print(f"  {f:16s} {b:+.3f}   {label}")
    print(f"  residual sigma = {m['sigma']:.2f} log10 (grab noise floor ~0.3-0.4)")

    print("\n== ATTRIBUTION DEMO (last 3 samples) ==")
    Z = (df[cols].to_numpy(float) - m["mu"]) / m["sd"]
    for i in range(len(df) - 3, len(df)):
        contrib = Z[i] * m["beta"][1:]
        top = np.argsort(-np.abs(contrib))[:3]
        parts = ", ".join(f"{FEATURES[j][1]} {contrib[j]:+.2f}" for j in top)
        print(f"  {df.date.iloc[i].date()}  actual={df.value.iloc[i]:5.0f}  "
              f"pred={10**ridge_predict(m, df[cols].iloc[[i]].to_numpy(float))[0]:5.0f}  drivers: {parts}")

    out = {
        "target": "log10 creek E.coli, standard 320",
        "features": cols, "labels": dict(FEATURES),
        "beta": m["beta"].tolist(), "mu": m["mu"].tolist(), "sd": m["sd"].tolist(),
        "sigma": float(m["sigma"]), "prev_logc_fill": float(fill),
        "trained_through": str(df.date.max().date()), "n": int(len(df)),
    }
    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "models" / "creek_v1.json").write_text(json.dumps(out, indent=1))
    print("\nsaved -> models/creek_v1.json")


if __name__ == "__main__":
    main()
