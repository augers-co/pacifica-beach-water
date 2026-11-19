# Data files for building on this project

Small JSON files that a web page or a phone app can read. They are rebuilt by
`pipeline/export_api.py` and served at:

    https://augers-co.github.io/pacifica-beach-water/api/v1/

**This address may move to another domain later.** Keep the base address in
one setting in your code, not written into every request.

## What must be shown with the forecast

Wherever the forecast is shown, show these four sentences too (they are also in
each file as `caveats`):

- This forecast is experimental.
- It is not an official advisory.
- None of the levels means the water is safe.
- It estimates the chance that a county test fails; it does not predict illness.

For official postings, link to the county's beach page:
https://www.smchealth.org/beaches

## The promise

Every file has `"schema": 1`. Within schema 1, fields are only ever added; none
is renamed, removed or given a new meaning. Ignore fields you do not know. A
breaking change would get a new folder (`v2/`) and `"schema": 2`.

Every file also has `generated_at` (when the file was written, UTC, ISO 8601)
and `rule_version` (the version of the forecast rule, now `"0.1"`). A file is
not rewritten when nothing but `generated_at` would change, so `generated_at`
is the last time the content changed, not the last time the job ran.

## The `stale` rule

`forecast.json` has `issue_date` (a date in Pacific time) and `stale`. If
`stale` is true, **show no forecast**. Also check it yourself: if `issue_date`
is not today's date in Pacific time (America/Los_Angeles), treat the forecast
as stale and show no forecast. The file is only rewritten when the daily job
runs, so a missed day can leave `stale: false` in an old file.

## The files

### `forecast.json` (daily)

| Field | Meaning |
|---|---|
| `issue_date` | The Pacific date the forecast was made. |
| `issued_at_utc` | When it was made, UTC. |
| `stale` | True when `issue_date` was not today (Pacific) when the file was written. See above. |
| `caveats` | The four sentences above. |
| `days` | Seven entries, today and the next six days. |
| `days[].date` | The day forecast (Pacific). |
| `days[].lead_days` | Days ahead of `issue_date`, 0 to 6. |
| `days[].level` | The level in words: `lower than usual`, `usual`, `high`, `very high`. |
| `days[].level_key` | The same as a key: `lower`, `usual`, `high`, `very_high`. |
| `days[].chance` | The rule's chance, 0 to 1, that a county test on that day would fail (be over 104 MPN per 100 mL). |
| `days[].fail_share` | In the 2022-2026 record, the share of tests at this level that failed (0 to 1). |
| `days[].far_over_share` | The same, for tests far over the standard (over 312). |
| `days[].inputs.rain3_mm` | Rain on that day and the two days before, mm. |
| `days[].inputs.rain3_forecast_mm` | The part of `rain3_mm` that is forecast rather than measured, mm. |
| `days[].inputs.ground_idx` | How wet the valley's ground is, an index built from rain alone (no unit). |
| `days[].weather` | The weather forecast logged with it; `null` where the service gave no value. `rain_day0_mm`, `rain_day1_mm`, `rain_day2_mm` (mm: that day, the day before, two days before) and `rain_day0_src` .. `rain_day2_src` (`archive`, `recent` or `forecast`); `rain_prob_max_pct` (%); `temp_mean_c`, `temp_max_c`, `temp_min_c` (degrees C); `sun_mj_m2` (sunshine, MJ per square metre); `wind_max_kmh` (km/h); `wind_dir_deg`, `wave_dir_deg` (degrees, direction it comes from); `wave_height_max_m` (m); `wave_period_max_s` (s); `sea_temp_c` (degrees C); `sea_lat`, `sea_lon` (the sea point used); `weather_source` (text). |
| `days[].beyond_experience` | True when that day's inputs are outside what the rule was fitted on: more rain over three days, or a higher ground index, than in any of the 243 tests it was fitted on. Treat the chance with extra caution. |
| `days[].beyond_reason` | A short sentence saying why, or `null`. |
| `days[].push.rain3`, `days[].push.ground` | How much each of the rule's two inputs moves that day's `chance`, compared with the same day if that one input were at its median in the 243 tests the rule was fitted on (the other input unchanged). `points`: the difference in percentage points (positive means the input raises the chance). `direction`: `up`, `down` or `none`. `size`: `none` (under 2 points), `a_little` (2 to under 10) or `clear` (10 or more). This describes the rule's arithmetic only; it does not say what causes a failed test. |
| `days[].ground_normal` | That day's `ground_idx` beside its normal for the date, or `null`. `normal_idx`: the average ground index on the same day of the water year (October 1 is day 1, counted as in `pipeline/features.py`) across every year in `open-data/daily_rain_and_ground.csv` from `normal_from` to `normal_to` (the first months of 1998 are left out because the index starts from zero there). `years`: how many years went into the average. `pct_of_normal`: `ground_idx` as a per cent of `normal_idx`. `compared_to_normal`: `below` (under 70%), `near` (70% to 130%) or `above` (over 130%); the same cut-offs the project uses for dry and wet winters (`docs/inferences.md`, section 11). |
| `push_reference` | The medians used by `push`: `rain3_mm` and `ground_idx` among the `tests` the rule was fitted on (`open-data/rule_v0_1_worked.csv`). |

