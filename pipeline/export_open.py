"""Export the public data behind the forecast rule into open-data/.

WHAT IT WRITES (all inside open-data/)
  county_ocean_tests.csv      every county ocean test at the creek mouth since 2000
  daily_rain_and_ground.csv   daily rain and the two wetness indexes since 1998
  rule_v0_1_worked.csv        the FROZEN record of the version-0.1 fit: the rule's
                              arithmetic for every test through 2026-10-19
  build/pacifica-open.sqlite  one database with all of the above, the allow-listed
                              source tables, the forecast log (if present) and an
                              "about" table describing every source
The CSV files are tracked in the repository. The build/ folder is not; the
database is published as a download on the repository's Releases page.

It reads data/pacifica.db read-only and never changes it. Output is
deterministic (fixed ordering and number formats) so weekly changes are small.

rule_v0_1_worked.csv is written once and then never touched: if it exists this
script leaves it alone and says so. Only --refreeze regenerates it, and that
changes what version 0.1 means, so do not use it casually.

Nothing here says the water is ever safe.

Run from the repo root:   python3 pipeline/export_open.py [--refreeze]
Needs numpy and pandas.
"""

# =====================================================================
# WHAT MAY BE PUBLISHED -- edit this list to change what is exported.
# Only tables named here are copied into the open database.
# =====================================================================
ALLOW_LIST = [
    "ceden_raw",           # county results via the state CEDEN database
    "beachwatch_raw",      # state BeachWatch results
    "advisories_raw",      # state BeachWatch advisories / postings
    "weather_daily",       # Open-Meteo / ERA5 daily rain
    "wx_extra_daily",      # Open-Meteo / ERA5 daily temperature and sunshine
    "rain_hourly",         # Open-Meteo / ERA5 hourly rain
    "rain_context",        # derived here from weather_daily (features.py)
    "tide_hourly",         # NOAA CO-OPS tide predictions
    "donor_flow_daily",    # USGS stream gauges elsewhere on the coast
    "baseflow_daily",      # derived from the USGS gauges (fetch_flow.py)
    # "sso_pacifica_old",  # left off: terms not stated by the source
    # "sso_pacifica_new",  # left off: terms not stated by the source
    # "bwtf_lindamar",     # left off: no reuse terms published; ask Surfrider.
    #                      # IF EVER ENABLED: first filter out every row for the
    #                      # Linda Mar Water Quality Coalition's own site
    #                      # ("Linda Mar Bridge - LM Water Quality Coalition");
    #                      # those results are the Coalition's to release.
    # "asos_haf",          # left off: no source or fetch script is recorded in the repository
]

# Columns that name or phone individual people; dropped on copy.
DROP_COLUMNS = {
    "beachwatch_raw": ["Results Contact Person"],
    "advisories_raw": ["Advisories Contact Person"],
    "sso_pacifica_old": ["CERT PERSON NAME", "CERT PERSON TITLE", "SSO OPERATOR NAME", "SSO OPERATOR PHONE"],
    "sso_pacifica_new": ["CERTIFIED_BY", "CERTIFIER_TITLE"],
}

# Never exported, whatever the list above says: the Linda Mar Water Quality
# Coalition's own results are theirs to release.
NEVER = {"lmwq_long"}

import sqlite3
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # find forecast_rule even under python -I
import forecast_rule as fr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pacifica.db"
OPEN = ROOT / "open-data"
BUILD = OPEN / "build"
SQLITE = BUILD / "pacifica-open.sqlite"
LOG = OPEN / "forecast_log.csv"

NO_LINK = "no public link recorded"
NOT_FOUND = "terms not found"
DEFAULT_WHY = "Held back until its reuse terms are confirmed."
CKAN_CEDEN = "https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results"
CKAN_BW = "https://data.ca.gov/dataset/beach-water-quality-postings-and-closures"
OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
NOAA = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USGS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items"
SSO_NEW = "https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Cat1-2-3-Spills.txt"

T_CEDEN = ('Rights field "No Restrictions on Public Use"; no licence named '
           "(" + CKAN_CEDEN + ", checked 2026-11-18)")
