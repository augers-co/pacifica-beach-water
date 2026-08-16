"""Rebuild ledger_data.json for the San Pedro Ledger, full record 2000->present.

Extends the original (2015+) export back to 2000-01-01: the county beach
record begins 2000-05-16, creek testing begins 2015-09-21 (lane honestly
empty before that), spills join 2007+. Adds `nd` (non-detect, "<10") flags
to beach samples and fixes the spill `loc` field (was a pandas repr bug).
"""

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DB = Path(__file__).resolve().parent.parent / "data" / "pacifica.db"
OUT = Path(__file__).parent / "ledger_data.json"
START = "2000-01-01"

GEO = {
    "LMMS": {"name": "Linda Mar Bridge", "lat": 37.58151, "lon": -122.4787},
    "ADMS": {"name": "Adobe Sanchez", "lat": 37.58687, "lon": -122.4949},
    "PRLT": {"name": "Peralta Bridge", "lat": 37.58852, "lon": -122.4993},
    "SPCM": {"name": "San Pedro Creek Mouth", "lat": 37.59625, "lon": -122.5055},
    "LM5": {"name": "Beach at creek mouth (county)", "lat": 37.59658, "lon": -122.50578},
}
NAME2CODE = {v["name"]: k for k, v in GEO.items()}
NAME2CODE["San Pedro Cr Mouth"] = "SPCM"
NAME2CODE["LM 5 - Pacific Ocean at San Pedro Cr"] = "LM5"

con = sqlite3.connect(DB)

# ---- daily covariates -------------------------------------------------------
rc = pd.read_sql("SELECT date, rain_mm, flow_idx, ground_idx, wy_pct_normal "
                 "FROM rain_context WHERE date >= ?", con, params=[START])
rc["date"] = pd.to_datetime(rc.date)

wx = pd.read_sql("SELECT date, temp_mean FROM wx_extra_daily", con)
wx["date"] = pd.to_datetime(wx.date)
need_from = pd.Timestamp(START)
if wx.date.min() > need_from:
    print(f"fetching daily temps {START} -> {wx.date.min().date()} from Open-Meteo...")
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={"latitude": 37.585, "longitude": -122.47,
                "start_date": START,
                "end_date": (wx.date.min() - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "daily": "temperature_2m_mean", "timezone": "America/Los_Angeles"},
        timeout=300)
    r.raise_for_status()
    d = r.json()["daily"]
    old = pd.DataFrame({"date": pd.to_datetime(d["time"]),
                        "temp_mean": d["temperature_2m_mean"]})
    pd.concat([old.assign(solar_mj=np.nan, temp_max=np.nan),
               pd.read_sql("SELECT * FROM wx_extra_daily", con)
               .assign(date=lambda x: pd.to_datetime(x.date))],
              ignore_index=True).sort_values("date").to_sql(
        "wx_extra_daily", con, if_exists="replace", index=False,
        # keep dates as ISO strings like before
        dtype={})
    wx = pd.read_sql("SELECT date, temp_mean FROM wx_extra_daily", con)
    wx["date"] = pd.to_datetime(wx.date)
    print(f"  wx_extra_daily now {wx.date.min().date()} -> {wx.date.max().date()}")

daily = rc.merge(wx, on="date", how="left").sort_values("date").reset_index(drop=True)
daily["air7"] = daily.temp_mean.rolling(7, min_periods=3).mean()
daily["wt"] = -1.59 + 1.05 * daily.air7
DAILY = [
    {"d": r.date.strftime("%Y-%m-%d"), "mm": round(float(r.rain_mm), 1),
     "f": round(float(r.flow_idx), 1), "s": round(float(r.ground_idx), 1),
     "wy": round(float(r.wy_pct_normal)) if pd.notna(r.wy_pct_normal) else None,
     "t": round(float(r.temp_mean), 1) if pd.notna(r.temp_mean) else None,
     "wt": round(float(r.wt), 1) if pd.notna(r.wt) else None}
    for r in daily.itertuples()
]
ctx = daily.set_index("date")

# ---- spills (2007+, surface-water-reaching) --------------------------------
old = pd.read_sql('SELECT "START DT" sd, "SPILL VOL REACH SURF" surf, '
                  '"SPILL LOC NAME" loc FROM sso_pacifica_old', con)
