# Findings v8 — analyte fingerprints; grounded indices; model v1 (2026-08-14)

## 1. Bacteria types differentiate, and the fingerprints converge

The record carries more analytes than we'd used: county creek has Total
Coliform (n=526) beside E. coli (n=524); the beach has E. coli (n=1,216)
beside enterococcus (n=1,260); the Coalition measures both EC and ENT at all
four creek sites (339 paired site-days).

**EC/ENT ratio falls monotonically downstream** (geo-mean, values floored
at 5): LMMS 0.84 → ADMS 0.79 → PRLT 0.70 → SPCM 0.64. E. coli dies faster
than enterococcus, so aging water drifts ENT-ward — consistent with load
entering upstream/mid-valley and aging in transit.

**Dry weather is EC-rich; storms are ENT-rich**: ratio 1.02 in stable
weather (<2mm/14d) vs 0.62 wet (>10mm/14d). Fresh sewage skews EC;
soil/sediment/bird material skews ENT and persists longer. The chronic
dry-weather signal carrying a *fresh* signature while the storm signal
carries an *aged/washed-in* one is a third independent line converging with
the DNA source-tracking — from data already in hand. (Supporting, not
proof: ratio-based source inference is indicative only; DNA markers remain
the arbiter.)

Beach EC and ENT are tightly coupled (r=0.85 log-log, n=1,208; ratio ~1.2
wet or dry). Total coliform adds little: E. coli is ~6% of TC regardless of
condition (r=0.46) — TC is mostly environmental organisms.

## 2. The rain-derived indices are now gauge-checked

Analog criteria (a gauge is an *analog* only if it matches San Pedro Creek
on the things that govern hydrology): drains west off the Santa Cruz
Mountains / coastal ranges to the open coast or Monterey Bay, unregulated,
inside the marine-layer climate. By these criteria:

- **Core analogs (5):** San Gregorio, Pescadero, Soquel, San Lorenzo —
  and Pilarcitos, flagged (partly regulated upstream, but coastal-side and
  Montara-adjacent).
- **Contrast gauges (3), reported but not part of the claim:** San
  Francisquito (bay side), Corralitos (interior Pajaro tributary),
  Lagunitas (Marin, drains to Tomales Bay, dam-regulated).

Results on the **core analog panel**:

- `flow_idx` (quick store, storm input split day 0/1): **r = 0.69–0.73
  log–log daily across all five** (San Gregorio 0.71 — mid-pack, not an
  outlier).
- `ground_idx` (slow store charged by quick-store drainage) vs dry-season
  baseflow (= groundwater discharge): **r = 0.65–0.74 across all five**.

The contrasts behave as contrasts should — instructively. Lagunitas posts
the *highest* storm-flow correlation (0.79: winter storms synchronize the
whole region regardless of geography) but collapses on the baseflow test
(0.51: summer releases are managed, not natural recession). That split is
the demonstration that the baseflow test, not the storm test, is the
discriminating one — and that panel membership must be argued from
geography, exactly the scrutiny applied here.