### `conditions.json` (daily)

The readings around today that the forecast page charts. The daily job fetches
them itself from Open-Meteo (the same point, services and rain handling as
`pipeline/forecast_log.py`). If that fetch fails, the file is left as it was;
check `as_of` and treat the file as out of date when it is not today's
Pacific date. Rain here is fetched minutes after the forecast log's, so a
recent day can differ slightly from the log; the forecast itself always uses
the log (`forecast.json`).

| Field | Meaning |
|---|---|
| `as_of` | The Pacific date the file was made. Day 0 below is this date. |
| `source`, `point` | The weather services used and the point (latitude, longitude) asked for: the San Pedro Creek watershed. |
| `days` | Twenty entries: the 13 days before `as_of`, `as_of` itself, and the 6 days after. |
| `days[].rain_mm` | Rain that day, mm. A weather-model estimate, not a gauge (`docs/inferences.md`, section 1). |
| `days[].rain_src` | `archive`, `recent` or `forecast`, as in the forecast log. |
| `days[].flow_idx` | Estimated creek flow, an index with no unit: F = 0.90 x yesterday's F + half of today's rain + half of yesterday's (`docs/inferences.md`, section 2). It halves about every 6.6 days once the rain stops. The page shows it as storm runoff. |
| `days[].ground_idx` | The ground-wetness index (`docs/inferences.md`, section 3), as known through the day before. |
| `days[].rain_shadow` | The rain shadow: S = 0.73 x yesterday's S + today's rain, in mm (`docs/inferences.md`, section 4). It halves about every 2.2 days. |
| `days[].air_temp_mean_c` | Mean air temperature that day, degrees C: the ERA5 archive for past days, the forecast where the archive has no value yet. |
| `days[].water_temp_est_c` | Estimated creek water temperature, degrees C: -1.59 + 1.05 x the mean air temperature of that day and the 6 before (at least 3 days needed). Fitted on Pescadero Creek, 1965-1979; not a measurement, at best +/- 2 degrees C (`docs/inferences.md`, section 5). This is the live page's "Water temp (est.)". |
| `rain_30d.from`, `rain_30d.to`, `rain_30d.total_mm` | Rain on `as_of` and the 29 days before, mm. |
| `rain_30d.forecast_mm` | The part of `total_mm` that is forecast rather than measured. |
| `rain_30d.storms[]` | The storms in that window. A rain event is a run of days with 1 mm or more each, and it counts as a storm when at least one of its days inside the window had 5 mm or more (the two thresholds in `pipeline/features.py`). `start`, `end` (an event may start before the window; `end` is at most `as_of`), `total_mm`, `wettest_day_mm`, `includes_forecast`. |
| `water_temp_trend` | `rising`, `falling` or `steady`: the estimate 3 days after `as_of` against the estimate on `as_of`; `steady` when they are less than 0.5 degrees C apart. |
| `flow_trend` | `peak` (flow on `as_of` is at least that of the day before and the day after), `rising` (the day after is higher) or `falling`. |

### `levels.json` (changes only with the rule)

| Field | Meaning |
|---|---|
| `standard` | The standard: enterococcus, MPN per 100 mL; a test fails when over 104 (single sample), and is far over when above 312. |
| `levels` | The four levels in order. |
| `levels[].key`, `levels[].name` | As `level_key` and `level` above. |
| `levels[].chance_min`, `levels[].chance_max` | The level's range of `chance`; `chance_min` is in the level, `chance_max` is not (except 1.0). |
| `levels[].tests` | How many tests in the 2022-2026 record fell in this level. |
| `levels[].fail_share`, `levels[].far_over_share` | The share of those tests that failed, and that were far over (0 to 1). Each year was predicted from a fit on the other years. These are not a promise. |
| `caveats` | The four sentences above. |

