"""Fetch computable covariates: hourly tide predictions (NOAA CO-OPS, SF station)
and hourly rainfall (Open-Meteo ERA5) for the modern era. Cache into pacifica.db.

Tide is deterministic (harmonic predictions), so historical values are exact;
SF Golden Gate phase leads Pacifica by minutes-to-tens-of-minutes — fine for
stage/height classification.
"""

import sqlite3
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
STATION = "9414290"  # San Francisco
YEARS = range(2000, 2027)  # tide is deterministic; span the full LM5 record


def fetch_tide(con):
    frames = []
    for y in YEARS:
        r = requests.get(
            COOPS,
            params={
                "product": "predictions", "datum": "MLLW", "units": "metric",
                "time_zone": "lst_ldt", "interval": "h", "format": "json",
                "station": STATION,
                "begin_date": f"{y}0101", "end_date": f"{y}1231",
            },
            timeout=120,
        )
        r.raise_for_status()
        js = r.json()
        df = pd.DataFrame(js["predictions"])
        frames.append(df)
        print(f"  tide {y}: {len(df)} rows")
        time.sleep(1)
    tide = pd.concat(frames, ignore_index=True).rename(columns={"t": "dt", "v": "height_m"})
    tide.to_sql("tide_hourly", con, if_exists="replace", index=False)


def fetch_hourly_rain(con):
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": 37.585, "longitude": -122.47,
            "start_date": "2015-01-01",
            "end_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "hourly": "precipitation", "timezone": "America/Los_Angeles",
        },
        timeout=300,
    )
    r.raise_for_status()
    d = r.json()["hourly"]
    df = pd.DataFrame({"dt": d["time"], "precip_mm": d["precipitation"]})
    df.to_sql("rain_hourly", con, if_exists="replace", index=False)
    print(f"  rain_hourly: {len(df)} rows")


def main():
    con = sqlite3.connect(DB)
    print("== tide predictions (CO-OPS hourly) ==")
    fetch_tide(con)
    print("== hourly rain (ERA5) ==")
    fetch_hourly_rain(con)
    con.close()


if __name__ == "__main__":
    main()
