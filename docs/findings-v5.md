# Findings v5 — the sewer spill record; the dilution test fails (2026-08-14)

Sources: CIWQS statewide spill flat files filtered to Pacifica (WDID 2SSO10100),
donor stream gauges (San Gregorio 11162500, Pilarcitos 11162630), county creek
E. coli 2015–2026. See `docs/data-sources.md`.

## A. Pacifica's reported spill record (2007–present)

**160 reported spills; 37 reached surface water; 4.16M gallons total spilled —
71% of it in a single event: 2,938,986 gallons from the Linda Mar Lift
Station on 2021-10-25** (the October 2021 atmospheric river). The lift
station is at the beach — the same pump station the county's LM7 station
monitors and the Coalition's "rare discharges" note refers to.

Recurring storm-coincident failure locations (>100 gal to surface water):

| location | events | largest |
|---|---|---|
| 500 block Linda Mar Blvd | ≥4 (2014, 2016, 2016, 2017×2) | 203,700 gal |
| Anza Dr @ Arguello Blvd | ≥2 (2014, 2016) | 124,500 gal |
| Linda Mar Lift Station | 2021 | 2,938,986 gal |

All large spills are storm-coincident (Dec/Jan/Oct dates) — classic
infiltration-and-inflow overload at fixed weak points, in the same lower-valley
reach where findings v4 located the stable-weather load entry (ADMS→PRLT).

**What the spill record does NOT explain:** reported spills collapsed after
2011 (38/yr in 2008 → ~3–5/yr since 2015) while the creek and beach
*deteriorated* from ~2014. Creek samples within 10 days after a
surface-reaching spill run only modestly higher (geo-mean 448 vs 356).
The chronic dry-weather signal is not reported spills — consistent with
continuous, unreported exfiltration or other diffuse input. LM7's 2026-01-19
spike has no matching reported spill (only 3 reports since mid-2023: 60 gal
2023-12-18, 170 gal 2024-12-20, 1,750 gal 2026-07-08).

**Monitoring-gap finding:** no county sample exists for 2021-10-25 — the
largest spill in the record fell between weekly Mondays (10-18 → 11-01), so
the biggest discharge ever produced zero direct water-quality measurements.
Weekly grab sampling is structurally blind to acute events.

## B. The dilution hypothesis fails its test

Prediction (findings v3): if stable-weather concentration = constant load ÷
flow, then log(C) vs log(Q) should slope ≈ −1.

Measured on 249 stable-weather creek samples vs donor-gauge daily flow:

| flow proxy | r(logC, logQ) | slope |
|---|---|---|
| San Gregorio (unregulated donor) | **+0.15** | +0.15 |
| Pilarcitos | +0.16 | +0.29 |
| synthetic rain-recession store | +0.01 | +0.01 |

No negative relationship at all — slightly *positive*. Seasonally, flow falls
June→September while concentration rises (216 → 466), but the pointwise
scaling dilution requires is absent. **Falling flow accompanies the summer
rise but does not cause it in a simple dilution sense; the load itself must
vary.**

Revised leading hypotheses for the late-summer stable-weather peak:

1. **Warm-water survival/regrowth in channel sediments** (Aug–Sep = warmest
   water; FIB persistence and regrowth in sediment is well documented).
2. **Reduced solar die-off** during the July–September fog season.
3. **Season-varying inputs** (summer creek/beach activity, irrigation-driven
   dry-weather drool through the storm drains that the Coalition's map shows
   emptying into the creek).

These are discriminable: (1) predicts correlation with water/air temperature,
(2) with solar radiation (both joinable from existing free sources), (3) has
time-of-day and day-of-week fingerprints (BWTF Thursday series + any shared
non-Monday data).

## Standing picture after v5

- Storm regime: distributed storm-sewer wash-in + occasional large I&I
  spills at known weak points (public record).
- Stable weather: chronic load entering in the ADMS→PRLT reach, *not*
  explained by reported spills, *not* modulated by dilution — late-summer
  peaking, morning-elevated. Temperature/solar joins are the next
  discriminating tests.