A_CEDEN = "No credit required. Suggested: State Water Resources Control Board (CEDEN), via data.ca.gov; sampling by San Mateo County Environmental Health"
T_BW = ('Rights field "No Restrictions on Public Use"; licence: Open Data Commons Attribution License '
        "(" + CKAN_BW + ", checked 2026-11-18)")
A_BW = "Credit required: State Water Resources Control Board (BeachWatch), under the Open Data Commons Attribution License"
T_OM = ("Creative Commons Attribution 4.0 (CC BY 4.0); the free service is for non-commercial use "
        "(https://open-meteo.com/en/licence, checked 2026-11-18). Terms of the upstream Copernicus ERA5 licence not read")
A_OM = 'Credit required: "Weather data by Open-Meteo.com", and "Generated using Copernicus Climate Change Service information 2022"'
T_NOAA = ("U.S. government information, in the public domain and free to use; must not be modified and then presented as official "
          "government material (https://www.tidesandcurrents.noaa.gov/disclaimers.html, checked 2026-11-18)")
A_NOAA = "Credit requested: NOAA National Ocean Service, Center for Operational Oceanographic Products and Services (CO-OPS)"
T_USGS = ('"USGS-authored or produced data and information are considered to be in the U.S. Public Domain" '
          "(https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)")
A_USGS = "Credit requested: U.S. Geological Survey"

# One entry per source. "tables" are the names in the working database.
SOURCES = [
    dict(tables=["ceden_raw"], org="State Water Resources Control Board (CEDEN), for San Mateo County Environmental Health",
         what="The county's weekly bacteria tests (enterococcus, E. coli, total coliform), including station LM5 at the creek mouth",
         link=CKAN_CEDEN, built="pipeline/fetch.py into table ceden_raw", terms=T_CEDEN, attr=A_CEDEN),
    dict(tables=["beachwatch_raw"], org="State Water Resources Control Board (BeachWatch), for San Mateo County Environmental Health",
         what="Beach bacteria results reported under the state's beach program, from 1998",
         link=CKAN_BW, built="pipeline/fetch.py into table beachwatch_raw", terms=T_BW, attr=A_BW),
    dict(tables=["advisories_raw"], org="State Water Resources Control Board (BeachWatch)",
         what="Beach advisories and postings (warnings, closures)",
         link=CKAN_BW, built="pipeline/fetch.py into table advisories_raw", terms=T_BW, attr=A_BW),
    dict(tables=["weather_daily", "wx_extra_daily"], org="Open-Meteo (ERA5 reanalysis)",
         what="Daily rain, temperature and sunshine modelled for the San Pedro Creek valley (37.585, -122.47)",
         link=OPEN_METEO, built="pipeline/fetch.py into tables weather_daily and wx_extra_daily", terms=T_OM, attr=A_OM),
    dict(tables=["rain_hourly"], org="Open-Meteo (ERA5 reanalysis)",
         what="Hourly rain modelled for the San Pedro Creek valley, from 2015",
         link=OPEN_METEO, built="pipeline/fetch_covariates.py into table rain_hourly", terms=T_OM, attr=A_OM),
    dict(tables=["rain_context"], org="Built by this project from the Open-Meteo daily rain",
         what="Rain totals, days since rain, and the two wetness indexes (flow_idx, ground_idx) the rule uses",
         link=OPEN_METEO, built="pipeline/features.py into table rain_context (from weather_daily)", terms=T_OM, attr=A_OM),
    dict(tables=["tide_hourly"], org="NOAA Center for Operational Oceanographic Products and Services (CO-OPS)",
         what="Hourly tide predictions at Princeton / Half Moon Bay (station 9414131)",
         link=NOAA, built="pipeline/fetch_covariates.py into table tide_hourly", terms=T_NOAA, attr=A_NOAA),
    dict(tables=["donor_flow_daily", "baseflow_daily"], org="U.S. Geological Survey",
         what="Daily flow at coastal stream gauges elsewhere on the peninsula, and a dry-weather flow index built from three of them",
         link=USGS, built="pipeline/fetch_flow.py into tables donor_flow_daily and baseflow_daily", terms=T_USGS, attr=A_USGS),
    dict(tables=["sso_pacifica_new"], org="State Water Resources Control Board (CIWQS sewer-spill reports)",
         what="Sewer spills reported by Pacifica's sewer system since mid-2023",
         link=SSO_NEW, built="pipeline/refresh.py into table sso_pacifica_new",
         terms="terms not stated by the source (https://www.waterboards.ca.gov/water_issues/programs/sso/docs/index.php, checked 2026-11-18)",
         why="The state publishes no reuse terms for these reports."),
    dict(tables=["sso_pacifica_old"], org="State Water Resources Control Board (CIWQS sewer-spill reports)",
         what="Sewer spills reported by Pacifica's sewer system, 2007 to mid-2023 (the state has since retired its old file)",
         link=NO_LINK + " (the old state file was retired; the Pacifica rows are kept in pipeline/sso_legacy_pacifica.csv)",
         built="pipeline/refresh.py into table sso_pacifica_old (reads pipeline/sso_legacy_pacifica.csv)",
         terms="terms not stated by the source",
         why="The state publishes no reuse terms for these reports."),
    dict(tables=["bwtf_lindamar"], org="Surfrider Foundation, San Mateo County Blue Water Task Force",
         what="Volunteer bacteria results at Linda Mar creek-mouth and beach sites, 2012 on",
         link="https://bwtf.surfrider.org/ (the portal's annual download: https://mmvk4falrj.execute-api.us-west-2.amazonaws.com/v1/annual?year=YYYY)",
         built="pipeline/fetch_bwtf.py into table bwtf_lindamar",
         terms="no reuse terms published; ask Surfrider",
         why="Surfrider publishes no reuse terms for these results, so permission is needed first."),
    dict(tables=["lmwq_long"], org="Linda Mar Water Quality Coalition",
         what="The Coalition's weekly results at four sites along San Pedro Creek",
         link="https://www.lindamarwaterquality.org/test-results",
         built="pipeline/parse_lmwq.py into table lmwq_long (pipeline/refresh.py fetches the spreadsheets)",
         terms=NOT_FOUND,
         why="These results belong to the Coalition and are theirs to release."),
    dict(tables=["asos_haf"], org="no source recorded",
         what="Hourly sky cover at Half Moon Bay airport (station HAF), 2015 on",
         link=NO_LINK, built="no script in pipeline/ fetches or reads it", terms=NOT_FOUND,
         why="The repository does not record where this came from, so its reuse terms cannot be checked."),
]

