# Data sources for a Linda Mar water quality forecast model

Goal: cross-analyze existing bacteria testing data with precipitation (and groundwater) to find correlates, then build a DB + model that turns real-time observations and weather forecasts into a water quality forecast ("nowcast") for Linda Mar / San Pedro Creek.

Verified 2026-08-14 unless marked otherwise.

## 1. Response variable — bacteria results

| Source | What | Access | Verified |
|---|---|---|---|
| **CA Open Data: Surface Water — Fecal Indicator Bacteria Results** ([dataset](https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results)) | CEDEN records. Station "San Pedro Creek-Pacifica State Beach" (37.596, -122.505), sampled by SM County Env Health. **694 records in the 2020–present resource alone**; separate resources for 2010–2020 and pre-2010. E. coli, enterococcus, coliform. | CKAN datastore API, resource `15a63495-8d9f-4a49-b43a-3092ef3106b9` (2020–present) | ✅ queried |
| **CA Open Data: Beach Water Quality Monitoring (BeachWatch)** ([dataset](https://data.ca.gov/dataset/beach-water-quality-postings-and-closures)) | **5,869 records for "Linda Mar Beach #5"** (beach: Pacifica State Beach, EPA ID CA447069), weekly year-round. Bonus: per-sample covariate fields — `StormDrainFlow`, `Weather`, `TidalHeight`, `SurfHeight`, `Turbidity` (often null, but check fill rate). Also: **Beach Posting and Closures — Advisories** resource (`d5cd6a23`) = the official advisory outcome variable. | CKAN datastore API, results resource `7bd961cf-abe4-433b-8033-378161237ff3` | ✅ queried |
| **Surfrider BWTF portal** ([bwtf.surfrider.org](https://bwtf.surfrider.org/)) | 12+ years at San Pedro Creek mouth + the Coalition's 4 creek sites (the pollution-localization series). | Internal AWS APIs behind the SPA (AppSync GraphQL + API Gateway `…/v1/annual?year=`). **Better: get a raw export directly from the chapter** (bwtf@smc.surfrider.org) since we're working with the Coalition — cleaner than scraping their API, and they may share sub-site metadata not shown publicly. | ✅ endpoints found |
| **Coalition winter campaign (upcoming)** | Higher-frequency, more sites along the creek through the rainy season. | First-party — design our DB schema so their field sheets ingest directly; this becomes the highest-value training data for source localization. | n/a |

## 2. Precipitation — the primary suspected correlate

San Pedro Creek's watershed is small (~8 mi²) and steep (Montara Mountain), so gauge placement matters; prefer gridded radar-blend products plus any in-valley gauge.

| Source | What | Access |
|---|---|---|
| **NOAA MRMS / Stage IV radar-gauge QPE** | Gridded precip (~1–4 km), hourly. Best spatial truth for a small coastal watershed; use to build antecedent rainfall features (1h/6h/24h/48h/72h, storm totals, season-to-date). | NOAA/NCEP archives, AWS Open Data |
| **PRISM daily** | 800 m/4 km daily precip, long record — good for backfilling the full 15-year training window. | prism.oregonstate.edu |
| **Personal weather stations (Pacifica)** | Hyperlocal real-time rain in/near the valley. Check the Wunderground map for Linda Mar/Park Pacifica stations; pull via **Synoptic Data API** (aggregates PWS + official networks, free research tier). ⚠ unverified which stations exist/are reliable | Synoptic Mesonet API |
| **NWS observations** | Nearest airport station Half Moon Bay (KHAF); SFO for long consistency. Coarse for this watershed but reliable. | NWS/NCEI APIs |
| **CoCoRaHS** | Volunteer daily gauges; check for Pacifica observers. ⚠ unverified | cocorahs.org |
| **Forecast: NWS `api.weather.gov`** | Gridpoint QPF (quantitative precip forecast) — free, no key; this is the *forward-looking* model input. NBM/HRRR for hourly detail. | api.weather.gov |

Consider: the Coalition installing one tipping-bucket gauge in the valley would anchor all gridded products.

## 3. Streamflow & groundwater — the gap column

| Source | Status |
|---|---|
| **USGS San Pedro Creek gauge** | ❌ **None active.** Site 11162655 "SAN PEDRO C A PACIFICA" has only two spot measurements (1977, 2015). No continuous discharge record exists for the creek. Flow must be *modeled* from rainfall (or the Coalition deploys a level logger — a ~$500 pressure transducer would be transformative for the winter campaign). |
| **USGS groundwater wells** | ❌ **Inventory only — no usable time series** (verified via `api.waterdata.usgs.gov` field-measurements, 2026-08-14). Four wells in/near the valley floor ([15G001M](https://waterdata.usgs.gov/monitoring-location/USGS-373517122295601/), [15G002M](https://waterdata.usgs.gov/monitoring-location/USGS-373517122295602/) — nested pair at 35 ft elev; [14E001M](https://waterdata.usgs.gov/monitoring-location/USGS-373513122293001/) at 60 ft; [14F001M](https://waterdata.usgs.gov/monitoring-location/USGS-373512122291601/) at 150 ft) return **zero** measurements. Up-valley well [27R001M](https://waterdata.usgs.gov/monitoring-location/USGS-373300122290001/) (482 ft elev) has exactly 2 visits: 2011 and 2021, depth-to-water ~314 ft (deep bedrock, irrelevant to shallow lateral infiltration). |
| **DWR periodic groundwater network** | ❌ **No coverage.** All 60 San Mateo County stations in DWR's Periodic Groundwater Level dataset are in the bayside "San Mateo Plain" basin; zero in Pacifica / San Pedro Valley, and none of the USGS state well numbers appear (verified via CKAN query, 2026-08-14). |
| **Practical groundwater proxy** | For the "shallow groundwater infiltrates leaky sewer laterals" mechanism, standard practice is proxying water-table state with **antecedent precipitation index + season-to-date cumulative rainfall**. If direct measurement matters for advocacy, a shallow piezometer + logger near the creek is cheap. |

## 4. Event & infrastructure data (tests the sewer hypothesis)

| Source | What |
|---|---|
| **CIWQS Sanitary Sewer Overflow reports** (State Water Board) | All reported SSOs by collection system incl. Pacifica, with date/volume/location — discrete contamination events to correlate against spikes. Public query/download. ⚠ access path unverified |
| **City of Pacifica sewer system** | Collection system maps, lateral inspection programs, lift station locations — context for siting and for the DNA source-tracking story. |

## 5. Ocean-side covariates (for the beach model)

| Source | What | Access |
|---|---|---|
| **NOAA CO-OPS tides** | SF station 9414290 predictions/observations; tide stage modulates creek-mouth dilution. | CO-OPS API |
| **NDBC / CDIP buoys** | Waves + SST: NDBC 46012 (Half Moon Bay), nearest CDIP buoy (likely Montara — verify). Wave height affects mixing/transport of the creek plume along the beach. | NDBC/CDIP APIs |
| **Solar radiation** | Drives bacteria die-off (day-of exceedance decay). CIMIS station or NLDAS. | CIMIS API |

## 6. Prior art — methodology to lean on

- **EPA Virtual Beach** — free EPA software purpose-built for statistical beach nowcast models (MLR/GBM on antecedent rain, flow, tide, waves). Using it, or replicating its approach, is the credibility shortcut for "holds up to scientific scrutiny."
- **Searcy & Boehm (Stanford)** — published data-driven coastal water quality prediction frameworks for California beaches; the Boehm lab is the academic center of gravity for exactly this problem (and geographically close — potential ally).
- **Heal the Bay NowCast** — operational daily predicted grades for a set of CA beaches, built on this same methodology. Precedent that agencies/public accept model-based advisories; Linda Mar is not currently one of their modeled beaches (opportunity).

## Suggested first analysis

Join county weekly results (15 yrs, Linda Mar #5 + San Pedro Creek stations) against PRISM/Stage IV antecedent rainfall features + tide + season. Logistic regression / gradient boosting on exceedance (single-sample standards). This is doable **now**, quantifies the rain→bacteria relationship the Coalition suspects, and tells us exactly how much lift real-time creek sensors would add.
