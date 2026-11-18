# Register of inferences and assumptions

Every derived quantity this project displays or models, with its math, what it
was fitted on, its validation, and its known weaknesses — so anyone with
better knowledge can interrogate or refit it. Code pointers are to this repo.
If you can improve one of these, the maintainers want to hear it.

## 1. Rainfall (the root input)

- **What:** daily & hourly precipitation at the watershed (37.585, −122.47).
- **Source:** ERA5 reanalysis via Open-Meteo — a weather-model estimate, not a
  gauge.
- **Rain gauges in and near the valley (corrected 2026-11-18; this register
  used to say none exists):** none has a complete record, which is why the
  weather model is the input.
  - Pacifica 4 SSE (USC00046599), the official cooperative station in the
    valley: November 1983 to November 2012, then closed.
  - Pacifica 1.9 S (US1CASM0033), a volunteer CoCoRaHS gauge in the valley:
    since December 2015, reporting on about half of days (19–61% a year
    since 2022).
  - Pacifica 0.3 W (US1CASM0001), a volunteer gauge about 3 km north of the
    valley: complete daily record since 2008.
  All three are public through NOAA's ACIS service (`data.rcc-acis.org`).
- **Checked against measured groundwater (2026-11-18):** the ground index
  (§3) driven by gauge rain (the valley station to 2012, then Pacifica 0.3 W)
  tracks the valley's well readings at +0.77, against +0.75 driven by ERA5
  (+0.37 against +0.30 with the seasonal cycle removed). The gain is small,
  so ERA5 stays the input: it is complete, uniform from 1998, and does not
  depend on one volunteer. `pipeline/validate_baseflow.py`, check 3.
- **Limitations:** single ~9 km grid cell; coastal orographic detail smoothed;
  we showed the same product's *radiation* misses the marine layer, so precip
  totals deserve similar skepticism at event scale. On days with 25 mm or
  more at the volunteer gauges, ERA5 shows about half the gauge total
  (probe of 2026-11-18, `docs/data-sources.md`).
- **To improve:** bias-correct storm totals against the Pacifica 0.3 W gauge;
  NOAA Stage IV/MRMS radar blend is the upgrade path. `pipeline/fetch.py`.

## 2. Estimated creek flow (`flow_idx`)

- **Formula:** F_t = 0.90·F_{t−1} + ½P_t + ½P_{t−1} (linear reservoir; storm
  input split across day 0/1 because small creeks crest fast and yesterday's
  rain is the strongest single-day predictor of morning samples).
- **Parameters chosen, not fitted:** retention 0.90/day (half-life ≈ 6.6 d).
- **Validation:** log–log daily r = 0.69–0.73 against five gauged analog
  creeks (San Gregorio, Pescadero, Soquel, San Lorenzo, Pilarcitos†), 2015–26.
  †partly regulated, flagged. Contrast gauges excluded by geography.
- **Limitations:** relative shape only — no gauged units, because San Pedro
  Creek has never had a gauge (USGS 11162655: two measurements, 1977 & 2015).
- **To improve:** one pressure-transducer level logger would calibrate it to
  real units. `pipeline/features.py`.

## 3. Ground wetness (`ground_idx`)

