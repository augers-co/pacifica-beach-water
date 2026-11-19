# Open data: check our work

This folder holds the public data behind our simple rule for how likely a
weekly county test at the mouth of San Pedro Creek (Linda Mar beach, Pacifica,
California) is to fail the bacteria standard. It is here so that anyone can
rerun the numbers, find mistakes, and suggest something better.

Nothing in this folder says the water is safe. The rule gives a chance that a
test fails. A low chance is still a chance.

San Mateo County Environmental Health did the county sampling, Surfrider's
Blue Water Task Force and the Linda Mar Water Quality Coalition do their own
sampling, and the state, NOAA, USGS and Open-Meteo supply the other records.
We did none of the sampling.

## What is in this folder

| File | What it is |
|---|---|
| `county_ocean_tests.csv` | Updated weekly. Every county ocean test at the creek mouth (county station LM5, enterococcus bacteria) since 2000, one row per sampling day. |
| `daily_rain_and_ground.csv` | Updated weekly. One row per day since 1998: modelled rain and two "how wet is the valley" indexes built from rain alone. |
| `rule_v0_1_worked.csv` | **This file never changes.** It is the frozen record of version 0.1 of the rule: the 243 tests from 2022-01-03 to 2026-10-19, with the inputs exactly as they were when the rule was fixed, and the arithmetic worked out row by row so you can check it in a spreadsheet. (The rain archive revises past rain a little each week, and new tests keep arriving, so rebuilt inputs drift; this file is the fixed reference.) |
| `forecast_log.csv` | Forecasts written down each day before the outcome is known (added to daily; never edited). |
| `forecast_scored.csv` | The logged forecasts lined up against the county's results as they arrive. Rebuilt weekly. |
| `build/pacifica-open.sqlite` | The whole database in one file (not stored in the repository; see "Check it yourself", route c). |

The forecast log records the weather forecast as it stood when each forecast
was made (rain, temperature, sunshine, wind and sea state), not only the rule's
answer. The scored file adds what actually happened on each test day, so the
rule's result can be recomputed with the real weather. Any change to the rule
is to be judged on the rule fed the actual weather; error in the weather
forecast is reported separately, because it is not the rule's fault. A blank
cell in the log means the service gave no value that day. The log is only ever
added to, never edited.

### Columns

