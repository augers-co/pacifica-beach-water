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

`flow_idx` (quick store, storm input split day 0/1) tracks San Gregorio
Creek's measured daily flow at **r = 0.71** (log–log, 4,243 days).
`ground_idx` (slow store charged by quick-store drainage — crests days
after storms, dries over months) tracks dry-season donor baseflow — which
physically is groundwater discharge — at **r = 0.74** (n=1,460 rain-free
warm-season days). Formulas in `pipeline/features.py`; the ledger's Methods
carry the same numbers. No water-temperature proxy exists (San Gregorio's
sensor ended 1979); air temperature remains the warmth proxy.

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
