"""Daily flow at neighbouring gauged creeks (USGS), and the dry-weather flow
index built from the three nearest coastal ones — the project's measured
stand-in for how high groundwater is standing in the San Pedro Creek valley.

San Pedro Creek itself has no gauge. In dry weather what flows in a creek is
groundwater draining out, so the lowest flow of the past week at comparable
creeks nearby is a measured groundwater signal (see docs/inferences.md §10,
checked against monitoring wells in the valley by validate_baseflow.py).

Tables written to pacifica.db:
  donor_flow_daily  date, cfs, gauge      every gauge below, daily mean flow
  baseflow_daily    date, <three gauges>, baseflow_cfs, n_gauges

These are context tables: nothing the ledger publishes depends on them yet, so
a failed fetch warns and keeps what is already stored rather than failing the
weekly refresh.
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
START = "2000-01-01"
UA = {"User-Agent": "pacifica-beach-water (github.com/augers-co/pacifica-beach-water)"}

# USGS site number -> label. Names verified against USGS site records
# 2026-11-18; before that date this project had the first two swapped.
GAUGES = {
    "11162500": "pescadero",         # Pescadero C nr Pescadero
    "11162570": "san_gregorio",      # San Gregorio C at San Gregorio
    "11162630": "pilarcitos",        # Pilarcitos C at Half Moon Bay (regulated upstream)
    "11160000": "soquel",            # Soquel C at Soquel
    "11160500": "san_lorenzo",       # San Lorenzo R at Big Trees
    "11159200": "corralitos",        # Corralitos C at Freedom (interior; contrast only)
    "11164500": "san_francisquito",  # San Francisquito C at Stanford (bay side; contrast only)
    "11460400": "lagunitas",         # Lagunitas C at Samuel P Taylor SP (regulated; contrast only)
}
CORE = ["pescadero", "san_gregorio", "pilarcitos"]  # the three nearest coastal creeks


def _ogc(site, end):
    """USGS water data API (current service)."""
    url = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items"
    params = {"monitoring_location_id": f"USGS-{site}", "parameter_code": "00060", "statistic_id": "00003",
              "time": f"{START}/{end}", "f": "json", "limit": 10000}
    out = {}
    for _ in range(20):
        r = requests.get(url, params=params, headers=UA, timeout=180)
        r.raise_for_status()
        js = r.json()
        for f in js.get("features", []):
            p = f["properties"]
            if p.get("value") is not None:
                out[p["time"][:10]] = float(p["value"])
        nxt = next((l["href"] for l in js.get("links", []) if l.get("rel") == "next"), None)
        if not nxt:
            break
        url, params = nxt, None
    return out


def _legacy(site, end):
    """USGS NWIS daily-values service (older, single request)."""
    r = requests.get("https://waterservices.usgs.gov/nwis/dv/", headers=UA, timeout=180,
                     params={"format": "json", "sites": site, "parameterCd": "00060", "startDT": START, "endDT": end})
    r.raise_for_status()
    ts = r.json()["value"]["timeSeries"]
    vals = ts[0]["values"][0]["value"] if ts else []
    return {v["dateTime"][:10]: float(v["value"]) for v in vals}


def fetch_gauge(site, end):
    for fn in (_ogc, _legacy):
        try:
            d = {k: v for k, v in fn(site, end).items() if v >= 0}
            if len(d) > 1000:
                return pd.Series(d).sort_index()
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"  warn: {fn.__name__.strip('_')} service failed for {site}: {str(e)[:80]}")
    return None


def baseflow(flows):
    """Lowest flow of the trailing 7 days at each core creek (storm peaks drop
    out), averaged across creeks in log space so no one creek dominates."""
    lows = np.log10(flows[CORE].clip(lower=0.01)).rolling(7, min_periods=5).min()
    out = flows[CORE].copy()
    out["n_gauges"] = lows.notna().sum(axis=1)
    out["baseflow_cfs"] = (10 ** lows.mean(axis=1)).where(out.n_gauges >= 2).round(3)
    return out.dropna(subset=["baseflow_cfs"])


def main():
    end = pd.Timestamp.now().strftime("%Y-%m-%d")
    series = {}
    for site, name in GAUGES.items():
        s = fetch_gauge(site, end)
        if s is None:
            print(f"  warn: no data for {name} ({site})")
            continue
        series[name] = s
        print(f"  {name:17} {len(s):5} days  {s.index[0]} .. {s.index[-1]}")
    if sum(g in series for g in CORE) < 2:
        print("warn: fewer than two core creeks fetched — keeping the existing flow tables")
        return 0
    flows = pd.DataFrame(series)
    flows.index = pd.to_datetime(flows.index)
    flows = flows.reindex(pd.date_range(flows.index.min(), flows.index.max(), freq="D"))
    for g in CORE:
        if g not in flows:
            flows[g] = np.nan
    long = flows.rename_axis("date").reset_index().melt("date", var_name="gauge", value_name="cfs").dropna(subset=["cfs"])
    long["date"] = long.date.dt.strftime("%Y-%m-%d")
    base = baseflow(flows).rename_axis("date").reset_index()
    base["date"] = base.date.dt.strftime("%Y-%m-%d")

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    try:
        prev = con.execute("SELECT count(*) FROM donor_flow_daily WHERE gauge IN ('pescadero','san_gregorio','pilarcitos')").fetchone()[0]
    except sqlite3.OperationalError:
        prev = 0
    now = int(long.gauge.isin(CORE).sum())
    if now < 0.98 * prev:
        print(f"warn: fetched {now} core rows < stored {prev} — keeping the existing flow tables")
        con.close()
        return 0
    long[["date", "cfs", "gauge"]].to_sql("donor_flow_daily", con, if_exists="replace", index=False)
    base.to_sql("baseflow_daily", con, if_exists="replace", index=False)
    con.close()
    last = base.iloc[-1]
    print(f"donor_flow_daily: {len(long)} rows, {long.gauge.nunique()} gauges")
    print(f"baseflow_daily: {len(base)} days ({base.date.iloc[0]} .. {base.date.iloc[-1]}), latest {last.baseflow_cfs} cfs from {int(last.n_gauges)} creeks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
