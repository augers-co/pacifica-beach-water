"""Pull Pacifica bacteria + weather data from public APIs into data/pacifica.db.

Sources (all free, no keys):
  - CEDEN fecal indicator bacteria (data.ca.gov CKAN datastore), 3 era resources
  - BeachWatch monitoring results + advisories (data.ca.gov CKAN datastore)
  - Open-Meteo ERA5 archive: daily precipitation at the San Pedro Creek watershed

Idempotent: each run fully replaces the raw tables.
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
CKAN = "https://data.ca.gov/api/3/action/datastore_search"

CEDEN_RESOURCES = {
    "ceden_2020_present": "15a63495-8d9f-4a49-b43a-3092ef3106b9",
    "ceden_2010_2020": "04d98c22-5523-4cc1-86e7-3a6abf40bb60",
    "ceden_pre2010": "1d333989-559a-433f-b93f-bb43d21da2b9",
}
CEDEN_STATIONS = [
    "Linda Mar Beach #5-Pacifica State Beach, San Mateo",
    "Linda Mar Beach #6-Pacifica State Beach, San Mateo",
    "San Pedro Creek-Pacifica State Beach, San Mateo",
]
BEACHWATCH_RESULTS = "7bd961cf-abe4-433b-8033-378161237ff3"
BEACHWATCH_ADVISORIES = "d5cd6a23-829c-426d-a63e-689a55a3db9c"

# Watershed centroid (mid San Pedro Valley, toward Montara Mtn slopes)
WX_LAT, WX_LON = 37.585, -122.47


def ckan_fetch_all(resource_id, filters=None, q=None, page=5000):
    """Fetch every record matching filters/q from a CKAN datastore resource."""
    records, offset = [], 0
    while True:
        params = {"resource_id": resource_id, "limit": page, "offset": offset}
        if filters:
            params["filters"] = json.dumps(filters)
        if q:
            params["q"] = q
        for attempt in range(3):
            try:
                r = requests.get(CKAN, params=params, timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                print(f"    retry {attempt + 1} after {e}", file=sys.stderr)
                time.sleep(5)
        result = r.json()["result"]
        batch = result["records"]
        records.extend(batch)
        offset += len(batch)
        if len(batch) < page or offset >= result.get("total", 0):
            return records, result.get("total")


def fetch_ceden(con):
    frames = []
    for name, rid in CEDEN_RESOURCES.items():
        for station in CEDEN_STATIONS:
            recs, total = ckan_fetch_all(rid, filters={"StationName": station})
            if recs:
                df = pd.DataFrame(recs)
                df["era_resource"] = name
                frames.append(df)
            print(f"  {name} / {station}: {len(recs)}")
    out = pd.concat(frames, ignore_index=True)
    out.to_sql("ceden_raw", con, if_exists="replace", index=False)
    print(f"ceden_raw: {len(out)} rows")


def fetch_beachwatch(con):
    recs, _ = ckan_fetch_all(BEACHWATCH_RESULTS, q="Linda Mar")
    df = pd.DataFrame(recs)
    df.to_sql("beachwatch_raw", con, if_exists="replace", index=False)
    print(f"beachwatch_raw: {len(df)} rows")

    adv, _ = ckan_fetch_all(BEACHWATCH_ADVISORIES, q="Pacifica")
    if adv:
        pd.DataFrame(adv).to_sql("advisories_raw", con, if_exists="replace", index=False)
    print(f"advisories_raw: {len(adv)} rows")


def fetch_weather(con):
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": WX_LAT,
            "longitude": WX_LON,
            "start_date": "1998-01-01",
            "end_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "daily": "precipitation_sum",
            "timezone": "America/Los_Angeles",
        },
        timeout=180,
    )
    r.raise_for_status()
    d = r.json()["daily"]
    df = pd.DataFrame({"date": d["time"], "precip_mm": d["precipitation_sum"]})
    df.to_sql("weather_daily", con, if_exists="replace", index=False)
    print(f"weather_daily: {len(df)} rows ({df['date'].min()} .. {df['date'].max()})")


def fetch_wx_extra(con):
    """Daily temperature + solar (the ledger's warmth signal and the inferred
    water temperature both derive from temp_mean). Originally a one-off pull;
    promoted into the chain when the CI cold rebuild exposed it as an orphan."""
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": WX_LAT,
            "longitude": WX_LON,
            "start_date": "2000-01-01",
            "end_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "daily": "temperature_2m_mean,temperature_2m_max,shortwave_radiation_sum",
            "timezone": "America/Los_Angeles",
        },
        timeout=180,
    )
    r.raise_for_status()
    d = r.json()["daily"]
    df = pd.DataFrame({"date": pd.to_datetime(d["time"]), "temp_mean": d["temperature_2m_mean"],
                       "solar_mj": d["shortwave_radiation_sum"], "temp_max": d["temperature_2m_max"]})
    df.to_sql("wx_extra_daily", con, if_exists="replace", index=False)
    print(f"wx_extra_daily: {len(df)} rows ({d['time'][0]} .. {d['time'][-1]})")


def main():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    print("== CEDEN bacteria ==")
    fetch_ceden(con)
    print("== BeachWatch ==")
    fetch_beachwatch(con)
    print("== Weather (Open-Meteo ERA5) ==")
    fetch_wx_extra(con)
    fetch_weather(con)
    con.close()
    print(f"done -> {DB}")


if __name__ == "__main__":
    main()