DERIVED = [  # tables made by this script: name, what, organisation, link, built, terms, attribution
    ("county_ocean_tests", "Every county ocean test at the creek mouth (LM5, enterococcus) since 2000, one row per sampling day; failed = over 104, far_over = over 312",
     "San Mateo County Environmental Health, via CEDEN", CKAN_CEDEN, "pipeline/export_open.py (from ceden_raw)", T_CEDEN, A_CEDEN),
    ("daily_rain_and_ground", "One row per day since 1998: modelled rain and the flow and ground wetness indexes",
     "Open-Meteo (ERA5), indexes built by this project", OPEN_METEO, "pipeline/export_open.py (from weather_daily and rain_context)", T_OM, A_OM),
    ("rule_v0_1_worked", "FROZEN record of the version-0.1 fit (never changes): the rule's arithmetic for the 243 tests through 2026-10-19, inputs as they were when the rule was fixed",
     "Built by this project from the two tables above", NO_LINK, "pipeline/export_open.py (written once; --refreeze only)",
     "Inherits the terms of the county tests and of Open-Meteo", A_CEDEN + "; " + A_OM),
    ("forecast_log", "Forecasts written down each day before the outcome is known",
     "Built by this project", NO_LINK, "pipeline/forecast_log.py (writes open-data/forecast_log.csv)",
     "Rain, weather and sea-state values come from Open-Meteo: " + T_OM, A_OM),
]

