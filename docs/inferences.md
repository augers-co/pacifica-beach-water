# Register of inferences and assumptions

Every derived quantity this project displays or models, with its math, what it
was fitted on, its validation, and its known weaknesses — so anyone with
better knowledge can interrogate or refit it. Code pointers are to this repo.
If you can improve one of these, the maintainers want to hear it.

## 1. Rainfall (the root input)

- **What:** daily & hourly precipitation at the watershed (37.585, −122.47).
- **Source:** ERA5 reanalysis via Open-Meteo — a weather-model estimate, not a
  gauge. No rain gauge exists in the valley.
- **Limitations:** single ~9 km grid cell; coastal orographic detail smoothed;
  we showed the same product's *radiation* misses the marine layer, so precip
  totals deserve similar skepticism at event scale.
- **To improve:** any local gauge record (even informal) could bias-correct
  it; NOAA Stage IV/MRMS radar blend is the upgrade path. `pipeline/fetch.py`.

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
- **Limitations:** stands in for a water table no one measures — the valley's
  USGS wells have no usable series and DWR has no coastal San Mateo stations.
  The 0.97 retention is assumed, not fitted to local recession.
- **To improve:** any shallow piezometer record in the valley; or refit
  retention to analog-creek recession curves. `pipeline/features.py`.

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
- **Fitted on:** San Gregorio Creek's daily water-temperature record —
  1965–1979, 3,935 paired days against ERA5 air at that site. r = 0.85,
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
  Cross-creek transfer (San Gregorio → San Pedro) is assumed.
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

- **Source:** NOAA harmonic predictions, San Francisco station 9414290.
  Deterministic (exact retroactively, forecastable ahead).
- **Assumption:** SF phase leads Pacifica by minutes-to-tens-of-minutes —
  fine for stage/height classification, not for minute-level timing.

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