- **Formula:** G_t = 0.97·G_{t−1} + 0.10·F_{t−1} (slow store charged by the
  quick store's drainage — crests days after storms, drains over months).
- **Validation:** r = 0.65–0.74 against dry-season baseflow (= groundwater
  discharge) at the five analog creeks (rain-free Jun–Oct days, n = 1,460).
- **Checked against measured groundwater (2026-11-18):** monitoring wells at
  cleanup sites in the valley (State Water Board GeoTracker, 2002–2016) —
  rank correlation +0.75 with the measured water table across 68 site
  visits, +0.30 with the seasonal cycle removed. `pipeline/validate_baseflow.py`.
- **Drain rate checked against the wells (2026-11-18):** the index was
  rebuilt keeping 90% to 99.6% a day and each version scored against the
  valley wells. Rates of 2–4% a day fit about equally well (kept 0.96: +0.74;
  0.97: +0.75; 0.98: +0.76); slower rates fit worse (0.99: +0.64; 0.996:
  +0.34). In 300 resamples of the 68 visits the best rate was 0.98 in 134,
  0.97 in 55, 0.96 in 53. Wells elsewhere in Pacifica prefer a slower drain
  (0.99: +0.57 against +0.48 at 0.97). The 0.97 in use sits inside the
  supported range and is left unchanged. `pipeline/validate_baseflow.py`,
  check 2.
- **Timing checked (2026-11-18):** the measured water table does not lag the
  index — the correlation is highest with the same day's value (+0.75) and
  falls as the index is read earlier (30 days: +0.62; 60 days: +0.22; 90
  days: −0.01). Check 4.
- **Limitations:** the valley wells stop in 2016, and USGS and DWR have no
  wells there, so nothing measures the water table today and the checks
  above cover 2002–2016 only. The 0.97 retention was chosen, not fitted; the
  wells support it but cannot pin it more tightly than 2–4% a day. See §10
  for the measured stand-in that complements this index.
- **To improve:** a recession-curve refit on the analog creeks would be an
  independent check on the drain rate. `pipeline/features.py`.

## 4. Rain-shadow decay (the storm-influence window)

- **Formula:** S_t = 0.73·S_{t−1} + P_t; drawn where S ≥ 2, opacity
  ∝ √(S/80), capped 0.5.
- **Fitted on:** the measured clearance curve — excess exceedance above the
  dry baseline by days-since-rain (42 → 40 → 29 → 16 → ~0 points over days
  0–4 at the beach station, 2015–26) → daily retention ≈ 0.73 (half-life
  ≈ 2.2 days).
- **Deliberately different from flow decay (0.90):** risk clears ~3× faster
  than the water recedes — the first flush carries most of the load. Do not
  merge these constants; the gap is a finding.
- **To improve:** refit on creek-specific or season-specific clearance;
  higher-frequency sampling would sharpen it.

## 5. Water temperature (inferred from air)

- **Formula:** water ≈ −1.59 + 1.05 × (7-day trailing mean air temperature),
  applied to ERA5 air at the watershed.
- **Fitted on:** Pescadero Creek's daily water-temperature record (USGS
  11162500; this register named it San Gregorio Creek until 2026-11-18, when
  the two gauge labels were found to be swapped — the data and fit are
  unchanged) — 1965–1979, 3,935 paired days against ERA5 air at that site. r = 0.85,
  RMSE ≈ 2.1 °C.
- **Stability check:** refit on halves — 1965–71: (−1.35, 1.01);
  1972–79: (−1.86, 1.08) — predictions within ±0.5 °C of each other across
  the relevant range. The relation was not drifting within its own era.
- **Limitations (be loud about these):** the calibration era ends in 1979 —
  USGS discontinued water-temperature monitoring region-wide that February,
  and no public agency has measured creek water temperature on any analog
  creek since (CEDEN carries none for San Pedro Creek). Climate warming since
  1979 enters through the *air* series, but if the air↔water coupling itself
  changed (e.g., via reduced summer baseflow), the transfer would be biased.
  Cross-creek transfer (Pescadero → San Pedro) is assumed.
- **Modern tests (2026-08):** two live USGS water-temp stations exist within
  range — Pilarcitos below Stone Dam (11162620, ~11 mi away) and Alameda Ck
  below Calaveras (11172175) — both **dam-influenced reaches**. On 2024–26
  data they confirm the model form (linear coupling to 7-day air; r = 0.87
  and 0.88) but with damped slopes (0.73, 0.60) — exactly the reservoir
  buffering a managed reach should show. The free-flowing slope (1.05, San
  Gregorio) therefore stands for San Pedro Creek. Pilarcitos-below-dam is
  usable as a live regional sanity anchor (its residuals vs. air flag
  anomalies) but not as a direct level proxy.
- **To improve:** a single modern paired air/water season on a free-flowing
  analog creek (a $100 logger) would close the era gap outright. Until then
  treat ±2 °C as a floor on uncertainty.

## 6. Tides