DATE_COLUMN = {
    "ceden_raw": "SampleDate", "beachwatch_raw": "SampleDate", "advisories_raw": "DateofAdvisory",
    "weather_daily": "date", "wx_extra_daily": "date", "rain_hourly": "dt", "rain_context": "date",
    "tide_hourly": "dt", "donor_flow_daily": "date", "baseflow_daily": "date",
    "sso_pacifica_old": "START DT", "sso_pacifica_new": "ESTIMATED_SPILL_START_DATE_AND_TIME",
    "county_ocean_tests": "date", "daily_rain_and_ground": "date", "rule_v0_1_worked": "date",
    "forecast_log": "issue_date",
}


# ------------------------------------------------------------------ csv files
def write_csv(df, path, formats=None):
    df = df.copy()
    for col, f in (formats or {}).items():
        df[col] = df[col].map(lambda v, f=f: "" if pd.isna(v) else format(v, f))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n")


def build_csvs(con):
    county = fr.county_series(con)
    county = county[county.date >= "2000-01-01"]
    county = pd.DataFrame({
        "date": county.date.dt.strftime("%Y-%m-%d"),
        "result_mpn": county.value.to_numpy(),
        "failed": (county.value > fr.STANDARD).astype(int).to_numpy(),
        "far_over": (county.value > fr.FAR_OVER).astype(int).to_numpy(),
    }).reset_index(drop=True)
    write_csv(county, OPEN / "county_ocean_tests.csv", {"result_mpn": ".10g"})

    wx = pd.read_sql("SELECT date, precip_mm AS rain_mm FROM weather_daily", con)
    rc = pd.read_sql("SELECT date, flow_idx, ground_idx FROM rain_context", con)
    daily = wx.merge(rc, on="date", how="outer").sort_values("date").reset_index(drop=True)
    daily = daily[daily.date >= "1998-01-01"]
    # Full precision on purpose: forecast_rule.py must get exactly the numbers
    # it gets from the database. (%r-style shortest round-trip text.)
    daily.to_csv(OPEN / "daily_rain_and_ground.csv", index=False, lineterminator="\n")

    frozen = OPEN / "rule_v0_1_worked.csv"
    if frozen.exists() and "--refreeze" not in sys.argv[1:]:
        print("rule_v0_1_worked.csv already exists: it is the frozen record of version 0.1 and is left untouched "
              "(use --refreeze to rebuild it).")
        return county, daily, pd.read_csv(frozen, float_precision="round_trip")
    t = fr.load_tests(con)  # tests since 2022 with rain3 and ground attached
    y, year = t.fail.to_numpy(float), t.year.to_numpy()
    X = fr._design(t.rain3.to_numpy(), t.ground.to_numpy())
    z = X @ np.asarray(fr.COEF, dtype=float)
    p = np.round(1.0 / (1.0 + np.exp(-z)), 6)
    p_out = fr.held_out(X, y, year, [0, 1, 2])
    worked = pd.DataFrame({
        "date": t.date.dt.strftime("%Y-%m-%d"),
        "result_mpn": t.value, "failed": t.fail, "far_over": t.far,
        "rain3_mm": t.rain3, "ground_idx": t.ground,
        "ln_1_plus_rain3": X[:, 1], "log10_ground": X[:, 2],
        "z": z, "chance": p, "level": [fr.level(v) for v in p],
        "chance_held_out": p_out,
    })
    # rain3_mm and ground_idx are the inputs of the frozen fit: full round-trip
    # precision. The derived columns are rounded.
    write_csv(worked, frozen, {
        "result_mpn": ".10g", "ln_1_plus_rain3": ".6f", "log10_ground": ".6f",
        "z": ".6f", "chance": ".6f", "chance_held_out": ".6f"})
    return county, daily, worked


# ------------------------------------------------------------------ database
def date_range(df, col):
    if col not in df or df.empty:
        return "", ""
    d = pd.to_datetime(df[col], errors="coerce", format="mixed").dropna()
    return (d.min().strftime("%Y-%m-%d"), d.max().strftime("%Y-%m-%d")) if len(d) else ("", "")


def source_for(table):
    for s in SOURCES:
        if table in s["tables"]:
            return s
    raise SystemExit(f"{table} is on the allow-list but has no entry in SOURCES")