| Column | Found in | Meaning |
|---|---|---|
| `date` | all three CSVs | Calendar day, year-month-day. |
| `result_mpn` | tests, worked | Bacteria count: enterococcus, most probable number per 100 mL. If the county ran more than one sample that day, the highest. |
| `failed` | tests, worked | 1 if `result_mpn` is over 104 (the state's single-sample standard), otherwise 0. |
| `far_over` | tests, worked | 1 if `result_mpn` is over 312 (three times the standard), otherwise 0. |
| `rain_mm` | daily | Modelled rain for the creek valley that day, in millimetres. |
| `flow_idx` | daily | An index of how much recent rain is still moving through the valley (built from rain alone). |
| `ground_idx` | daily | An index of how wet the valley's soil and water table are, as known through the day before. Built from rain alone. |
| `rain3_mm` | worked | Rain on the test day and the two days before it, added up (mm). |
| `ground_idx` | worked | The ground index for the test day. |
| `ln_1_plus_rain3` | worked | The natural log of (1 + `rain3_mm`). |
| `log10_ground` | worked | The base-10 log of `ground_idx`, with `ground_idx` raised to 1 if it is below 1. |
| `z` | worked | The rule's score: 2.051 + 0.770 x `ln_1_plus_rain3` - 1.363 x `log10_ground`. |
| `chance` | worked | The rule's chance (0 to 1) that the test fails: 1 / (1 + e^(-z)). |
| `level` | worked | `chance` in words: lower than usual (under 0.50), usual (0.50 to 0.70), high (0.70 to 0.85), very high (0.85 or more). |
| `chance_held_out` | worked | The same chance, but worked out with every test from that calendar year left out when fitting the equation. This is the fairer test of whether the rule works. |
| `issued_at_utc`, `issue_date` | log | When the forecasts were written (UTC), and that day's date in Pacific time. Seven rows are written each day, one per target date. |
| `target_date`, `lead_days` | log | The day being forecast, and how many days ahead of `issue_date` it is (0 to 6). |
| `rain3_mm`, `rain3_forecast_mm`, `ground_idx`, `chance`, `level`, `rule_version` | log | The rule's inputs and result, as in the worked file. `rain3_forecast_mm` is the part of `rain3_mm` that was forecast rather than measured. |
| `rain_day0_mm`, `rain_day1_mm`, `rain_day2_mm` | log | The three daily rain values (mm) that add up to `rain3_mm`: the target day, the day before, and two days before. |
| `rain_day0_src`, `rain_day1_src`, `rain_day2_src` | log | Where each of those came from: `archive` (the rain archive), `recent` (the forecast service's estimate for a past day the archive does not have yet), or `forecast`. |
| `rain_prob_max_pct` | log | The forecast's highest chance of rain that day, per cent. |
| `temp_mean_c`, `temp_max_c`, `temp_min_c` | log | Forecast mean, highest and lowest air temperature for the target day, degrees C. |
| `sun_mj_m2` | log | Forecast sunshine for the day (total solar energy, MJ per square metre). |
| `wind_max_kmh`, `wind_dir_deg` | log | Forecast top wind speed (km/h) and dominant wind direction (degrees, the direction the wind blows from). |
| `wave_height_max_m`, `wave_period_max_s`, `wave_dir_deg` | log | Forecast highest wave (m), longest wave period (seconds) and dominant wave direction (degrees) offshore. |
| `sea_temp_c` | log | Forecast mean sea surface temperature for the day, degrees C. |
| `sea_lat`, `sea_lon` | log | The sea point the marine forecast actually used (the request was for 37.60 N, 122.51 W, just offshore of Linda Mar beach). |
| `weather_source` | log | The services the weather and sea values came from. |
| `rain3_actual_mm`, `ground_actual` | scored | The rain over the test day and the two days before, and the ground index, as the database holds them when the file is rebuilt (the rain archive revises past rain a little). |
| `chance_actual_weather`, `level_actual_weather` | scored | What the rule gives when it is fed that actual rain and ground index. |
| `chance_lead0` to `chance_lead6`, `level_lead0` to `level_lead6` | scored | The chance and level that were logged for that test date, 0 to 6 days ahead. |
| `rain3_error_mm_lead0`, `_lead1`, `_lead3` | scored | Logged `rain3_mm` minus `rain3_actual_mm` (mm); plus means more rain was forecast than fell. |
| `temp_mean_c_lead1`, `temp_mean_actual_c`, `sun_mj_m2_lead1`, `sun_actual_mj_m2` | scored | The temperature and sunshine forecast logged one day ahead, beside what the archive says happened. |

A blank cell means no value was available.

## Where the data comes from, and the terms

Every source below is public. The terms were read on the pages named, on
2026-11-18. Where a source states none, this says "terms not found" or "terms
not stated by the source" rather than guessing.

### Included

| Source | What it provides | Where to get it yourself | Included here | Terms, and the credit it asks for |
|---|---|---|---|---|
| State Water Resources Control Board (CEDEN), for San Mateo County Environmental Health | The county's weekly bacteria tests, including station LM5 at the creek mouth | https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results | Yes (`ceden_raw`, and the test list above) | Rights field on that page: "No Restrictions on Public Use"; no licence named. No credit required; see Credits. |
| State Water Resources Control Board (BeachWatch) | Beach bacteria results and advisories / postings | https://data.ca.gov/dataset/beach-water-quality-postings-and-closures | Yes (`beachwatch_raw`, `advisories_raw`) | "No Restrictions on Public Use"; licence: Open Data Commons Attribution License. Credit required; see Credits. |
| Open-Meteo (ERA5 reanalysis) | Modelled daily and hourly rain, temperature, sunshine for the creek valley | https://archive-api.open-meteo.com/v1/archive | Yes (`weather_daily`, `wx_extra_daily`, `rain_hourly`) | Creative Commons Attribution 4.0 (https://open-meteo.com/en/licence); the free service is for non-commercial use. Credit required; see Credits. The terms of the upstream Copernicus ERA5 licence were not read. |
| This project, from the Open-Meteo rain | The wetness indexes (`flow_idx`, `ground_idx`) | built by `pipeline/features.py` | Yes (`rain_context`) | Same as Open-Meteo above. |
| NOAA CO-OPS | Hourly tide predictions, Princeton / Half Moon Bay, station 9414131 | https://api.tidesandcurrents.noaa.gov/api/prod/datagetter | Yes (`tide_hourly`) | Public domain (https://www.tidesandcurrents.noaa.gov/disclaimers.html); must not be modified and then presented as official government material. Credit requested; see Credits. |
| U.S. Geological Survey | Daily flow at coastal stream gauges elsewhere on the peninsula, and a dry-weather flow index built from three of them | https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items | Yes (`donor_flow_daily`, `baseflow_daily`) | U.S. public domain (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits). Credit requested; see Credits. |

### Deliberately not included

| Source | Why it is not reposted | Where to get it yourself | How to rebuild the full database with our code |
|---|---|---|---|
| Linda Mar Water Quality Coalition: weekly results at four sites along San Pedro Creek | These results belong to the Coalition and are theirs to release. Terms not found. | https://www.lindamarwaterquality.org/test-results | `pipeline/refresh.py` fetches the spreadsheets and `pipeline/parse_lmwq.py` reads them into table `lmwq_long` of `data/pacifica.db`. The forecast rule does not use them. |
| Surfrider Foundation, San Mateo County Blue Water Task Force: volunteer results at Linda Mar sites | Surfrider publishes no reuse terms for these results, so permission is needed first (ask Surfrider). | https://bwtf.surfrider.org/ (the portal's annual download is https://mmvk4falrj.execute-api.us-west-2.amazonaws.com/v1/annual?year=YYYY) | `pipeline/fetch_bwtf.py` reads it into table `bwtf_lindamar`. The forecast rule does not use it. |
| State Water Resources Control Board: Pacifica sewer-spill reports (2023 on) | Terms not stated by the source. | https://www.waterboards.ca.gov/water_issues/programs/sso/docs/data_files/Cat1-2-3-Spills.txt | `pipeline/refresh.py` reads it into table `sso_pacifica_new`. The forecast rule does not use it. |
| State Water Resources Control Board: Pacifica sewer-spill reports (2007 to mid-2023) | Terms not stated by the source. The state has retired this file. | no public link recorded; our saved copy of the Pacifica rows is `pipeline/sso_legacy_pacifica.csv` | `pipeline/refresh.py` reads that file into table `sso_pacifica_old`. The forecast rule does not use it. |
| Hourly sky cover, Half Moon Bay airport | The repository does not record where this came from, so terms cannot be checked (terms not found). | no public link recorded | No script in `pipeline/` fetches or reads it (table `asos_haf`). The forecast rule does not use it. |

The same list, one row per source, is in the `about` table of the database file.

### Credits

The county's tests were taken by San Mateo County Environmental Health,
Surfrider's Blue Water Task Force and the Linda Mar Water Quality Coalition do
their own sampling, and we are grateful to all of them. We did none of the sampling.

- Weather data by Open-Meteo.com (licence: https://open-meteo.com/en/licence; CC BY 4.0). Changes: we sum, index and log-transform the rain.
- Generated using Copernicus Climate Change Service information (ERA5), 2026.
- Source: State Water Resources Control Board, BeachWatch and CEDEN (data.ca.gov). The BeachWatch tables are used under the Open Data Commons Attribution License.
- Tide predictions: NOAA National Ocean Service, CO-OPS. Not official NOAA material; we have only copied it.
- Credit: U.S. Geological Survey.

## Check it yourself

### a. No code: a spreadsheet

1. Open `rule_v0_1_worked.csv` in Excel, Numbers or Google Sheets. The columns
   are A `date` through L `chance_held_out`.
2. Pick any row, say row 2. The two inputs are `rain3_mm` (column E) and
   `ground_idx` (column F). Everything else can be worked out from those.
3. In free cells type:
   - `ln_1_plus_rain3`: `=LN(1+E2)`
   - `log10_ground`: `=LOG10(MAX(F2,1))`
   - `z`: `=2.051+0.770*(LN(1+E2))-1.363*(LOG10(MAX(F2,1)))`
   - `chance`: `=1/(1+EXP(-(2.051+0.770*LN(1+E2)-1.363*LOG10(MAX(F2,1)))))`
4. They should match columns G, H, I and J to about six decimal places.
5. Compare `chance` with `failed` over all rows if you like: in the record,
   tests the rule called "high" or "very high" failed far more often than ones
   it called "lower than usual", but the "lower than usual" days still failed
   more than a third of the time.

### b. One command

You need Python with numpy and pandas. From a clone of this repository:

```
pip install numpy pandas
python pipeline/forecast_rule.py
```

That is all: no database, and the only data file it reads is the frozen
`rule_v0_1_worked.csv`. It reproduces version 0.1 exactly, the same on every
machine and on every day. The numbers to expect:

- 243 tests, 2022-01-03 to 2026-10-19; 150 failed; 61 were far over.
- `z = +2.051 +0.770*ln(1+R3) -1.363*log10(G)`
- Ranking score (AUC) for failures, each year predicted from the other four
  years: 0.726 (far over: 0.795); Brier score 0.202. Predicting 2024 to 2026
  from earlier years only: 0.712 (far over: 0.755); Brier 0.216.
- Levels, on those held-out predictions: lower than usual 74 tests (36% failed),
  usual 64 (62%), high 74 (76%), very high 31 (87%).

To see what the same method gives on today's data, add `--refit`:

```
python pipeline/forecast_rule.py --refit
```

It uses the database if you have one, otherwise the two weekly-updated files
here (`county_ocean_tests.csv` and `daily_rain_and_ground.csv`), prints the same
report labelled as a refit on N tests through the latest date, and shows the
frozen coefficients beside the new ones. Those numbers drift a little each week,
because new tests arrive and the rain archive revises past rain; version 0.1
itself does not change.

AUC is the chance that a randomly chosen failing test was given a higher chance
than a randomly chosen passing one; 0.5 is a coin flip. Brier score is the
average squared error of the chances; lower is better, and 0.239 is what "no
forecast" scores.

### c. The whole database

Every table above, plus the full `about` table, is in one SQLite file, rebuilt
every week. Download `pacifica-open.sqlite` from the Releases page of the
repository (the release named `open-data`). Open it with a free tool such as
[DB Browser for SQLite](https://sqlitebrowser.org/), or from Python with
`sqlite3.connect("pacifica-open.sqlite")`. Start with the `about` table: it
says what each table holds, where it came from, how many rows, and what dates
it covers.

## Found a problem or an improvement?

Open an issue on this repository. Say what you ran, what you got, and what you
expected. A wrong number, a better input, a different rain window, or a
disagreement with the approach are all welcome. If your change would alter the
rule, say how it did on years it was not fitted to.

## Limits, plainly

- The two inputs and the rain window were chosen after looking at the whole
  record, so the held-out scores are somewhat flattering. A truly untouched
  test would likely score lower.
- With about 240 tests over five years, the coefficients are rough.
- The ground index is a stand-in built from rain alone. The rule cannot say
  what is behind the rise in the dry season (warmth, a low creek, or something
  else), and it is not evidence that wet ground carries pollution.
- Weekly tests sample one moment at one spot, and bacteria levels change
  within hours.
- None of the levels means the water is safe. A "lower than usual" day still failed more
  than a third of the time in the record.
