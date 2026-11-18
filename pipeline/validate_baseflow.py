"""Check the groundwater stand-ins, and the assumptions behind them, against
groundwater that was actually measured.

The State Water Board's GeoTracker database holds depth-to-water readings from
monitoring wells at cleanup sites. Five such sites sit in the San Pedro Creek
valley. They were read from 2002 to 2016 and then stopped, so they can test
our assumptions for those years; nothing measures the valley's water table
today. This script downloads the county files, builds each well's level
relative to its own typical level, and reports:

  1. how closely the two stand-ins move with the measured water table
       baseflow_daily.baseflow_cfs  (dry-weather flow at three neighbouring creeks)
       rain_context.ground_idx      (the rain-derived ground-wetness index)
  2. whether the ground index's assumed drain rate (keeps 97% a day) is the
     rate the wells support
  3. whether rain-gauge readings would drive that index better than the
     weather-model rain it uses
  4. whether the water table lags the stand-ins, and whether a 7-day minimum
     is the right window for dry-weather flow
  5. whether a wet winter leaves a higher water table the following summer
  6. whether the measured water table moves with bacteria, where the two
     records overlap
  7. summer by summer, whether the creek's rain-free level follows the
     winter's rain (the page's "Wet winters" view) or that summer's
     dry-weather flow at the neighbouring creeks

Correlations with the wells are rank correlations computed within each site
(site means removed), so sites with different depths cannot manufacture a
relationship. Not part of the weekly refresh. Run after fetch_flow.py and
features.py:  .venv/bin/python3 pipeline/validate_baseflow.py
"""

import io
import sqlite3
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
BASE = "https://documents.geotracker.waterboards.ca.gov/data_download/geo_by_county/"
ACIS = "https://data.rcc-acis.org/StnData"
VALLEY = dict(lat=(37.572, 37.602), lon=(-122.512, -122.455))   # San Pedro Creek valley floor
PACIFICA = dict(lat=(37.56, 37.67), lon=(-122.52, -122.44))
CORE = ["pescadero", "san_gregorio", "pilarcitos"]
DRAIN_RATES = (0.90, 0.94, 0.96, 0.97, 0.98, 0.985, 0.99, 0.993, 0.996)
# Rain gauges (NOAA ACIS ids). The valley's official station closed in 2012;
# the nearest complete record since then is a volunteer gauge outside the valley.
VALLEY_GAUGE, VALLEY_GAUGE_END = "USC00046599", "2012-11-30"    # Pacifica 4 SSE, 1983-2012
NEARBY_GAUGE, NEARBY_GAUGE_START = "US1CASM0001", "2008-06-01"  # Pacifica 0.3 W, under 2 mi north