old["d"] = pd.to_datetime(old.sd, errors="coerce")
old["gal"] = pd.to_numeric(old.surf, errors="coerce")
new_cols = [r[1] for r in con.execute("PRAGMA table_info(sso_pacifica_new)")]
surf_col = next(c for c in new_cols if "SURFACE" in c.upper() and "VOL" in c.upper())
new = pd.read_sql(f'SELECT ESTIMATED_SPILL_START_DATE_AND_TIME sd, '
                  f'"{surf_col}" surf, '
                  f'"ESTIMATED_TOTAL_SPILL_VOLUME_EXITING_THE_SYSTEM_(GAL)" tot, '
                  f'SPILL_LOCATION_NAME loc FROM sso_pacifica_new', con)
new["d"] = pd.to_datetime(new.sd, errors="coerce")
new["gal"] = pd.to_numeric(new.surf, errors="coerce").fillna(
    pd.to_numeric(new.tot, errors="coerce"))
sp = pd.concat([old[["d", "gal", "loc"]], new[["d", "gal", "loc"]]], ignore_index=True)
sp = sp[(sp.gal > 0) & sp.d.notna() & (sp.d >= START)].sort_values("d")
SPILLS = [{"d": r.d.strftime("%Y-%m-%d"), "gal": int(round(r.gal)),
           "loc": str(r.loc).strip().title() if pd.notna(r.loc) and str(r.loc).strip() else "location not given"}
          for r in sp.itertuples()]
spill_days = pd.to_datetime([s["d"] for s in SPILLS])


def enrich(df, add_nd=False):
    """Attach hover-card context (hour, rain state, warmth, spill window)."""
    rows = []
    for r in df.itertuples():
        d = r.date
        c = ctx.loc[d] if d in ctx.index else None
        rec = {"d": d.strftime("%Y-%m-%d"), "v": int(r.v) if float(r.v).is_integer() else float(r.v),
               "hr": round(r.hr, 1) if pd.notna(r.hr) else None,
               "dsr": float(c.days_since_rain) if c is not None and "days_since_rain" in c else None}
        rows.append((rec, r))
    return rows


# rain columns needed per-sample
rc2 = pd.read_sql("SELECT date, days_since_rain, last_event_mm, prev3, wy_pct_normal "
                  "FROM rain_context WHERE date >= ?", con, params=[START])
rc2["date"] = pd.to_datetime(rc2.date)
rcx = rc2.set_index("date")
air7 = daily.set_index("date").air7


def sample_rows(df, add_nd=False, add_sp=False):
    out = []
    for r in df.itertuples():
        d = r.date
        rec = {"d": d.strftime("%Y-%m-%d"),
               "v": int(r.v) if float(r.v).is_integer() else round(float(r.v), 1),
               "hr": round(float(r.hr), 1) if pd.notna(r.hr) else None}
        if d in rcx.index:
            c = rcx.loc[d]
            rec["dsr"] = round(float(c.days_since_rain), 1)
            rec["ev"] = round(float(c.last_event_mm), 1)
            rec["p3"] = round(float(c.prev3), 1)
            rec["wy"] = round(float(c.wy_pct_normal), 1) if pd.notna(c.wy_pct_normal) else None
        rec["t7"] = round(float(air7.get(d, np.nan)), 1) if pd.notna(air7.get(d, np.nan)) else None
        if add_sp:
            rec["sp"] = bool(((d - spill_days) / pd.Timedelta(days=1)).map(
                lambda x: 0 <= x <= 7).any()) if len(spill_days) else False
        if add_nd:
            rec["nd"] = bool(r.nd)
            if pd.notna(r.hr) and r.hr > 0:  # 00:00 = missing-time sentinel
                ts = d + pd.Timedelta(minutes=int(round(r.hr * 60)))
                rec["th"], rec["ti"], rec["tp"] = tide_at(ts)
        out.append(rec)
    return out


# ---- county creek (E. coli, 2015-09-21 ->) ---------------------------------
ck = pd.read_sql("""SELECT SampleDate, CollectionTime, Result FROM ceden_raw
                    WHERE StationName LIKE '%San Pedro Creek%'
                    AND Analyte LIKE '%E. coli%'""", con)
