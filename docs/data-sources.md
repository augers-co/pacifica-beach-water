# Data source registry

Every source this project uses or has probed, with access method, coverage,
where it lands in `data/pacifica.db`, and status. Kept current as sources are
added or die. (Verification dates: 2026-08-14 unless noted.)

## Bacteria (response variables)

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **Linda Mar Water Quality Coalition** — canonical dataset per the Coalition; Surfrider feeds/draws from it | [lindamarwaterquality.org/test-results](https://www.lindamarwaterquality.org/test-results) → two xlsx (Enterococcus, E. coli; PDFs are print mirrors). File URLs change per upload — re-scrape the page to refresh. Raw copies in `data/lmwq/` + `Files/` (both gitignored; not ours to republish) | Weekly 2024-07 → present; 4 creek sites (LMMS, ADMS, PRLT, SPCM) + county LM5/LM7 same-morning + BWTF Thursday series (ends 2025-05); Creek Level + Rain flags | `lmwq_long` (via `pipeline/parse_lmwq.py`) | ✅ live |
| **CEDEN fecal indicator bacteria** (county weekly sampling) | CKAN datastore API, [dataset](https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results); resources: 2020+ `15a63495…`, 2010–20 `04d98c22…`, pre-2010 `1d333989…` | Linda Mar #5 2000→ (entero + E. coli + TC), #6 1998–2008, San Pedro Creek 2015→ (E. coli + TC; **entero added 2026-03**, n=4 so far); weekly; includes CollectionTime | `ceden_raw` (via `pipeline/fetch.py`) | ✅ live |
| **BeachWatch results + advisories** | CKAN: results `7bd961cf…`, advisories `d5cd6a23…`, [dataset](https://data.ca.gov/dataset/beach-water-quality-postings-and-closures) | LM5 1998→; StartTime 100% filled; advisory postings | `beachwatch_raw`, `advisories_raw` | ✅ live (⚠ covariate fields TidalHeight/SurfHeight/StormDrainFlow/Turbidity ~0% filled — dead end) |
| **Surfrider BWTF portal** | [bwtf.surfrider.org](https://bwtf.surfrider.org/) — internal AWS APIs (AppSync GraphQL; `…execute-api…/v1/annual?year=`); prefer a chapter export via Josh's contact | 12+ yr creek mouth | — | ⏳ export requested |
| Coalition site details (site codes + coordinates) | [testing-sites page](https://www.lindamarwaterquality.org/testing-sites): LMMS 37.58151,-122.47870 → ADMS 37.58687,-122.49490 → PRLT 37.58852,-122.49930 → SPCM 37.59625,-122.50550 (upstream→downstream) | — | — | ✅ confirmed geography |

## Weather & hydrology (predictors)

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **ERA5 daily precip** (watershed 37.585,-122.47) | Open-Meteo archive API, free, no key | 1998 → present, daily | `weather_daily` | ✅ live |
| **ERA5 hourly precip** (intensity features) | same, `hourly=precipitation` | 2015 → present | `rain_hourly` | ✅ live |
| **NOAA CO-OPS tide predictions** — Princeton/Half Moon Bay station **9414131** (open-coast reference station; Pacifica trails it ~5–10 min; deterministic → exact retroactively and forecastable ahead). SF gauge 9414290 used before 2026-08-15 — it runs 30–65 min behind the coast (inferences §6) | CO-OPS API, hourly predictions | 2000 → present (full LM5 era; extendable any range) | `tide_hourly` | ✅ live |
| **Donor stream gauges** — core analogs (coastal-draining, unregulated, marine-layer): San Gregorio 11162500, Pescadero 11162570, Soquel 11160000, San Lorenzo 11160500, + Pilarcitos 11162630 (flagged: partly regulated). Contrast-only, not analogs: San Francisquito 11164500 (bay side), Corralitos 11159200 (interior), Lagunitas 11460400 (Marin/Tomales Bay, regulated) | USGS OGC API `api.waterdata.usgs.gov` collection `daily`, param 00060 | 2014 → present, daily cfs | `donor_flow_daily` | ✅ live — core panel: flow_idx r=0.69–0.73, ground_idx r=0.65–0.74 |
| San Pedro Creek gauge | USGS 11162655 | 2 spot measurements ever (1977, 2015) | — | ❌ none exists |
| Groundwater (USGS wells 15G001/2M, 14E001M, 14F001M, 27R001M; DWR periodic network) | USGS OGC field-measurements; DWR CKAN `c4de0d7e…` | zero usable series; DWR has no coastal SM County stations | — | ❌ dead end |
| NWS forecast (QPF, for the forward-looking product) | `api.weather.gov` gridpoint | forecast horizon | — | 🔜 not yet wired |
| Waves (NDBC 46012 / CDIP), solar & water temp | NDBC/CDIP archives; Open-Meteo radiation | untested covariates | — | 🔜 candidate |

## Infrastructure & events

| Source | Access | Coverage | DB table | Status |
|---|---|---|---|---|
| **CIWQS sanitary sewer spills** — Pacifica = WDID **2SSO10100** (Agency "City of Pacifica", CS "Calera Crk Wtr Recycling Plant CS" — text-search "Pacifica" misses it; filter by WDID) | Flat files: [SSO.txt](https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/SSO.txt) (2007–2023-06), [Cat1-2-3-Spills.txt](https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Cat1-2-3-Spills.txt) (2023-06→), [Enrollee_Info.txt](https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Enrollee_Info.txt) (WDID map); tab-delimited, latin-1 | 157 spills 2007–2023 + 3 since; volumes, surface-water fractions, locations | `sso_pacifica_old`, `sso_pacifica_new` | ✅ live |
| Health-impacts survey (Coalition) | [Alchemer survey](https://survey.alchemer.com/s3/8923478/Linda-Mar-Health-Impacts-Survey) — aggregate results not public | — | — | 👀 watch |

## Aggregators / context (not model inputs)

- [smchealth.org/beaches](https://www.smchealth.org/beaches) — county advisisory map, hotline (650) 599-1266
- [Safe to Swim map](https://mywaterquality.ca.gov/safe_to_swim/) (state), [Heal the Bay BRC](https://beachreportcard.org/) — grades built on the same county data
- Prior art: EPA Virtual Beach, Stanford (Searcy & Boehm) CA nowcast frameworks, Heal the Bay NowCast
