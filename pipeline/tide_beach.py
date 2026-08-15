"""Tide state at the actual sampling moment vs LM5 beach enterococcus.

The beach model (model_beach.py) carries a tide-at-sampling coefficient; this
script shows the correlation directly instead of leaving it inside a ridge fit.

Method
------
- Samples: CEDEN LM5 enterococcus with a recorded CollectionTime (the
  "00:00:00" sentinel rows are dropped as missing-time). Same-date replicates
  collapse to the max (register §7).
- Tide: NOAA CO-OPS harmonic predictions, Princeton/Half Moon Bay station
  9414131 (open coast; see inferences.md §6 for the SF-gauge correction),
  hourly, local clock (lst_ldt) — deterministic, so historical values are
  exact.
  Height and rate at the sampling minute are linearly interpolated; each
  sample also gets a phase = signed hours from the nearest high water
  (parabola-refined local maxima), negative before high (flood), positive
  after (ebb).
- Controls: rain_context by date (the dominant confounder), season, hour.

Outputs: printed stats + docs/charts/tide_phase_lm5.png
"""

import sqlite3
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
OUT = ROOT / "docs" / "charts"
STD = 104
RNG = np.random.default_rng(11)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
LM5 = "#eb6834"
DRY = "#8a5a00"

plt.rcParams.update(
    {
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "axes.edgecolor": BASE,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "figure.dpi": 200,
    }
)


def load():
    con = sqlite3.connect(DB)
    b = pd.read_sql(
        """SELECT SampleDate, CollectionTime, Result FROM ceden_raw
           WHERE StationName LIKE '%#5%' AND Analyte LIKE '%Enterococcus%'""",
        con,
    )
    tide = pd.read_sql("SELECT * FROM tide_hourly", con)
    rc = pd.read_sql(
        "SELECT date, prev3, prev7, days_since_rain FROM rain_context", con
    )
    con.close()

    b["date"] = pd.to_datetime(b.SampleDate).dt.normalize()
    b["time"] = pd.to_datetime(b.CollectionTime, errors="coerce")
    b["hhmm"] = b.time.dt.strftime("%H:%M")
    b = b[b.hhmm != "00:00"]  # midnight = missing-time sentinel (149 rows)
    b["value"] = pd.to_numeric(b.Result, errors="coerce")
    b = (
        b.dropna(subset=["value"])
        .groupby("date", as_index=False)
        .agg(hhmm=("hhmm", "first"), value=("value", "max"))
    )
    b["ts"] = pd.to_datetime(b.date.dt.strftime("%Y-%m-%d") + " " + b.hhmm)

    tide["dt"] = pd.to_datetime(tide.dt)
    tide["h"] = pd.to_numeric(tide.height_m)
    tide = tide.sort_values("dt").reset_index(drop=True)

    # interpolated height + rate at the sampling minute
    tt = tide.dt.values.astype("datetime64[s]").astype(np.int64)
    hh = tide.h.values
    st = b.ts.values.astype("datetime64[s]").astype(np.int64)
    b["tide_h"] = np.interp(st, tt, hh)
    b["tide_rate"] = (np.interp(st + 1800, tt, hh) - np.interp(st - 1800, tt, hh))  # m/hr

    # high-water times: local maxima, parabola-refined to minutes
    m = (hh[1:-1] >= hh[:-2]) & (hh[1:-1] > hh[2:])
    idx = np.where(m)[0] + 1
    denom = hh[idx - 1] - 2 * hh[idx] + hh[idx + 1]
    off = np.where(denom < 0, 0.5 * (hh[idx - 1] - hh[idx + 1]) / denom, 0.0)
    highs = tt[idx] + off * 3600
    near = np.searchsorted(highs, st)
    near = np.clip(near, 1, len(highs) - 1)
    prev_gap = st - highs[near - 1]
    next_gap = highs[near] - st
    signed = np.where(prev_gap <= next_gap, prev_gap, -next_gap) / 3600.0
    b["phase_h"] = signed  # negative = before high (flood), positive = after (ebb)

    rc["date"] = pd.to_datetime(rc.date)
    b = b.merge(rc, on="date", how="left")
    b["exceed"] = b.value > STD
    b["nd"] = False
    b["logc"] = np.log10(b.value.clip(lower=1))
    b["ebb"] = b.tide_rate < 0
    return b.reset_index(drop=True)


