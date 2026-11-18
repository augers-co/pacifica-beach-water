"""Check the groundwater stand-ins against groundwater that was actually measured.

The State Water Board's GeoTracker database holds depth-to-water readings from
monitoring wells at cleanup sites. Five such sites sit in the San Pedro Creek
valley (measured 2002-2016). This script downloads the county files, builds
each well's level relative to its own typical level, and reports how closely
two stand-ins move with it:

  - baseflow_daily.baseflow_cfs  (dry-weather flow at three neighbouring creeks)
  - rain_context.ground_idx      (the rain-derived ground-wetness index)

Correlations are computed within each site (site means removed), so sites with
different depths cannot manufacture a relationship. Run after fetch_flow.py and
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
VALLEY = dict(lat=(37.572, 37.602), lon=(-122.512, -122.455))   # San Pedro Creek valley floor
PACIFICA = dict(lat=(37.56, 37.67), lon=(-122.52, -122.44))


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


def main():
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
    ev = w.groupby(["GLOBAL_ID", "date", "valley"], as_index=False).agg(lvl=("lvl", "mean"), dtw=("dtw", "median"))
    v = ev[ev.valley]
    print(f"valley sites: {v.GLOBAL_ID.nunique()}, site visits: {len(v)}, {v.date.min().date()} .. {v.date.max().date()}")
    print(f"depth to water in the valley: median {v.dtw.median():.1f} ft; Jan-Apr {v[v.date.dt.month <= 4].dtw.median():.1f} ft; "
          f"Aug-Oct {v[v.date.dt.month.isin([8, 9, 10])].dtw.median():.1f} ft")

    con = sqlite3.connect(DB)
    bf = pd.read_sql("SELECT date, baseflow_cfs FROM baseflow_daily", con, parse_dates=["date"]).set_index("date").baseflow_cfs
    gi = pd.read_sql("SELECT date, ground_idx FROM rain_context", con, parse_dates=["date"]).set_index("date").ground_idx
    con.close()
    stand_ins = {"dry-weather flow, three neighbouring creeks": np.log10(bf.shift(1)),
                 "ground-wetness index (from rain)": np.log10(gi.clip(lower=1))}

    def rho(sub, s, by):
        x = sub.assign(c=s.reindex(sub.date).to_numpy()).dropna(subset=["c"])
        if by == "month":
            x = x.assign(month=x.date.dt.month)
        a = x.c - x.groupby(by)["c"].transform("mean")
        b = x.lvl - x.groupby(by)["lvl"].transform("mean")
        return pd.concat([a, b], axis=1).corr(method="spearman").iloc[0, 1], len(x)

    print(f"\nrank correlation with the measured water table (1.0 = moves exactly together)")
    print(f"  {'stand-in':44} {'valley wells':>14} {'all Pacifica wells':>20} {'valley, seasons removed':>25}")
    for name, s in stand_ins.items():
        a, na = rho(v, s, "GLOBAL_ID")
        b, nb = rho(ev, s, "GLOBAL_ID")
        c, _ = rho(v, s, "month")
        print(f"  {name:44} {a:+.2f} (n={na}){'':3} {b:+.2f} (n={nb}){'':6} {c:+.2f}")


if __name__ == "__main__":
    main()
