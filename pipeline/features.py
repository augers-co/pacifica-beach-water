"""Build the canonical daily rain-context table (`rain_context`) from
weather_daily (ERA5, 1998->present).

For every calendar day: antecedent totals, days since last rain event (two
thresholds), the size of that most recent event, water-year cumulative and
its percent-of-normal for the day of season (saturation proxy), and two
antecedent-precipitation-index stores. Join any sample table on `date`
(features use rain through the PRIOR day, so they are knowable at sample time).

Event definition: a run of consecutive days with >=1mm; event total = run sum.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"

RAIN_DAY_MM = 1.0
STORM_DAY_MM = 5.0


def water_year(idx):
    return idx.year + (idx.month >= 10).astype(int)


def build(p: pd.Series) -> pd.DataFrame:
    p = p.sort_index().astype(float).fillna(0)
    f = pd.DataFrame(index=p.index)
    f["rain_mm"] = p
    f["prev1"] = p.shift(1)
    for w in (3, 7, 14, 30):
        f[f"prev{w}"] = p.shift(1).rolling(w).sum()

    # events: consecutive runs of days >= RAIN_DAY_MM
    is_rain = p >= RAIN_DAY_MM
    event_id = (is_rain & ~is_rain.shift(1, fill_value=False)).cumsum().where(is_rain)
    event_total = p.groupby(event_id).transform("sum")

    # as-of yesterday: days since last rain day / storm day, and that event's size
    last_rain_day, last_storm_day, last_event_sz = {}, {}, {}
    lr, ls, sz = pd.NaT, pd.NaT, np.nan
    for d in p.index:
        last_rain_day[d] = lr
        last_storm_day[d] = ls
        last_event_sz[d] = sz
        if is_rain[d]:
            lr = d
            sz = event_total[d]
        if p[d] >= STORM_DAY_MM:
            ls = d
    f["days_since_rain"] = (f.index - pd.Series(last_rain_day)).dt.days
    f["days_since_storm"] = (f.index - pd.Series(last_storm_day)).dt.days
    f["last_event_mm"] = pd.Series(last_event_sz)

    # water-year cumulative through yesterday, and percent of normal-to-date
    wy = water_year(f.index)
    f["wy_cum"] = p.groupby(wy).cumsum().shift(1)
    doy = pd.Series(
        np.where(f.index.dayofyear >= 274, f.index.dayofyear - 273, f.index.dayofyear + 92),
        index=f.index,
    )  # day of water year (Oct 1 = 1), leap-fuzzy is fine
    normal = f.groupby(doy.values)["wy_cum"].transform("mean")
    f["wy_pct_normal"] = 100 * f["wy_cum"] / normal.replace(0, np.nan)

    # antecedent precipitation index stores (fast/slow recession)
    for name, k in [("api_fast", 0.90), ("api_slow", 0.97)]:
        s, vals = 0.0, []
        for v in p.shift(1).fillna(0):
            s = k * s + v
            vals.append(s)
        f[name] = vals

    # physically-lagged display indices (linear reservoir cascade):
    #   flow_idx: quick store, storm input split across day 0 and day 1
    #     F_t = 0.90 F_{t-1} + 0.5 P_t + 0.5 P_{t-1}
    #   ground_idx: charged by the quick store's drainage, so it crests
    #     days after the storm and drains over months
    #     G_t = 0.97 G_{t-1} + 0.10 F_{t-1}
    Fv, Gv, F, G, Fprev = [], [], 0.0, 0.0, 0.0
    pv = p.fillna(0).tolist()
    for i, rain in enumerate(pv):
        prev_rain = pv[i - 1] if i else 0.0
        Fprev = F
        F = 0.90 * F + 0.5 * rain + 0.5 * prev_rain
        G = 0.97 * G + 0.10 * Fprev
        Fv.append(F)
        Gv.append(G)
    f["flow_idx"] = Fv
    f["ground_idx"] = Gv
    return f


def main():
    con = sqlite3.connect(DB)
    wx = pd.read_sql("SELECT * FROM weather_daily", con)
    wx["date"] = pd.to_datetime(wx["date"])
    f = build(wx.set_index("date")["precip_mm"])
    f.reset_index(names="date").assign(date=lambda d: d.date.dt.strftime("%Y-%m-%d")).to_sql(
        "rain_context", con, if_exists="replace", index=False
    )
    con.close()
    print(f"rain_context: {len(f)} days, {f.index.min().date()} -> {f.index.max().date()}")
    print("columns:", ", ".join(f.columns))


if __name__ == "__main__":
    main()