def gm(v):
    return 10 ** np.log10(v.clip(lower=1)).mean()


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - hw, c + hw


def contrast(df, label):
    e, f = df[df.ebb], df[~df.ebb]
    pe, pf = e.exceed.mean(), f.exceed.mean()
    rr = pe / pf if pf > 0 else np.nan
    # bootstrap CI on the relative risk
    rrs = []
    for _ in range(4000):
        se = e.exceed.sample(len(e), replace=True).mean()
        sf = f.exceed.sample(len(f), replace=True).mean()
        if sf > 0:
            rrs.append(se / sf)
    lo, hi = np.percentile(rrs, [2.5, 97.5])
    # permutation p on the exceedance difference
    pool = df.exceed.values
    obs = pe - pf
    ne = len(e)
    perm = np.array(
        [np.abs(np.mean(s[:ne]) - np.mean(s[ne:]))
         for s in (RNG.permutation(pool) for _ in range(20000))]
    )
    p = (perm >= abs(obs)).mean()
    print(f"\n{label}  (n={len(df)}: ebb {len(e)}, flood {len(f)})")
    print(f"  ebb   : {pe:5.1%} exceed, geo-mean {gm(e.value):6.1f}")
    print(f"  flood : {pf:5.1%} exceed, geo-mean {gm(f.value):6.1f}")
    print(f"  RR ebb/flood {rr:.2f}  [95% CI {lo:.2f}-{hi:.2f}]  perm p={p:.4f}")
    return rr, lo, hi, p


def phase_curve(df, nbins=6):
    edges = np.linspace(-6.21, 6.21, nbins + 1)
    rows = []
    for a, z in zip(edges[:-1], edges[1:]):
        s = df[(df.phase_h >= a) & (df.phase_h < z)]
        if len(s) < 10:
            continue
        lo, hi = wilson(s.exceed.sum(), len(s))
        rows.append(dict(mid=(a + z) / 2, n=len(s), p=s.exceed.mean(),
                         lo=lo, hi=hi, gmv=gm(s.value)))
    return pd.DataFrame(rows)


