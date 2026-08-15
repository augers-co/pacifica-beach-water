"""Verify the clean-readings claims (findings v9) against the LIVE state API.

Uses no local data: every row is fetched from data.ca.gov (CEDEN fecal
indicator bacteria) at run time, so anyone can reproduce the era collapse,
the year-by-year clean counts, and the vanished streaks with nothing but
this file and an internet connection.

  python pipeline/verify_clean_era.py
"""

import numpy as np
import pandas as pd
import requests

RES = {
    "pre2010": "1d333989-559a-433f-b93f-bb43d21da2b9",
    "2010-2020": "04d98c22-5523-4cc1-86e7-3a6abf40bb60",
    "2020+": "15a63495-8d9f-4a49-b43a-3092ef3106b9",
}
API = "https://data.ca.gov/api/3/action/datastore_search"


def fetch():
    frames = []
    for era, rid in RES.items():
        off, rows = 0, []
        while True:
            r = requests.get(
                API,
                params={"resource_id": rid, "limit": 5000, "offset": off,
                        "q": "Linda Mar"},
                timeout=120,
            )
            r.raise_for_status()
            recs = r.json()["result"]["records"]
            rows += recs
            if len(recs) < 5000:
                break
            off += 5000
        print(f"  live API {era}: {len(rows)} Linda Mar rows")
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def main():
    d = fetch()
    d = d[d.StationName.str.contains("#5") & d.Analyte.str.startswith("Entero")].copy()
    d["date"] = pd.to_datetime(d.SampleDate).dt.normalize()
    d["v"] = pd.to_numeric(d.Result, errors="coerce")
    d["nd"] = d.ResultQualCode == "<"
    g = (d.dropna(subset=["v"]).groupby("date")
         .agg(nd=("nd", "all"), v=("v", "max")).reset_index())
    g["yr"] = g.date.dt.year

    print(f"\nLinda Mar #5 enterococcus: {len(g)} sample-days, "
          f"{g.date.min():%Y-%m-%d} → {g.date.max():%Y-%m-%d}")
    print("\nyear  tests  clean(<10)  over104")
    for yr, s in g.groupby("yr"):
        bar = "#" * int(round(s.nd.mean() * 20))
        print(f"{yr}   {len(s):3}     {s.nd.sum():3} ({s.nd.mean():4.0%})   "
              f"{(s.v > 104).sum():3}  {bar}")

    pre, post = g[g.yr <= 2013], g[g.yr >= 2014]
    print(f"\n2001-2013: {pre.nd.mean():.1%} clean, {(pre.v > 104).mean():.1%} "
          f"over  (n={len(pre)})")
    print(f"2014-2026: {post.nd.mean():.1%} clean, {(post.v > 104).mean():.1%} "
          f"over  (n={len(post)})")

    g = g.sort_values("date").reset_index(drop=True)
    runs, cur = [], []
    for _, r in g.iterrows():
        if r.nd:
            cur.append(r.date)
        else:
            if len(cur) >= 4:
                runs.append((cur[0], cur[-1], len(cur)))
            cur = []
    if len(cur) >= 4:
        runs.append((cur[0], cur[-1], len(cur)))
    longest = max(runs, key=lambda x: x[2])
    print(f"\nclean streaks of 4+ consecutive tests: {len(runs)}")
    print(f"  longest: {longest[0]:%Y-%m-%d} → {longest[1]:%Y-%m-%d} "
          f"({longest[2]} tests)")
    print(f"  most recent: {runs[-1][0]:%Y-%m-%d} → {runs[-1][1]:%Y-%m-%d} "
          f"({runs[-1][2]} tests)")


if __name__ == "__main__":
    main()