ck["date"] = pd.to_datetime(ck.SampleDate).dt.normalize()
ck["v"] = pd.to_numeric(ck.Result, errors="coerce")
ck["hr"] = pd.to_datetime(ck.CollectionTime, errors="coerce").dt.hour \
    + pd.to_datetime(ck.CollectionTime, errors="coerce").dt.minute / 60
ck = (ck.dropna(subset=["v"]).groupby("date", as_index=False)
      .agg(v=("v", "max"), hr=("hr", "first")).sort_values("date"))
CREEK = sample_rows(ck, add_sp=True)
cke = pd.read_sql("""SELECT SampleDate, CollectionTime, Result FROM ceden_raw
                     WHERE StationName LIKE '%San Pedro Creek%'
                     AND Analyte LIKE '%Enterococcus%'""", con)
cke["date"] = pd.to_datetime(cke.SampleDate).dt.normalize()
cke["v"] = pd.to_numeric(cke.Result, errors="coerce")
cke["hr"] = pd.to_datetime(cke.CollectionTime, errors="coerce").dt.hour \
    + pd.to_datetime(cke.CollectionTime, errors="coerce").dt.minute / 60
cke = (cke.dropna(subset=["v"]).groupby("date", as_index=False)
       .agg(v=("v", "max"), hr=("hr", "first")).sort_values("date"))
# weeks where the county ran enterococcus INSTEAD of E. coli get their own rows
have = {r["d"] for r in CREEK}
extra = cke[~cke.date.dt.strftime("%Y-%m-%d").isin(have)]
if len(extra):
    for rec in sample_rows(extra, add_sp=True):
        rec["ent"] = rec.pop("v")
        rec["v"] = None
        CREEK.append(rec)
entby = {r.date.strftime("%Y-%m-%d"): float(r.v) for r in cke.itertuples()}
for rec in CREEK:
    if rec["v"] is not None and rec["d"] in entby and "ent" not in rec:
        ev = entby[rec["d"]]
        rec["ent"] = int(ev) if float(ev).is_integer() else round(ev, 1)
CREEK.sort(key=lambda r: r["d"])

# ---- tide series for beach hover ------------------------------------------
tide = pd.read_sql("SELECT * FROM tide_hourly", con)
tide["dt"] = pd.to_datetime(tide.dt)
tide["h"] = pd.to_numeric(tide.height_m)
tide = tide.sort_values("dt")
TT = tide.dt.values.astype("datetime64[s]").astype(np.int64)
HH = tide.h.values
_m = (HH[1:-1] >= HH[:-2]) & (HH[1:-1] > HH[2:])
_i = np.where(_m)[0] + 1
_d = HH[_i - 1] - 2 * HH[_i] + HH[_i + 1]
_o = np.where(_d < 0, 0.5 * (HH[_i - 1] - HH[_i + 1]) / _d, 0.0)
HIGHS = TT[_i] + _o * 3600  # high-water epochs, parabola-refined


def tide_at(ts):
    t = ts.value // 10**9
    h = float(np.interp(t, TT, HH))
    rate = float(np.interp(t + 1800, TT, HH) - np.interp(t - 1800, TT, HH))
    n = int(np.clip(np.searchsorted(HIGHS, t), 1, len(HIGHS) - 1))
    pg, ng = t - HIGHS[n - 1], HIGHS[n] - t
    ph = (pg if pg <= ng else -ng) / 3600.0  # signed hours from nearest high
    return round(h * 3.28084, 1), 1 if rate >= 0 else 0, round(ph, 1)


# ---- county beach LM5 (enterococcus, 2000-05-16 ->) ------------------------
bc = pd.read_sql("""SELECT SampleDate, CollectionTime, Result, ResultQualCode
                    FROM ceden_raw WHERE StationName LIKE '%#5%'
                    AND Analyte LIKE '%Enterococcus%'""", con)
bc["date"] = pd.to_datetime(bc.SampleDate).dt.normalize()
bc["v"] = pd.to_numeric(bc.Result, errors="coerce")
bc["hr"] = pd.to_datetime(bc.CollectionTime, errors="coerce").dt.hour \
    + pd.to_datetime(bc.CollectionTime, errors="coerce").dt.minute / 60