def main():
    b = load()
    print(f"LM5 enterococcus with recorded sampling time: n={len(b)}, "
          f"{b.date.min():%Y-%m-%d} → {b.date.max():%Y-%m-%d}")
    print(f"sampling times: {b.hhmm.min()}–{b.hhmm.max()}, "
          f"median {b.hhmm.median() if False else b.hhmm.mode()[0]}")

    # confounder balance: tide state should be as-good-as-random vs weather
    e, f = b[b.ebb], b[~b.ebb]
    print("\nBalance check (ebb vs flood):")
    print(f"  prev7 rain mean : {e.prev7.mean():.1f} vs {f.prev7.mean():.1f} mm")
    print(f"  dry>=3d share   : {(e.days_since_rain>=3).mean():.1%} vs "
          f"{(f.days_since_rain>=3).mean():.1%}")
    print(f"  winter share    : {(e.date.dt.month.isin([11,12,1,2,3])).mean():.1%} vs "
          f"{(f.date.dt.month.isin([11,12,1,2,3])).mean():.1%}")
    hr = b.ts.dt.hour + b.ts.dt.minute / 60
    print(f"  corr(phase, hour-of-day) = {np.corrcoef(b.phase_h, hr)[0,1]:+.3f}")

    contrast(b, "ALL DAYS")
    dry3 = b[b.days_since_rain >= 3]
    contrast(dry3, "DRY >=3 DAYS (storm influence excluded)")
    dry7 = b[b.days_since_rain >= 7]
    contrast(dry7, "DRY >=7 DAYS")

    # phase-window contrast: around high water vs around low water
    def window_contrast(df, label):
        hi = df[df.phase_h.abs() <= 2.07]
        lo = df[df.phase_h.abs() >= 4.14]
        ph, pl = hi.exceed.mean(), lo.exceed.mean()
        rrs = []
        for _ in range(4000):
            sh = hi.exceed.sample(len(hi), replace=True).mean()
            sl = lo.exceed.sample(len(lo), replace=True).mean()
            if sh > 0:
                rrs.append(sl / sh)
        clo, chi = np.percentile(rrs, [2.5, 97.5])
        pool = pd.concat([hi, lo]).exceed.values
        obs = pl - ph
        nlo = len(lo)
        perm = np.array([abs(np.mean(x[:nlo]) - np.mean(x[nlo:]))
                         for x in (RNG.permutation(pool) for _ in range(20000))])
        p = (perm >= abs(obs)).mean()
        print(f"\n{label} — around high (|ph|<=2.07h) vs around low (|ph|>=4.14h)")
        print(f"  high-water window: {ph:5.1%} exceed, geo-mean {gm(hi.value):6.1f}, ND {hi.nd.mean() if 'nd' in hi else float('nan'):5.1%}  n={len(hi)}")
        print(f"  low-water window : {pl:5.1%} exceed, geo-mean {gm(lo.value):6.1f}, ND {lo.nd.mean() if 'nd' in lo else float('nan'):5.1%}  n={len(lo)}")
        print(f"  RR low/high {pl/ph:.2f}  [95% CI {clo:.2f}-{chi:.2f}]  perm p={p:.4f}")

    window_contrast(b, "ALL DAYS")
    window_contrast(dry3, "DRY >=3 DAYS")

    # height (stage) check — expected null from prior work
    print("\nTide HEIGHT terciles (all days):")
    b["htier"] = pd.qcut(b.tide_h, 3, labels=["low", "mid", "high"])
    for t, s in b.groupby("htier", observed=True):
        print(f"  {t:4}: {s.exceed.mean():5.1%} exceed, geo-mean {gm(s.value):6.1f}, n={len(s)}")

    # OLS robustness: log-concentration on ebb with rain/season controls
    X = np.column_stack([
        np.ones(len(b)),
        b.ebb.astype(float),
        np.log10(b.prev3.values + 1),
        np.log10(b.prev7.values + 1),
        np.minimum(b.days_since_rain.values, 60),
        np.sin(2 * np.pi * b.date.dt.dayofyear / 365),
        np.cos(2 * np.pi * b.date.dt.dayofyear / 365),
    ])
    beta, *_ = np.linalg.lstsq(X, b.logc.values, rcond=None)
    naive, *_ = np.linalg.lstsq(X[:, :2], b.logc.values, rcond=None)
    print(f"\nOLS log10(entero) ebb coefficient: naive {naive[1]:+.3f}, "
          f"with rain+season controls {beta[1]:+.3f} "
          f"(x{10**beta[1]:.2f} concentration)")

    # figure: exceedance by tide phase
    pc_all = phase_curve(b)
    pc_dry = phase_curve(dry3)
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.xaxis.grid(False)
    ax.tick_params(length=0)
    for pc, col, lab in ((pc_all, LM5, "all days"),
                         (pc_dry, DRY, "dry ≥3 days")):
        ax.errorbar(pc.mid, pc.p * 100,
                    yerr=[(pc.p - pc.lo) * 100, (pc.hi - pc.p) * 100],
                    fmt="o-", color=col, lw=1.6, ms=5, capsize=3, label=lab)
    ax.axvline(0, color=BASE, lw=1)
    ax.text(0.12, ax.get_ylim()[0] + 0.5, "high water", ha="left", va="bottom",
            fontsize=8.5, color=MUTED)
    ax.set_xlabel("hours from high water at the sampling minute  "
                  "(← flood rising | ebb falling →)")
    ax.set_ylabel("% of samples over the 104 standard")
    ax.set_title("Linda Mar Beach #5: enterococcus vs tide phase at the "
                 "recorded collection time", fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "tide_phase_lm5.png")
    print(f"\nwrote {OUT/'tide_phase_lm5.png'}")
    for name, pc in (("all", pc_all), ("dry3", pc_dry)):
        print(f"  phase bins ({name}): " +
              ", ".join(f"{r.mid:+.1f}h {r.p:.0%} (n={r.n})" for r in pc.itertuples()))


if __name__ == "__main__":
    main()