# ------------------------------------------------------------------ inputs
def county_file(name, ncol):
    """GeoTracker's tab-delimited county export; free-text columns can contain
    stray tabs, so only the leading fixed columns are kept."""
    r = requests.get(BASE + name, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    rows = [ln.split("\t")[:ncol] for ln in z.read(z.namelist()[0]).decode("latin-1").splitlines() if ln.count("\t") >= ncol - 1]
    return pd.DataFrame(rows[1:], columns=rows[0])


def inside(df, box):
    return df.lat.between(*box["lat"]) & df.lon.between(*box["lon"])


def well_visits():
    """One row per cleanup site per visit: the water table's height (ft) above
    that site's own typical level, averaged over the site's wells."""
    w = county_file("SanMateoGeoWell.zip", 7)
    xy = county_file("SanMateoGeoXY.zip", 7)
    w["date"] = pd.to_datetime(w.GW_MEAS_DATE, errors="coerce")
    w["dtw"] = pd.to_numeric(w.DTW, errors="coerce")
    w = w[(w.date >= "2001-01-01") & (w.dtw > 0) & (w.dtw < 200)].copy()
    xy["lat"], xy["lon"] = pd.to_numeric(xy.LATITUDE, errors="coerce"), pd.to_numeric(xy.LONGITUDE, errors="coerce")
    site = xy.dropna(subset=["lat", "lon"]).groupby("GLOBAL_ID")[["lat", "lon"]].median()
    w = w.join(site, on="GLOBAL_ID").dropna(subset=["lat"])
    w = w[inside(w, PACIFICA)].copy()
    w["well"] = w.GLOBAL_ID + "|" + w.FIELD_POINT_NAME
    w = w[w.groupby("well").dtw.transform("size") >= 6]
    w["lvl"] = w.groupby("well").dtw.transform("median") - w.dtw          # feet above the well's typical level
    w = w[w.lvl.abs() < 15]
    w["valley"] = inside(w, VALLEY)
    return w.groupby(["GLOBAL_ID", "date", "valley"], as_index=False).agg(lvl=("lvl", "mean"), dtw=("dtw", "median"))


def table(con, sql):
    return pd.read_sql(sql, con, parse_dates=["date"]).set_index("date")


def gauge_rain(sid):
    """Daily rain (mm) at one gauge from NOAA's ACIS service; unreported days are NaN."""
    r = requests.get(ACIS, timeout=120, params={"sid": sid, "sdate": "1998-01-01", "elems": "pcpn",
                                                "edate": pd.Timestamp.now().strftime("%Y-%m-%d")})
    r.raise_for_status()
    out = {}
    for day, v in r.json()["data"]:
        v = v[0] if isinstance(v, list) else v
        try:
            out[pd.Timestamp(day)] = 0.0 if v == "T" else float(v.rstrip("A")) * 25.4
        except ValueError:
            out[pd.Timestamp(day)] = np.nan
    return pd.Series(out)


def bacteria(con, sql):
    """Daily maximum per sampling day, as log10."""
    df = pd.read_sql(sql, con)
    df["date"] = pd.to_datetime(df.d, errors="coerce").dt.tz_localize(None).dt.normalize()
    df["v"] = pd.to_numeric(df.v, errors="coerce")
    g = df.dropna().groupby("date", as_index=False).v.max()
    return g.assign(logc=np.log10(g.v.clip(lower=1)))


# ------------------------------------------------------------------ statistics
def rho(visits, s, by="GLOBAL_ID"):
    """Rank correlation between a daily series and the well levels, with the
    mean of each group (site, or calendar month) removed from both."""
    x = visits.assign(c=s.reindex(visits.date).to_numpy()).dropna(subset=["c"])
    if by == "month":
        x = x.assign(month=x.date.dt.month)
    a = x.c - x.groupby(by)["c"].transform("mean")
    b = x.lvl - x.groupby(by)["lvl"].transform("mean")
    return pd.concat([a, b], axis=1).corr(method="spearman").iloc[0, 1], len(x)


def corr_p(a, b, rank=False, n=10000):
    """Correlation and a two-sided permutation p-value."""
    a, b = pd.Series(np.asarray(a, float)), pd.Series(np.asarray(b, float))
    if rank:
        a, b = a.rank(), b.rank()
    a, b = a.to_numpy(), b.to_numpy()
    obs = np.corrcoef(a, b)[0, 1]
    rng = np.random.default_rng(41)
    hits = sum(abs(np.corrcoef(a, rng.permutation(b))[0, 1]) >= abs(obs) - 1e-12 for _ in range(n))
    return obs, hits / n


def ground(rain, keep=0.97):
    """features.py's ground index (as log10), rebuilt from daily rain with a
    chosen share kept per day."""
    F = G = prev = 0.0
    out = np.empty(len(rain))
    for i, r in enumerate(rain.to_numpy()):
        Fprev = F
        F = 0.90 * F + 0.5 * r + 0.5 * prev
        G = keep * G + 0.10 * Fprev
        out[i], prev = G, r
    return pd.Series(np.log10(np.clip(out, 1, None)), index=rain.index)


def dry_weather_flow(flows, days):
    """Lowest flow of the trailing `days` at each core creek, averaged in log space."""
    lows = np.log10(flows[CORE].clip(lower=0.01)).rolling(days, min_periods=max(2, round(days * 5 / 7))).min()
    return lows.mean(axis=1).where(lows.notna().sum(axis=1) >= 2)


# ------------------------------------------------------------------ report
def main():
    ev = well_visits()
    v, other = ev[ev.valley], ev[~ev.valley]
    print(f"valley sites: {v.GLOBAL_ID.nunique()}, site visits: {len(v)}, {v.date.min().date()} .. {v.date.max().date()}")
    print(f"all Pacifica sites: {ev.GLOBAL_ID.nunique()}, site visits: {len(ev)}, {ev.date.min().date()} .. {ev.date.max().date()}")
    print(f"depth to water in the valley: median {v.dtw.median():.1f} ft; Jan-Apr {v[v.date.dt.month <= 4].dtw.median():.1f} ft; "
          f"Aug-Oct {v[v.date.dt.month.isin([8, 9, 10])].dtw.median():.1f} ft")

    con = sqlite3.connect(DB)
    bf = table(con, "SELECT date, baseflow_cfs FROM baseflow_daily").baseflow_cfs
    rc = table(con, "SELECT date, ground_idx, wy_pct_normal, prev3, days_since_rain FROM rain_context")
    model_rain = table(con, "SELECT date, precip_mm FROM weather_daily").precip_mm.fillna(0)
    flows = pd.read_sql("SELECT date, gauge, cfs FROM donor_flow_daily", con, parse_dates=["date"]).pivot(index="date", columns="gauge", values="cfs")
    flows = flows.reindex(pd.date_range(flows.index.min(), flows.index.max(), freq="D"))
    beach = bacteria(con, "SELECT SampleDate AS d, Result AS v FROM ceden_raw WHERE StationName LIKE '%#5%' AND Analyte = 'Enterococcus'")
    creek = bacteria(con, "SELECT SampleDate AS d, Result AS v FROM ceden_raw WHERE StationName LIKE 'San Pedro Creek%' AND Analyte = 'E. coli'")
    mouth = bacteria(con, "SELECT collection_date AS d, entero AS v FROM bwtf_lindamar WHERE \"site name\" = 'Linda Mar Beach/San Pedro Creek'")
    con.close()

    print("\n1. Do the stand-ins move with the measured water table?   (1.0 = exactly together)")
    print(f"   {'stand-in':44} {'valley wells':>14} {'all Pacifica wells':>20} {'valley, seasons removed':>25}")
    for name, s in {"dry-weather flow, three neighbouring creeks": np.log10(bf.shift(1)),
                    "ground-wetness index (from rain)": np.log10(rc.ground_idx.clip(lower=1))}.items():
        (a, na), (b, nb), (c, _) = rho(v, s), rho(ev, s), rho(v, s, "month")
        print(f"   {name:44} {a:+.2f} (n={na}){'':3} {b:+.2f} (n={nb}){'':6} {c:+.2f}")

    built = ground(model_rain)
    drift = (10 ** built - rc.ground_idx.reindex(built.index).clip(lower=1)).abs().max()
    print(f"\n2. Does the ground drain about 3% a day?   (index rebuilt at other rates; rebuild differs from the stored index by at most {drift:.3f})")
    print(f"   {'kept per day':>12} {'half-life':>10} {'valley wells':>13} {'other Pacifica wells':>21} {'valley, seasons removed':>24}")
    series = {k: ground(model_rain, k) for k in DRAIN_RATES}
    for k, s in series.items():
        print(f"   {k:>12} {np.log(0.5) / np.log(k):>8.0f} d {rho(v, s)[0]:>+13.2f} {rho(other, s)[0]:>+21.2f} {rho(v, s, 'month')[0]:>+24.2f}")
    rng = np.random.default_rng(41)
    best = []
    for _ in range(300):
        b = v.sample(len(v), replace=True, random_state=int(rng.integers(1e9)))
        best.append(max(DRAIN_RATES, key=lambda k: rho(b, series[k])[0]))
    print("   best rate in each of 300 resamples of the valley visits:", {k: best.count(k) for k in DRAIN_RATES if best.count(k)})

    print("\n3. Would rain-gauge readings drive the index better than weather-model rain?")
    try:
        official, nearby = gauge_rain(VALLEY_GAUGE), gauge_rain(NEARBY_GAUGE)
        g = official.reindex(model_rain.index).where(model_rain.index <= VALLEY_GAUGE_END)
        g = g.fillna(nearby.reindex(model_rain.index).where(model_rain.index >= NEARBY_GAUGE_START))
        print(f"   gauge record covers {g.notna().mean():.0%} of days since 1998 (valley gauge to 2012, then the nearest complete one); gaps use the weather model")
        g = g.shift(-1).fillna(model_rain)      # gauges are read in the morning for the day before
        for name, s in (("weather-model rain (what the index uses)", built), ("gauge rain", ground(g)), ("gauge rain, keeping 98% a day", ground(g, 0.98))):
            print(f"   {name:42} valley {rho(v, s)[0]:+.2f}   other Pacifica {rho(other, s)[0]:+.2f}   valley, seasons removed {rho(v, s, 'month')[0]:+.2f}")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"   skipped: gauge service unavailable ({str(e)[:80]})")

    print("\n4. Does the water table lag the stand-ins?   (valley correlation with the stand-in read N days earlier)")
    for name, s in (("ground-wetness index", built), ("three-creek dry-weather flow", dry_weather_flow(flows, 7))):
        print(f"   {name:30}", "  ".join(f"{d:>2}d {rho(v, s.shift(d))[0]:+.2f}" for d in (0, 7, 14, 30, 45, 60, 90)))
    print("   dry-weather flow by window:   ", "  ".join(f"{n}-day low {rho(v, dry_weather_flow(flows, n))[0]:+.2f}" for n in (3, 7, 14, 30)))

    print("\n5. Does a wet winter leave a higher water table the following summer?   (Jul-Oct visits, by year)")
    flow7 = dry_weather_flow(flows, 7)
    for name, sub in (("valley wells", v), ("all Pacifica wells", ev)):
        x = sub[sub.date.dt.month.isin([7, 8, 9, 10])].copy()
        x["a"] = x.lvl - x.groupby("GLOBAL_ID")["lvl"].transform("mean")
        t = x.groupby(x.date.dt.year).agg(a=("a", "mean"), n=("a", "size"))
        t = t[t.n >= 3]
        t["winter"] = [rc.wy_pct_normal.get(pd.Timestamp(f"{y}-06-01"), np.nan) for y in t.index]
        t["flow"] = [flow7[(flow7.index.year == y) & flow7.index.month.isin([7, 8, 9])].mean() for y in t.index]
        t = t.dropna()
        if len(t) < 5:
            print(f"   {name}: only {len(t)} summers with 3 or more visits; too few to test")
            continue
        (r1, p1), (r2, p2) = corr_p(t.winter, t.a), corr_p(t.flow, t.a)
        print(f"   {name}: {len(t)} summers, {t.index.min()}-{t.index.max()};  summer water table vs the winter's rain r={r1:+.2f} (p={p1:.2f});  "
              f"vs that summer's dry-weather flow at the three creeks r={r2:+.2f} (p={p2:.2f})")
        print("      ", "  ".join(f"{y}: {a:+.1f} ft after {w:.0f}%" for y, a, w in zip(t.index, t.a, t.winter)))

    print("\n6. Does the measured water table move with bacteria?   (rain-free samples within 14 days of a valley well visit)")
    for name, b in (("county beach, 2002-2016", beach), ("county beach, 2012-2016 only", beach[beach.date >= "2012-01-01"]),
                    ("Surfrider creek mouth", mouth), ("county creek", creek)):
        cx = rc.reindex(b.date)
        dry = b[((cx.prev3 < 1) & (cx.days_since_rain >= 3)).to_numpy()]
        rows = []
        for day, lvl in v.groupby("date").lvl.mean().items():
            near = dry[(dry.date >= day - pd.Timedelta(days=14)) & (dry.date <= day + pd.Timedelta(days=14))]
            if len(near) >= 2:
                rows.append((day, lvl, near.logc.mean()))
        t = pd.DataFrame(rows, columns=["date", "lvl", "logc"])
        if len(t) < 8:
            print(f"   {name}: only {len(t)} well visits overlap; too few to test")
            continue
        mo = t.date.dt.month
        (r1, p1), (r2, p2) = corr_p(t.lvl, t.logc, rank=True), corr_p(t.lvl - t.groupby(mo).lvl.transform("mean"), t.logc - t.groupby(mo).logc.transform("mean"), rank=True)
        print(f"   {name}: {len(t)} well visits, {t.date.min().date()} .. {t.date.max().date()};  rank correlation {r1:+.2f} (p={p1:.2f});  seasons removed {r2:+.2f} (p={p2:.2f})")

    print("\n7. Summer by summer: does the creek's rain-free level follow the winter's rain?   (county creek, Jun-Sep, 7+ days after rain)")
    cx = rc.reindex(creek.date)
    c = creek.assign(dsr=cx.days_since_rain.to_numpy(), yr=creek.date.dt.year)
    c = c[c.date.dt.month.isin([6, 7, 8, 9]) & (c.dsr >= 7)]
    t = c.groupby("yr").agg(n=("logc", "size"), logc=("logc", "mean"), over=("v", lambda x: int((x > 320).sum())))
    t["winter"] = [rc.wy_pct_normal.get(pd.Timestamp(f"{y}-06-15"), np.nan) for y in t.index]
    t["flow"] = [flow7[(flow7.index.year == y) & flow7.index.month.isin([7, 8, 9])].mean() for y in t.index]
    t["cls"] = np.where(t.winter > 130, "wet", np.where(t.winter < 70, "dry", "normal"))
    for y, r in t.iterrows():
        print(f"   {y}: winter {r.winter:>4.0f}% ({r.cls:6})  {r.n:>2} samples  typical {10 ** r.logc:>4.0f}  over the standard {r.over:>2}")
    for cls in ("dry", "normal", "wet"):
        x = c[c.yr.map(t.cls) == cls]
        print(f"   pooled, after {cls:6} winters: {len(x):>3} samples, typical {10 ** x.logc.mean():.0f}, {(x.v > 320).mean():.0%} over the standard")
    t = t[t.n >= 5].dropna()
    (r1, p1), (r2, p2), (r3, p3) = corr_p(t.winter, t.logc, rank=True), corr_p(t.winter, t.logc), corr_p(t.flow, t.logc)
    print(f"   across the {len(t)} summers with 5 or more samples:  vs the winter's rain, rank correlation {r1:+.2f} (p={p1:.2f}), r={r2:+.2f} (p={p2:.2f});  "
          f"vs that summer's dry-weather flow at the three creeks r={r3:+.2f} (p={p3:.2f})")


if __name__ == "__main__":
    main()
