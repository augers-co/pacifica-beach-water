"""Fetch Surfrider Blue Water Task Force (BWTF) data for the Linda Mar sites.

BWTF publishes its citizen-science water-quality results on a public portal
(bwtf.surfrider.org) whose "download annual data" button hits a public,
unauthenticated export endpoint — one CSV per year, all chapters. This script
calls that same endpoint (the one the website itself uses), one year at a
time, and keeps the Linda Mar / San Pedro Creek rows. No login, no scraping of
rendered HTML; robots.txt carries no restrictions (checked 2026-08-15).

Surfrider's SMC Blue Water Task Force is a member of the Linda Mar Water
Quality Coalition this project supports — this is an allied program's public
data, used gently. Raw CSVs land in data/bwtf/ (gitignored, not ours to
republish); this script is the provenance record.

Sites returned:
  - "Linda Mar Beach/San Pedro Creek" — the CREEK MOUTH (37.5962,-122.5056;
    same reach as the county SPCM/LM5 station). Sampled Dec 2013 → present.
  - "Linda Mar North" / "Linda Mar South" — surf-zone beach transects,
    2012 → ~2014.
  - "Linda Mar Bridge - LM Water Quality Coalition" — the Coalition's upstream
    LMMS site, recent.
"""

import sqlite3
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
RAW = ROOT / "data" / "bwtf"
ENDPOINT = "https://mmvk4falrj.execute-api.us-west-2.amazonaws.com/v1/annual"
YEARS = range(2011, 2027)
UA = "pacifica-beach-water research (Linda Mar Water Quality Coalition ally)"


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    frames = []
    for y in YEARS:
        cache = RAW / f"{y}.csv"
        if cache.exists():
            text = cache.read_text()
        else:
            r = requests.get(
                ENDPOINT,
                params={"year": y, "timezone": "America/Los_Angeles",
                        "timezoneOffset": 480},
                headers={"User-Agent": UA}, timeout=90,
            )
            r.raise_for_status()
            text = r.text
            cache.write_text(text)
            time.sleep(1.5)  # be gentle on a public endpoint
        try:
            df = pd.read_csv(StringIO(text), dtype=str)
        except Exception:
            continue
        df.columns = [c.strip() for c in df.columns]
        lm = df[df["site name"].str.contains("san pedro|linda mar",
                                             case=False, na=False)]
        if len(lm):
            frames.append(lm)
        print(f"  {y}: {len(lm)} Linda Mar rows")
    return pd.concat(frames, ignore_index=True)


def main():
    lm = fetch()
    lm["collection_date"] = pd.to_datetime(lm["collection date"], errors="coerce")
    lm["entero"] = pd.to_numeric(lm["Enterococcus (mpn/100mL)"], errors="coerce")
    lm["ecoli"] = pd.to_numeric(lm["Ecoli (mpn/100mL)"], errors="coerce")
    con = sqlite3.connect(DB)
    lm.to_sql("bwtf_lindamar", con, if_exists="replace", index=False)
    con.close()
    print(f"\nbwtf_lindamar: {len(lm)} rows, "
          f"{lm.collection_date.min().date()} → {lm.collection_date.max().date()}")
    print("sites:", dict(lm["site name"].value_counts()))


if __name__ == "__main__":
    main()
