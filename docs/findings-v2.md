# Findings v2 — benchmarking the folk rule; new covariates (2026-08-14)

Question: can a forecast beat "stay out if it's raining or recently rained"?
Frame: LM5 enterococcus, modern era (2015+, n≈528–540), where the beach fails
~48% of samples overall. Code: `pipeline/fetch_covariates.py` + analysis
snippets; tide from NOAA CO-OPS harmonic predictions (deterministic, so
retroactive values are exact), hourly rain from ERA5.

## The incumbent, measured

"Any rain in the last 72h → stay out" **catches 51% of bad days and wrongly
kills 31% of good days.** A 7-day version catches 68% but kills 55% of good
days. The rule is near coin-toss at this beach because dry-weather failures
dominate the modern era.

## Working correlates (measured here)

| # | Feature | Evidence | Deployable from |
|---|---|---|---|
| 1 | **Rain recency** | Clearance curve: 81% on rain days → 79% (+1d) → 68% (+2d) → 55% (+3d) → 39% (+4–7d). The 72-hour folk threshold is wrong on both ends: day 3 is still risky, and the day-4+ floor is ~39%, not safe. | ERA5 / any gauge, free |
| 2 | **Rain amount ≈ intensity** | Among wet samples, AUC 0.69 for both 72h total and 72h max-hourly — statistically interchangeable in this climate (winter frontal storms). Graded: drizzle 53%, moderate 79%, intense 81%. | same |
| 3 | **Lagged creek state** | Last available creek reading (county weekly, 24h lab lag) splits *dry-day* beach risk 34% vs 49%. Creek is persistent: P(fail \| failed last week)=66% vs 38% — lag doesn't kill the signal because the state is sticky. | county postings, free |
| 4 | **Tide stage (new)** | Ebb 55% vs flood 42% at sample moment (n=194/286); tide *height* is null (48/47/48 across terciles). Effect concentrates on wet days (dry: 40 vs 37). Mechanism: ebb drains creek plume along the beach; flood dilutes. Deterministic → forecastable years ahead. | CO-OPS predictions, free |
| 5 | **Season regime** | Annual exceedance sd jumped 3pp (2000–13) → 18pp (2014+); model needs a trend/era term. | derived |
| 6 | **First flush (provisional)** | Early-season moderate storms 90% (n=10) vs 69% on soaked ground. Small n. | derived |

## What's still unexplained

Dry-day failures run ~38–41% in the modern era and are flat across tide bands —
the only current handle is lagged creek state (#3). Consistent with a pulsed
dry-weather source (which is what the Coalition's DNA testing addresses; the
near-50% creek rate on dry days is maximum Bernoulli variance — coin-flip —
which itself indicates intermittent release, not steady state).

## Where this lands

Single features top out at AUC ~0.63–0.69. Stacked (graded rain + creek lag +
tide stage + season), comparable published beach nowcast models typically reach
AUC 0.75–0.85. The product difference vs the folk rule: graded current
probabilities instead of a binary that misses half the bad days and cries wolf
on a third of the good ones — plus honest "green" windows (day-4+, creek
passing, flood tide) that the rain rule can never issue in winter.

## Nulls & caveats

- Tide **height**: null. BeachWatch per-sample covariate fields (TidalHeight,
  SurfHeight, StormDrainFlow, Turbidity): ~0% filled — dead end.
- Rain intensity is not *independently* informative beyond amount (r too high
  in this climate); use either.
- ERA5 rain, SF tide station (phase leads Pacifica by minutes): both fine for
  classification, both upgradeable.
- Untested public covariates: waves (NDBC 46012 archive), solar/water temp
  (die-off), sample time-of-day.