def main():
    bad = NEVER & set(ALLOW_LIST)
    if bad or any("lmwq" in t.lower() for t in ALLOW_LIST):
        raise SystemExit(f"Refusing to export: {sorted(bad) or 'lmwq'} must never be on the allow-list.")
    if not DB.exists():
        raise SystemExit(f"{DB} not found; this script needs the working database.")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        county, daily, worked = build_csvs(con)
        BUILD.mkdir(parents=True, exist_ok=True)
        tmp = SQLITE.with_suffix(".tmp")
        for f in (tmp, SQLITE):
            if f.exists():
                f.unlink()
        out = sqlite3.connect(tmp)
        today = date.today().isoformat()
        about = []

        def add_about(table, n, first, last, org, what, link, included, why="", built="", attribution="", terms=""):
            about.append((table, org, what, link, "yes" if included else "no", attribution, terms, why, built, n, first, last, today))

        existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ALLOW_LIST:
            if table not in existing:
                raise SystemExit(f"allow-listed table {table} is not in the database")
            info = con.execute(f'PRAGMA table_info("{table}")').fetchall()
            drop = set(DROP_COLUMNS.get(table, []))
            cols = [(r[1], r[2]) for r in info if r[1] not in drop]
            names = ", ".join('"%s"' % c for c, _ in cols)
            out.execute('CREATE TABLE "%s" (%s)' % (table, ", ".join('"%s" %s' % c for c in cols)))
            df = pd.read_sql(f'SELECT {names} FROM "{table}" ORDER BY rowid', con)
            rows = [tuple(None if (isinstance(v, float) and v != v) else v for v in r)
                    for r in con.execute(f'SELECT {names} FROM "{table}" ORDER BY rowid')]
            out.executemany('INSERT INTO "%s" VALUES (%s)' % (table, ",".join("?" * len(cols))), rows)
            a, b = date_range(df, DATE_COLUMN[table])
            s = source_for(table)
            add_about(table, len(rows), a, b, s["org"], s["what"], s["link"], True, built=s["built"],
                      attribution=s["attr"], terms=s["terms"])

        for name, df in (("county_ocean_tests", county), ("daily_rain_and_ground", daily), ("rule_v0_1_worked", worked)):
            df.to_sql(name, out, index=False)
        if LOG.exists():
            pd.read_csv(LOG, dtype=str, keep_default_na=False).to_sql("forecast_log", out, index=False)
        derived_present = {"county_ocean_tests": county, "daily_rain_and_ground": daily, "rule_v0_1_worked": worked}
        if LOG.exists():
            derived_present["forecast_log"] = pd.read_csv(LOG, dtype=str, keep_default_na=False)
        for name, what, org, link, built, terms, attr in DERIVED:
            if name in derived_present:
                df = derived_present[name]
                a, b = date_range(df, DATE_COLUMN[name])
                add_about(name, len(df), a, b, org, what, link, True, built=built, attribution=attr, terms=terms)

        # Sources whose tables are not in the open database: one row each.
        for s in SOURCES:
            if not all(t in ALLOW_LIST for t in s["tables"]):
                add_about("", None, "", "", s["org"], s["what"], s["link"], False,
                          why=s.get("why", DEFAULT_WHY), built=s["built"],
                          attribution="not applicable (not included)", terms=s["terms"])

        out.execute("""CREATE TABLE about (table_name TEXT, organisation TEXT, what_it_holds TEXT, link TEXT,
                       included_in_open_database TEXT, attribution TEXT, terms TEXT, why_not_included TEXT,
                       rebuilt_by TEXT, row_count INTEGER, first_date TEXT, last_date TEXT, exported TEXT)""")
        out.executemany("INSERT INTO about VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", about)
        out.commit()
        out.execute("VACUUM")
        out.close()
        tmp.replace(SQLITE)
    finally:
        con.close()

    print("open-data/ written:")
    for f in sorted(OPEN.glob("*.csv")) + [SQLITE]:
        print(f"  {f.relative_to(ROOT)}  {f.stat().st_size:,} bytes")
    print(f"database size: {SQLITE.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
