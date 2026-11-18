# Data source registry

Every source this project uses or has probed, with access method, coverage,
where it lands in `data/pacifica.db`, and status. Kept current as sources are
added or die. (Verification dates: 2026-08-14 unless noted.)

## Bacteria (response variables)

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **Linda Mar Water Quality Coalition** — canonical dataset per the Coalition; Surfrider feeds/draws from it | [lindamarwaterquality.org/test-results](https://www.lindamarwaterquality.org/test-results) → two xlsx (Enterococcus, E. coli; PDFs are print mirrors). File URLs change per upload — re-scrape the page to refresh. **Retention (2026-10):** the Oct 2026 enterococcus file was cut to 2026 only (and dated the 2026-07-06 week as 07-05), so results already published stay published when a later edition drops them; corrected values still win, re-dated copies keep the published date, and every refresh reports what it carried (export `retained` block). Raw copies in `data/lmwq/` + `Files/` (both gitignored; not ours to republish) | Weekly 2024-07 → present; 4 creek sites (LMMS, ADMS, PRLT, SPCM) + county LM5/LM7 same-morning + BWTF Thursday series (ends 2025-05); Creek Level + Rain flags | `lmwq_long` (via `pipeline/parse_lmwq.py`) | ✅ live |
| **CEDEN fecal indicator bacteria** (county weekly sampling) | CKAN datastore API, [dataset](https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results); resources: 2020+ `15a63495…`, 2010–20 `04d98c22…`, pre-2010 `1d333989…` | Linda Mar #5 2000→ (entero + E. coli + TC), #6 1998–2008, San Pedro Creek 2015→ (E. coli + TC; **entero added 2026-03**, n=4 so far); weekly; includes CollectionTime | `ceden_raw` (via `pipeline/fetch.py`) | ✅ live |
| **BeachWatch results + advisories** | CKAN: results `7bd961cf…`, advisories `d5cd6a23…`, [dataset](https://data.ca.gov/dataset/beach-water-quality-postings-and-closures) | LM5 1998→; StartTime 100% filled; advisory postings | `beachwatch_raw`, `advisories_raw` | ✅ live (⚠ covariate fields TidalHeight/SurfHeight/StormDrainFlow/Turbidity ~0% filled — dead end) |
| **Surfrider BWTF** — SMC chapter (a Coalition member) | Public "download annual data" export the portal itself uses: `GET https://mmvk4falrj.execute-api.us-west-2.amazonaws.com/v1/annual?year=YYYY&timezone=…` → one CSV/year, all chapters, no auth (robots.txt empty, checked 2026-08-15). `pipeline/fetch_bwtf.py` pulls & filters Linda Mar sites; raw in `data/bwtf/` (gitignored) | **Creek mouth** ("Linda Mar Beach/San Pedro Creek", 37.5962,-122.5056) Dec 2013→present, 476 samples, entero+E.coli; **beach transects** (Linda Mar North/South) 2012→2014; Coalition LMMS ("Linda Mar Bridge") recent | `bwtf_lindamar` | ✅ live (fetched 2026-08-15) |
| Coalition site details (site codes + coordinates) | [testing-sites page](https://www.lindamarwaterquality.org/testing-sites): LMMS 37.58151,-122.47870 → ADMS 37.58687,-122.49490 → PRLT 37.58852,-122.49930 → SPCM 37.59625,-122.50550 (upstream→downstream) | — | — | ✅ confirmed geography |

## Weather & hydrology (predictors)

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **ERA5 daily precip** (watershed 37.585,-122.47) | Open-Meteo archive API, free, no key | 1998 → present, daily | `weather_daily` | ✅ live |
| **ERA5 hourly precip** (intensity features) | same, `hourly=precipitation` | 2015 → present | `rain_hourly` | ✅ live |
| **NOAA CO-OPS tide predictions** — Princeton/Half Moon Bay station **9414131** (open-coast reference station; Pacifica trails it ~5–10 min; deterministic → exact retroactively and forecastable ahead). SF gauge 9414290 used before 2026-08-15 — it runs 30–65 min behind the coast (inferences §6) | CO-OPS API, hourly predictions | 2000 → present (full LM5 era; extendable any range) | `tide_hourly` | ✅ live |
| **Donor stream gauges** — core analogs (coastal-draining, unregulated, marine-layer): Pescadero 11162500, San Gregorio 11162570, Soquel 11160000, San Lorenzo 11160500, + Pilarcitos 11162630 (flagged: partly regulated). Contrast-only, not analogs: San Francisquito 11164500 (bay side), Corralitos 11159200 (interior), Lagunitas 11460400 (Marin/Tomales Bay, regulated). **Names verified against USGS 2026-11-18 — the first two were swapped in this project before that date** | USGS water data API `api.waterdata.usgs.gov` collection `daily`, param 00060 (falls back to the older `waterservices.usgs.gov` daily-values service); `pipeline/fetch_flow.py`, in the weekly refresh | 2000 → present, daily cfs | `donor_flow_daily` | ✅ live — core panel: flow_idx r=0.69–0.73, ground_idx r=0.65–0.74 |
| **Dry-weather flow index** (groundwater stand-in) — 7-day minimum flow at Pescadero, San Gregorio and Pilarcitos, averaged in log space (inferences §10) | derived in `pipeline/fetch_flow.py` | 2000 → present, daily | `baseflow_daily` | ✅ live — tracks the valley's measured water table at +0.71 |
| **Valley monitoring wells** (the only measured groundwater in the valley) | State Water Board GeoTracker county exports: `documents.geotracker.waterboards.ca.gov/data_download/geo_by_county/SanMateoGeoWell.zip` (depth to water) and `SanMateoGeoXY.zip` (well coordinates); `pipeline/validate_baseflow.py` | five cleanup sites in the valley, 2002–2016 (22 across Pacifica, to 2021); water table ~4–6.4 ft below ground | — (downloaded on demand) | ✅ validation only — nothing current |
| San Pedro Creek gauge | USGS 11162655 | 2 spot measurements ever (1977, 2015) | — | ❌ none exists |
| Groundwater (USGS wells 15G001/2M, 14E001M, 14F001M, 27R001M; DWR periodic network) | USGS OGC field-measurements; DWR CKAN `c4de0d7e…` | zero usable series; DWR has no coastal SM County stations | — | ❌ dead end |
| NWS forecast (QPF, for the forward-looking product) | `api.weather.gov` gridpoint | forecast horizon | — | 🔜 not yet wired |
| Waves (NDBC 46012 / CDIP), solar & water temp | NDBC/CDIP archives; Open-Meteo radiation | untested covariates | — | 🔜 candidate |

### Probed 2026-11-18 for the forecast work (not wired in)

| Source | Access | What it offers | Finding |
|---|---|---|---|
| NWS forecast for the valley | `api.weather.gov/gridpoints/MTR/80,98` | hourly rain, temperature, sky cover, 7 days ahead | needed for any look-ahead tool; nothing to backtest |
| National Water Model, reach 17687535 (San Pedro Creek) | live: `api.water.noaa.gov/nwps/v1/reaches/17687535/streamflow`; history: v3.0 retrospective (hourly 1979 – Jan 2023) on AWS open data | simulated flow and a groundwater bucket for the creek itself | tested and set aside — see inferences §10 |
| Rain gauges (CoCoRaHS via ACIS, `data.rcc-acis.org`) | `US1CASM0001` "Pacifica 0.3 W" (3 km north, complete daily since 2008); `US1CASM0033` "Pacifica 1.9 S" (inside the valley, since 2015-12, about half of days) | measured daily rain | ERA5 shows about half the gauge total on 25+ mm days; forecast gains small and not statistically clear |
| Calera Creek plant daily flow | data.ca.gov eSMR yearly resources, facility "Calera Creek Water Recycling Plant", parameter Flow, location E-001 | rain and groundwater entering the city's sewers, daily since 2014 | flow more than doubles after 25+ mm storms; no forecast gain; published weeks late |
| County's other stations (same CEDEN resources, q="San Mateo") | as CEDEN above | 36 other creeks and beaches, same mornings | no forecast gain; Linda Mar tracks them at 0.09 in dry weather, 0.47 on storm mornings |
| Offshore buoy 46237 (San Francisco Bar) | NDBC yearly `stdmet` files | waves, sea temperature | no forecast gain |
| Modelled soil moisture by depth | Open-Meteo archive, `soil_moisture_*` | ERA5-Land soil moisture | deep layer does not track the valley wells |
| County flood-warning creek sensors (Colma, El Zanjon, Green Hills, Belmont) | NOAA NWPS gauges API | creek level, 15-minute | only 30 days of history exposed; bay-side urban channels |

## Infrastructure & events

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **CIWQS sanitary sewer spills** — Pacifica = WDID **2SSO10100** (Agency "City of Pacifica", CS "Calera Crk Wtr Recycling Plant CS" — text-search "Pacifica" misses it; filter by WDID) | Flat files: legacy SSO.txt (2007–2023-06) **retired to an empty stub by the state 2026-10** — the Pacifica extract (157 spills) made before retirement is committed at `pipeline/sso_legacy_pacifica.csv` (closed-era record, immutable); [Cat1-2-3-Spills.txt](https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Cat1-2-3-Spills.txt) (2023-06→) still live-fetched, [Enrollee_Info.txt](https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Enrollee_Info.txt) (WDID map); tab-delimited, latin-1 | 157 spills 2007–2023 + 3 since; volumes, surface-water fractions, locations | `sso_pacifica_old`, `sso_pacifica_new` | ✅ live |
| Health-impacts survey (Coalition) | [Alchemer survey](https://survey.alchemer.com/s3/8923478/Linda-Mar-Health-Impacts-Survey) — aggregate results not public | — | — | 👀 watch |
| **In-creek construction timeline** (candidate explanations for record shifts) | Mouth restoration / managed retreat: constructed **2001–2003** ([ResilientCA](https://resilientca.org/projects/0d7cdcb8-3035-46f1-9042-b852f8d38bb9/); incl. Anza pump station renovation). **Hwy 1 bridge replacement + channel widening: in-creek construction Jun 2014 → ~Oct 2015** ([CEQA NOD 2005012126](https://ceqanet.lci.ca.gov/2005012126/2) approved 2013-07-19; [detour notice](https://www.pacificariptide.com/pacifica_riptide/2014/06/caltrans-new-highway-1-bridge-detour-begins-june-20.html)) — spans the 2014 beach-record break; county creek station begins Sep 2015, right after. **Adobe Drive fish passage (RCD SMC): culvert→free-span bridge, in-creek work dry season 2026** ([CEQA NOE 2026020624](https://ceqanet.lci.ca.gov/2026020624)) — the ADMS reach, ongoing during 2026 data | — | ✅ dated, sourced (2026-08-15) |
| **In-creek construction — fuller timeline** (verified against primary sources 2026-08-15; LLM-drafted list vetted, unverifiable items dropped) | 2000–03 flood control + managed retreat ([ResilientCA](https://resilientca.org/projects/0d7cdcb8-3035-46f1-9042-b852f8d38bb9/)); 2004 Capistrano Ave fish passage / mid-reach regrade ([CEQA 2003052028](https://ceqanet.lci.ca.gov/2003052028/3)); 2014–16 Hwy 1 bridge; **storm first-flush diverted from Linda Mar + Anza pump stations to treatment wetlands, built to cut beach coliform/E.coli** ([City of Pacifica](https://www.cityofpacifica.org/departments/public-works/wastewater-treatment/calera-creek-water-recycling/linda-mar-san-pedro-creek-wetlands), Prop 13; **construction dates unverified** — LLM's "2018–20" + its CEQA# 2012061091 are wrong, that SCH is a Pacific Grove project; project existence/purpose confirmed, build window not); 2026 Adobe Dr culvert→bridge. Dropped: 2021–22 CDFW study (no work), 2024–25 volunteer cleanup (minor) | — | ✅ verified, sourced |

## Aggregators / context (not model inputs)

- [smchealth.org/beaches](https://www.smchealth.org/beaches) — county advisisory map, hotline (650) 599-1266
- [Safe to Swim map](https://mywaterquality.ca.gov/safe_to_swim/) (state), [Heal the Bay BRC](https://beachreportcard.org/) — grades built on the same county data
- Prior art: EPA Virtual Beach, Stanford (Searcy & Boehm) CA nowcast frameworks, Heal the Bay NowCast