bc["ndrow"] = bc.ResultQualCode == "<"
bc = (bc.dropna(subset=["v"]).groupby("date", as_index=False)
      .agg(v=("v", "max"), hr=("hr", "first"), nd=("ndrow", "all")).sort_values("date"))
BEACH = sample_rows(bc, add_nd=True)
bce = pd.read_sql("""SELECT SampleDate, Result FROM ceden_raw
                     WHERE StationName LIKE '%#5%'
                     AND Analyte LIKE '%E. coli%'""", con)
bce["date"] = pd.to_datetime(bce.SampleDate).dt.normalize()
bce["v"] = pd.to_numeric(bce.Result, errors="coerce")
bce = bce.dropna(subset=["v"]).groupby("date").v.max()
for rec in BEACH:
    ev = bce.get(pd.Timestamp(rec["d"]))
    if ev is not None and pd.notna(ev):
        rec["ec"] = int(ev) if float(ev).is_integer() else round(float(ev), 1)

# ---- coalition sites (2024-07 ->) ------------------------------------------
lm = pd.read_sql("""SELECT date, analyte, site, value FROM lmwq_long
                    WHERE value IS NOT NULL AND (org LIKE '%Coalition%'
                       OR (org LIKE '%County%' AND site LIKE 'LM 5%'))""", con)
lm["analyte"] = lm.analyte.map({"ecoli": "ec", "ent": "ent"})
lm = lm.dropna(subset=["analyte"])
lm["code"] = lm.site.map(NAME2CODE)
lm = lm.dropna(subset=["code"])
lm["date"] = pd.to_datetime(lm.date)
wide = (lm.groupby(["date", "code", "analyte"]).value.max().unstack("analyte")
        .reset_index().sort_values(["date", "code"]))
SITES = [{"d": r.date.strftime("%Y-%m-%d"), "s": r.code,
          "ent": None if pd.isna(getattr(r, "ent", np.nan)) else round(float(r.ent), 1),
          "ec": None if pd.isna(getattr(r, "ec", np.nan)) else round(float(r.ec), 1)}
         for r in wide.itertuples()]

# ---- Surfrider BWTF creek mouth (enterococcus, 2013-12 ->) -----------------
bw = pd.read_sql(
    """SELECT collection_date, "collection time (America/Los_Angeles)" AS ctime, entero
       FROM bwtf_lindamar
       WHERE "site name" = 'Linda Mar Beach/San Pedro Creek'""", con)
bw["date"] = pd.to_datetime(bw.collection_date, errors="coerce").dt.normalize()
bw["v"] = pd.to_numeric(bw.entero, errors="coerce")
t = pd.to_datetime(bw.ctime, errors="coerce")
bw["hr"] = t.dt.hour + t.dt.minute / 60
bw = (bw.dropna(subset=["date", "v"]).groupby("date", as_index=False)
      .agg(v=("v", "max"), hr=("hr", "first")).sort_values("date"))
BWTF = sample_rows(bw)

con.close()

data = {"daily": DAILY, "creek": CREEK, "beach": BEACH,
        "spills": SPILLS, "sites": SITES, "bwtf": BWTF, "geo": GEO}
OUT.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
print(f"daily {len(DAILY)} ({DAILY[0]['d']} -> {DAILY[-1]['d']})")
print(f"creek {len(CREEK)}  beach {len(BEACH)} (nd={sum(1 for b in BEACH if b['nd'])})")
print(f"spills {len(SPILLS)} ({SPILLS[0]['d']} -> {SPILLS[-1]['d']})  sites {len(SITES)}")
print(f"creek ent {sum(1 for r in CREEK if 'ent' in r)}  beach ec {sum(1 for r in BEACH if 'ec' in r)}")
from collections import Counter
print("site rows by code:", dict(Counter(r['s'] for r in SITES)))
print("sites with ec:", sum(1 for r in SITES if r.get('ec') is not None))
print(f"bwtf {len(BWTF)} ({BWTF[0]['d']} -> {BWTF[-1]['d']}, "
      f"pre-2015-09: {sum(1 for r in BWTF if r['d'] < '2015-09-21')})")
print(f"json {OUT.stat().st_size/1024:.0f} KB")
