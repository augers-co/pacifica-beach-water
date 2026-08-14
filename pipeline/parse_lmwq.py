"""Parse the Linda Mar Water Quality Coalition Excel exports
(lindamarwaterquality.org/test-results) into a tidy table: lmwq_long.

Sheet layout: rows 0-2 title/org bands, row 3 site headers, data from row 4.
Columns are mapped dynamically from the row-2 org band + row-3 site names.
Values may carry '<' '>' qualifiers; coerced to numeric (qualifier kept).
Raw files live in data/lmwq/ (gitignored — Coalition data is not ours to
republish).
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"

FILES = {
    "ent": ROOT / "data/lmwq/enterococcus.xlsx",
    "ecoli": ROOT / "data/lmwq/ecoli.xlsx",
}


def clean_value(v):
    if pd.isna(v):
        return np.nan, ""
    s = str(v).strip().replace(",", "")
    qual = ""
    if s.startswith(("<", ">")):
        qual, s = s[0], s[1:]
    try:
        return float(s), qual
    except ValueError:
        return np.nan, ""


def parse_sheet(path, analyte):
    raw = pd.read_excel(path, header=None)
    orgs = raw.iloc[2].ffill()
    sites = raw.iloc[3]
    date_cols = [c for c in raw.columns if str(sites[c]).strip() == "Date"]
    rows = []
    for c in raw.columns:
        site = str(sites[c]).strip()
        if site in ("nan", "Date", "Creek Level", "Rain") or not site:
            continue
        # each value column belongs to the nearest Date column to its left
        dcol = max([d for d in date_cols if d < c], default=date_cols[0])
        org = str(orgs[c]).strip()
        for i in range(4, len(raw)):
            date = pd.to_datetime(raw.iloc[i][dcol], errors="coerce")
            if pd.isna(date):
                continue
            val, qual = clean_value(raw.iloc[i][c])
            if np.isnan(val):
                continue
            rows.append(
                dict(
                    date=date, analyte=analyte, org=org, site=site, value=val,
                    qualifier=qual,
                    creek_level=str(raw.iloc[i][0]).strip() if pd.notna(raw.iloc[i][0]) else None,
                    rain_flag=str(raw.iloc[i][1]).strip() if pd.notna(raw.iloc[i][1]) else None,
                )
            )
    return pd.DataFrame(rows)


def main():
    frames = [parse_sheet(p, a) for a, p in FILES.items()]
    out = pd.concat(frames, ignore_index=True)
    con = sqlite3.connect(DB)
    out.assign(date=out.date.dt.strftime("%Y-%m-%d")).to_sql(
        "lmwq_long", con, if_exists="replace", index=False
    )
    con.close()
    print(out.groupby(["analyte", "org", "site"]).agg(
        n=("value", "size"), first=("date", "min"), last=("date", "max")
    ))


if __name__ == "__main__":
    main()