- **Source:** NOAA harmonic predictions, **Princeton/Half Moon Bay station
  9414131** (open-coast reference station 14 mi south of Linda Mar), hourly,
  2000→present. Deterministic (exact retroactively, forecastable ahead).
  Switched from the SF Golden Gate gauge 9414290 on 2026-08-15 — see below.
- **Derived at each sampling minute** (`pipeline/tide_beach.py`): height and
  rate by linear interpolation of the hourly series; **phase** = signed hours
  from the nearest high water, with high-water times refined to minutes by a
  parabola through the three hourly points around each local maximum
  (negative = flood, positive = ebb).
- **Phase offset (measured 2026-08-15, corrected):** the open coast leads
  the SF gauge — Princeton/Half Moon Bay (9414131, a reference station 14 mi
  south of Linda Mar) turns **54–64 min earlier at highs, 32–52 min at lows**
  (12 turns compared). An earlier version of this register had the direction
  backwards. Pacifica, on the open coast, tracks Princeton far more closely
  than SF; phase computed from SF timing therefore *understates* local phase
  by up to ~1 h. The initial reading of this error as "attenuation only" was
  itself wrong: relabeling an hour of each cycle moved the clean around-high
  window into the "flood" class wholesale, which *manufactured* the v9
  first-publication ebb/flood split rather than understating it (see the
  findings-v9 correction).
- **Residual error:** the coastal tide propagates northward, so Pacifica
  turns an estimated ~5–10 min after Princeton — negligible against the
  12.4 h cycle. The switch's lesson (findings-v9 correction): an hour-scale
  clock error does not merely blur phase results, it can relabel them —
  the SF-timed "ebb effect" was an alias of the clean high-water window.

## 7. Replicate & censoring handling

- Same station/date/analyte replicates collapsed to the **maximum**
  (conservative toward exceedance; county-facing numbers may differ).
- Censored results are rare in this record (creek E. coli: 5 "<", 3 ">";
  0.6% at instrument caps) and are used at face value.

## 8. Standards applied

- Freshwater E. coli 320; freshwater enterococcus 110; ocean enterococcus
  104; ocean E. coli 320 (single-sample values). The creek mouth is brackish;
  the freshwater standard is applied there, following county practice.

## 9. Measurement noise (the floor under everything)

- Two labs sampling the same reach the same morning: pass/fail agreement 80%,
  log–log r = 0.56 (74 paired days). Single grabs carry ~±half-log noise.
  Every model and display treats this as the irreducible floor; claims are
  made on patterns across weeks, never single results.

## 10. Groundwater stand-in: dry-weather flow at neighbouring creeks (`baseflow_daily`)

- **What it is:** the lowest daily flow of the trailing 7 days at each of the
  three nearest gauged coastal creeks — Pescadero (USGS 11162500), San
  Gregorio (11162570), Pilarcitos at Half Moon Bay (11162630) — averaged in
  log space. In dry weather a creek carries groundwater draining out, so this
  is a measured signal of how much groundwater the coastal hills are
  releasing. `pipeline/fetch_flow.py`.
- **Why it is needed:** San Pedro Creek has no gauge and the valley has had no
  measured water table since 2016.
- **Checked against measured groundwater:** the valley's monitoring wells
  (GeoTracker; five cleanup sites, four with enough repeat readings,
  2002–2016; water table about 4 ft below ground in Jan–Apr and 6.4 ft in
  Aug–Oct) — rank correlation +0.71 across 68 site visits, +0.58 across 532
  visits at all Pacifica sites, +0.38 in the valley with the seasonal cycle
  removed. `pipeline/validate_baseflow.py` reproduces these.
- **Window and timing checked (2026-11-18):** against the valley wells a
  3-day low scores +0.73, the 7-day low in use +0.72, a 14-day low +0.64 and
  a 30-day low +0.49, so a short window is right. The water table does not
  lag the creeks: read 30 days earlier the flow scores +0.41, 90 days earlier
  −0.10. `pipeline/validate_baseflow.py`, check 4.
- **Alternatives tested and set aside (2026-11-18):** winter rain as percent of
  normal (+0.18 against the valley wells), modelled deep soil moisture
  (−0.02), and the National Water Model's simulated flow for San Pedro Creek
  itself (+0.34; it moves with the three measured creeks at 0.75–0.82 but is
  far flatter than reality and its archive ends January 2023).