Formulas in `pipeline/features.py`. No water-temperature proxy exists
anywhere in the region (San Gregorio's sensor ended 1979); air temperature
remains the warmth proxy.

## 3. Model v1: honest walk-forward results

Ridge regression on log₁₀ creek E. coli, 13 vetted features, expanding-window
validation — **every score below is on years the model never saw**
(2019–2026, n=367 out-of-sample). `pipeline/model.py`, saved spec
`models/creek_v1.json`.

| metric (pooled out-of-sample) | value |
|---|---|
| AUC, exceedance | **0.64** |
| AUC, folk rain rule | 0.57 |
| AUC, persistence only (last reading) | 0.65 |
| R², log-concentration | −0.01 |
| At the rain rule's flag rate | model catches 53% of bad days killing 32% of good; rule catches 49% killing 35% |

Read plainly:

- **The noise ceiling is the story.** Residual σ = 0.49 log₁₀ against a
  measured cross-lab grab-noise floor of ~0.35–0.4 (v4: two labs, same
  water, 80% label agreement). Most unexplained variance in a *single grab*
  is unexplainable by any model. Single-sample R² near zero out-of-sample is
  the expected consequence, not a modeling failure; conditional averages
  (the v2–v7 findings) remain solid because they aggregate over the noise.
- **Regime shifts dominate years.** 2022 — the level-jump year — breaks an
  expanding-window model (R² −1.2) exactly as the v7 instability finding
  predicts. A trailing 4-reading baseline (v1.1) recovers some of it; the
  chronic level itself remains the unpredicted, unpredictable-by-weather
  component. That is an argument *for* the source hunt: weather explains
  deviations; the level is the pollution.
- **Persistence ties the model on sample-day scoring** because the county's
  own weekly reading already carries the regime state. The model's distinct
  value is what persistence cannot do: look **forward** (an incoming storm
  is visible to the model via rain forecasts, invisible to persistence),
  grade the **between-sample days**, and **attribute** each prediction to
  named drivers (the app's "why" layer — demo in model.py output).
- Coefficient signs all match the findings that motivated them (flow +,
  warmth +, hour −, baseline +), which is what defensible looks like.

## 4. The reframe: borderline by default; forecast the departures

The product frame that matches the statistics (and resets expectations
honestly): **Linda Mar's resting state is borderline** — the stable-weather
creek geometric mean *equals* the standard, so "pollution is likely present"
is the default message, not a prediction. Safe-vs-unsafe on an ordinary day
is a coin the measurement itself can't call (two labs disagree 20% of the
time). The forecast's job is **flagging departures** — the days that are a
different animal — where the high-signal drivers (storm shadow, event size,
tide, baseline) actually operate.

Out-of-sample tier calibration supports this:

**Creek** (predicted tier → actual): cleaner 198 geo-mean / 11% big-deal
(>1000) → typical 322 / 13% → elevated 518 / 24% → high 1,843 / 50%.
Creek big-deal AUC is only 0.61 because many creek extremes are *dry-day
source pulses* — invisible to weather by definition. That is a
source-evidence fact, and a reason the creek product is a monitor, not a
forecast.

**Beach (LM5) — the user-facing product** (`pipeline/model_beach.py`,
`models/beach_v1.json`; adds creek state + tide at sampling moment):

| OOS metric | value |
|---|---|
| AUC exceedance (>104) | 0.63 (rain rule 0.59) |
| AUC serious days (>3× std, n=79) | **0.69** |
| AUC big-deal days (>10× std, n=28) | **0.67** (single years up to 0.92) |

| predicted tier (OOS) | n | actual geo-mean | >104 | >10× std |
|---|---|---|---|---|
| cleaner (<52) | 49 | 54 | 35% | 2% |
| typical (52–208) | 228 | 96 | 48% | 6% |
| elevated (208–1,040) | 95 | 191 | 66% | **15%** |

Monotone, honest, and a 7× big-deal separation between tiers. Beach
coefficients independently re-derive the physics: est. creek flow dominant
(+0.26), ebb tide + (the v2 transport finding), beach baseline +, trend +.

**Product language that follows:** never "safe/unsafe." Default: "Typical
for Linda Mar — borderline; pollution likely present." Departures: "Elevated
— storm influence, real added risk" / "High — stay out." Rare: "Cleaner
window than usual." Each with its drivers named (attribution) and its
calibration stated.

### The good-news side, measured (LM5 modern era, base 48% / geo-mean 92)

| stacked condition | n | exceed | geo-mean | rel. risk | >10× std |
|---|---|---|---|---|---|
| dry ≥7d | 354 | 44% | 68 | 0.91× | 3% |
| dry ≥7d + creek 3-wk avg passing | 142 | 35% | 58 | 0.74× | 2% |
| + flood tide | 76 | 33% | 58 | 0.69× | 3% |
| + cool season (all four) | 42 | **29%** | 57 | **0.60×** | 2% |

- The best defensible "quieter window" is ~**0.6× the usual risk with
  big-spike risk ~2%** — meaningful, honestly communicable ("about half the
  typical risk; extreme days near zero"), never "safe."
- **Tide height does nothing** (high tide alone: 47%, geo-mean *higher* at
  104) — the "high tide dilutes" intuition is not supported. **Tide
  direction matters modestly** (flood 0.86×): it's the water's movement,
  not its level.
- The strongest single good-news lever is the **creek being quiet**
  (3-week average passing → 0.74×) — the vector state, not the weather.
- The unbeatable good-news lever remains **location**: north of the pump
  station runs 2–8% while the creek mouth runs 48–78%. "Walk north" beats
  every weather condition by 4–10×.

## What v2 should target (in order)

1. **Aggregated targets**: predict the 2–4-week risk level rather than
   single grabs — averaging beats grab noise; this matches what the public
   actually needs ("how is the creek running lately") and should show much
   higher skill.
2. **The beach product**: same pipeline on LM5 (rain signal is stronger
   ocean-side; the surfer-facing forecast lives there), with creek state as
   an input.
3. **Forward mode**: swap observed rain for NWS QPF and verify true
   forecasts live through the winter — the deployment test.
