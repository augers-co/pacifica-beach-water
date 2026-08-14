# Findings v3 — the structure of stable-weather variance (2026-08-14)

Question: what drives creek variance when weather is stable, and how would we
identify the source? Subset: creek E. coli with <2mm rain in the prior 14 days
(n=249, "stable weather"), full record 2015–2026 (n=523). Collection times from
CEDEN; tide from CO-OPS predictions.

## The structural finding: pinned at the standard

Stable-weather creek concentrations: **geometric mean 320 MPN/100mL — equal to
the health standard (320)**. Median 336, log₁₀ sd 0.51.

| where values sit | share |
|---|---|
| within ×2 of the standard (160–640) | 53% |
| within ×3.16 (101–1,012) | 74% |
| genuinely low (<100) | 15% |
| genuinely high (>1,000) | 10% |

The 50% stable-weather exceedance rate is therefore substantially a
**threshold artifact**: a chronic near-standard baseline plus ordinary
half-log noise flips the pass/fail label. The informative questions are
(a) what pins the *level* at the standard, and (b) what wiggles it ±half-log.
Modeling implication: model **log-concentration, not exceedance** from here on.

## The wiggles, decomposed

**Diurnal — morning is dirtier (×2 by late morning).** Stable-weather
geo-means by collection hour: 07–08h **409** (60% exceed, n=50) → 09–10h 324
(50%, n=163) → 11h+ **216** (42%, n=36). Two mechanisms fit: the morning
sanitary-usage pulse reaching the creek, and/or cumulative solar die-off
through the day. Either way, *variation in collection hour alone flips labels*
near a threshold-straddling baseline — part of the week-to-week "variance" is
sampling-time noise, not water change.

**Multi-week persistence, not white noise.** Same-state agreement between
samples k weeks apart: 64% at 1–2 wk, ~60–63% out to 4 wk (null 50%).
Fail-runs average 2.6 weeks; the longest ran **16 consecutive weeks** (longest
pass-run: 22). Some state variable moves on month scales.

**Late-summer peak in stable weather.** Geo-mean June **216** (32% exceed) →
August **421** (69%) → September **466** (61%). With rain controlled, this
gradient tracks declining summer baseflow — concentration = load ÷ flow —
the same dilution mechanism that fits the 2014 drought-era inflection. It also
means the worst stable-weather water coincides with peak recreation season.

**Tide at the creek station: near-null.** Mild dilution at high tide (geo-mean
299 vs 333 at low; 47% vs 54%); stage effects negligible. Good news: creek
readings are not meaningfully tide-corrupted, so they can be treated as source
signal.

## Ranked hypotheses for the stable-weather signal

1. **Chronic human load + slowly-varying dilution (baseflow).** Explains the
   pinned level, the June→September gradient, the drought-era rise, and
   month-scale persistence. Master variable: creek flow — unmeasured.
2. **Diurnal input or decay** (usage pulse vs solar): explains morning highs.
   Discriminable: solar predicts steeper morning decline on clear days
   (joinable — hourly radiation data); usage predicts weekday/weekend
   structure (needs non-Monday sampling, e.g. BWTF data if shared).
3. **Discrete events** (SSOs, blockages): the >1,000 tail (10%) and possibly
   the long fail-episodes. Testable against CIWQS public SSO records.

## How to discriminate, within our lane (public data only)

- **Flow proxy via donor catchment**: scale a nearby gauged coastal creek
  (e.g. Pilarcitos) + rain-recession modeling to estimate San Pedro Creek
  baseflow history; test the dilution hypothesis directly against 11 years of
  concentrations. Highest-value next analysis.
- **Solar join**: hourly shortwave radiation vs the morning gradient,
  clear vs overcast days.
- **CIWQS SSO records join**: do reported Pacifica sewer incidents co-occur
  with spikes/episodes?
- **Log-concentration modeling** replaces exceedance modeling.
- **BWTF 4-site series (if shared)**: upstream–downstream differencing
  isolates reach-level loading — the spatial fingerprint.

## Revision of an earlier claim

Findings v2 read the dry-day 50% rate as "maximum-variance coin flip →
intermittent pulsed source." The fuller picture: a **chronic source holding
the creek at the standard**, modulated by dilution, time-of-day, and
occasional discrete events. Less flicker, more pinned-plus-wobble.