- **Limitations:** the creeks are 15–35 km south and drain other watersheds;
  Pilarcitos is regulated upstream; the validation wells end in 2016; the
  latest days are provisional USGS values. This says how wet the region's
  ground is, not what is in the water.
- **To improve:** a staff gauge or level logger on San Pedro Creek itself.

## 11. Winter carry-over (the "Wet winters" view)

- **What the page shows:** county creek samples from June to September taken
  7 or more days after rain, grouped by the preceding winter's rain as a
  percent of normal on June 15 (dry under 70%, wet over 130%). Typical level
  (geometric mean) 165 after dry winters, 354 after normal ones, 496 after
  wet ones; 28%, 53% and 68% of samples over the single-sample standard
  (54, 60 and 63 samples). Recomputed 2026-11-18; findings v7 (August 2026)
  had 161 and 27% for the dry group.
- **How much it rests on:** twelve summers, eleven with five or more samples.

  | summer | winter, % of normal | group | samples | typical | over 320 |
  |---|---|---|---|---|---|
  | 2015 | 69 | dry | 2 | 287 | 1 |
  | 2016 | 105 | normal | 17 | 293 | 10 |
  | 2017 | 165 | wet | 12 | 693 | 10 |
  | 2018 | 69 | dry | 17 | 577 | 12 |
  | 2019 | 146 | wet | 17 | 603 | 12 |
  | 2020 | 68 | dry | 18 | 111 | 2 |
  | 2021 | 42 | dry | 17 | 67 | 0 |
  | 2022 | 98 | normal | 13 | 465 | 10 |
  | 2023 | 180 | wet | 16 | 423 | 10 |
  | 2024 | 134 | wet | 18 | 381 | 11 |
  | 2025 | 101 | normal | 15 | 436 | 6 |
  | 2026 | 111 | normal | 15 | 282 | 6 |

  The low dry-winter figure comes from 2020 and 2021. Summer 2018 followed a
  dry winter and ran as high as the wet-winter summers. Three of the four
  dry summers (2015, 2018, 2020) sit within two points of the 70% cut-off,
  on a rain total that is itself a weather-model estimate (§1).
- **Summer-by-summer test:** across the eleven summers, the summer's typical
  level against the winter's percent of normal: rank correlation +0.49
  (permutation p = 0.13), linear r = +0.67 (p = 0.02). Against that summer's
  dry-weather flow at the three neighbouring creeks (§10): r = +0.72
  (p = 0.02). `pipeline/validate_baseflow.py`, check 7.
- **The mechanism step, checked against wells (2026-11-18):** the claim runs
  wet winter → higher water table through summer → more reaching the creek.
  For the first step, July–October well readings across Pacifica (17 summers,
  2002–2018; the valley alone has one summer with enough visits): summer
  water table against the winter's rain r = +0.46 (p = 0.07); against that
  summer's three-creek dry-weather flow r = +0.58 (p = 0.01). Carry-over
  runs longer than one winter: the water table stood 1.0 ft low in summer
  2016 after a normal winter that followed four below-normal ones, and 0.8 ft high in
  summer 2018 after a dry winter that followed the very wet 2017 — the same
  summer the creek tested high. One year, so a lead: it suggests the water
  table, not the single winter, is the thing to group summers by. Check 5.
- **The second step cannot be tested with the wells:** the valley's wells
  were read while the beach mostly passed and stopped as creek testing
  began. County beach, 51 well visits with rain-free samples nearby,
  2002–2016: rank correlation −0.02 (+0.16 with the seasonal cycle removed;
  neither distinguishable from none). Surfrider creek mouth: 8 overlapping
  visits. County creek: 2. Check 6.
- **Limitations:** eleven summers; the creek's level also stepped up in 2022
  for reasons this grouping does not separate (the two cleanest summers,
  2020–21, are both dry-winter summers and both before the step); no
  groundwater has been measured in the valley since 2016.
- **To improve:** summer 2027 is the dated test (the page states it before
  the winter ends). Grouping summers by the three-creek dry-weather flow
  instead of the winter's percent of normal would use a measured quantity.