### `meta.json`

`files` (each file and what it holds), `links` (the repository, the open-data
guide, this guide, the county's beach page), `base_address` and
`address_note`.

### `latest_results.json` (weekly)

The most recent county test result for each county series shown on the
project's page. These arrive weeks after the sample; they are not current
conditions.

| Field | Meaning |
|---|---|
| `results[].series` | `lm5_enterococcus`, `lm5_e_coli`, `creek_e_coli`, `creek_enterococcus`, and `surfrider_creek_mouth_enterococcus` (see below). |
| `results[].station` | Where the sample was taken. |
| `results[].sampled_by` | Who took it (San Mateo County Environmental Health, or for the Surfrider series the Surfrider Foundation Blue Water Task Force, San Mateo County chapter). |
| `results[].source_url` | Where the results are published: the state's data page for the county series, https://bwtf.surfrider.org/ for the Surfrider series. |
| `results[].as_of` | The Pacific date the weekly job read the results. Newer results may exist at the source. |
| `results[].recent` | Only on `lm5_enterococcus`: the last eight county sampling days, oldest first, each with `date`, `result_mpn` (highest of the day) and `compared_to_standard` (over or under 104). |
| `results[].analyte` | The bacteria measured. |
| `results[].date` | Sample date. |
| `results[].result_mpn` | The result, MPN per 100 mL (highest of the day). |
| `results[].standard_mpn` | The single-sample standard the page uses for that series. |
| `results[].compared_to_standard` | `over` or `under` (`under` means not over: at or below the standard). |
| `results[].days_old` | Days from the sample date to the day the file was written. |

The Surfrider series is only the latest enterococcus result at Surfrider's
creek-mouth site ("Linda Mar Beach/San Pedro Creek"), the highest of that day,
judged against the freshwater standard of 110 that the project's page uses for
this site (`docs/inferences.md`, section 8). Surfrider's results are not
redistributed here: for the data, go to https://bwtf.surfrider.org/. Nothing
from the Linda Mar Water Quality Coalition's own results is in these files; see
https://www.lindamarwaterquality.org/test-results.

### `track_record.json` (weekly)

Each county test that had a forecast logged for it, so anyone can see how the
forecast did. Until a county result arrives for a forecast date, `tests` and
`summary` are empty and `note` says so.

| Field | Meaning |
|---|---|
| `tests[].date`, `tests[].result_mpn` | The test day and its enterococcus result (MPN per 100 mL). |
| `tests[].compared_to_standard` | `over` or `under` 104. |
| `tests[].far_over` | True if over 312. |
| `tests[].forecasts.lead0`, `.lead1`, `.lead3` | The `level`, `level_key` and `chance` logged that many days ahead, or `null`. |
| `summary[]` | For leads 0, 1 and 3 and each level: `tests`, `over`, `over_share`, beside `stated_fail_share` and `stated_tests` from `levels.json`. With few tests these shares swing a lot. |

## Reading `forecast.json`

JavaScript (browser):

```js
const BASE = "https://augers-co.github.io/pacifica-beach-water/api/v1/";
const f = await (await fetch(BASE + "forecast.json")).json();
const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
if (f.stale || f.issue_date !== today) { /* show no forecast */ }
else for (const d of f.days) console.log(d.date, d.level, d.chance);
```

Swift (Foundation):

```swift
struct Day: Decodable { let date: String; let level: String; let chance: Double }
struct Forecast: Decodable { let stale: Bool; let issue_date: String; let caveats: [String]; let days: [Day] }

let base = URL(string: "https://augers-co.github.io/pacifica-beach-water/api/v1/")!
let (data, _) = try await URLSession.shared.data(from: base.appendingPathComponent("forecast.json"))
let f = try JSONDecoder().decode(Forecast.self, from: data)
let fmt = DateFormatter(); fmt.locale = Locale(identifier: "en_US_POSIX")
fmt.dateFormat = "yyyy-MM-dd"; fmt.timeZone = TimeZone(identifier: "America/Los_Angeles")
if f.stale || f.issue_date != fmt.string(from: Date()) { /* show no forecast */ }
else { for d in f.days { print(d.date, d.level, d.chance) } }
```
