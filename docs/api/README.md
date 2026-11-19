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
| `results[].series` | `lm5_enterococcus`, `lm5_e_coli`, `creek_e_coli`, `creek_enterococcus`. |
| `results[].station` | Where the sample was taken. |
| `results[].sampled_by` | Who took it (San Mateo County Environmental Health). |
| `results[].analyte` | The bacteria measured. |
| `results[].date` | Sample date. |
| `results[].result_mpn` | The result, MPN per 100 mL (highest of the day). |
| `results[].standard_mpn` | The single-sample standard the page uses for that series. |
| `results[].compared_to_standard` | `over` or `under` (`under` means not over: at or below the standard). |
| `results[].days_old` | Days from the sample date to the day the file was written. |

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
