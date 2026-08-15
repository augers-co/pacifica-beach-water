# Findings v9 — tide at the sampling minute (2026-08-15)

The beach model carries an ebb-tide coefficient; this note shows the
correlation directly, using the recorded collection time of every sample
rather than leaving the claim inside a ridge fit. `pipeline/tide_beach.py`.

## Data

- **Samples:** CEDEN LM5 (Linda Mar Beach #5) enterococcus, 2001–2026.
  1,255 sample-days; 1,106 carry a real `CollectionTime` (149 rows hold the
  `00:00:00` missing-time sentinel and are dropped). Times cluster 8–11 AM,
  median 9:00. Same-date replicates collapse to the max (register §7).
- **Tide:** NOAA CO-OPS harmonic predictions, SF station 9414290, hourly,
  extended back to 2000 (deterministic, so historical values are exact;
  `tide_hourly` now spans 2000–2026). Height and rate at the sampling minute
  are interpolated; each sample gets a **phase** = signed hours from the
  nearest high water (parabola-refined maxima): negative = flood (rising),
  positive = ebb (falling).

The sampling program never chose its times by tide — samplers arrive on a
morning schedule while the tide drifts ~50 minutes later each day — so tide
phase at the sampling minute is close to naturally randomized
(corr with hour-of-day = +0.01). One imbalance does exist and matters: ebb
samples land disproportionately in winter (50% vs 37%) and on rainier weeks
(prev-7d 11.7 vs 9.1 mm), so every claim below is checked in dry weather.

## Result: ebb tide raises the odds ~1.3×, and it is not rain in disguise

| subset | n (ebb/flood) | ebb exceed | flood exceed | RR [95% CI] | perm p |
|---|---|---|---|---|---|
| all days | 478/628 | 34.7% | 25.3% | **1.37 [1.15–1.65]** | 0.001 |
| dry ≥3 days | 347/505 | 28.8% | 21.6% | **1.34 [1.06–1.70]** | 0.020 |
| dry ≥7 days | 279/397 | 29.7% | 23.2% | 1.28 [0.99–1.64] | 0.062 |

Geo-means move the same way (all days: 52 vs 37). OLS on log-concentration
gives the same answer from the other direction: the ebb coefficient is
+0.147 naive and **+0.114 with rain + season controls** (≈ ×1.30
concentration). The dry-weather replication is the load-bearing row: with
storm influence excluded entirely, the effect stands at the same size; the
≥7-day subset thins to p=0.06 as n drops, at an unchanged effect size —
what a modest real effect looks like as power shrinks, not a disappearing one.

## The phase curve is the mechanism's signature

Exceedance by hours-from-high-water (`docs/charts/tide_phase_lm5.png`):

| phase | −5.2h | −3.1h | −1.0h | +1.0h | +3.1h | +5.2h |
|---|---|---|---|---|---|---|
| all days | 30% | 26% | **21%** | 36% | 33% | **39%** |
| dry ≥3d | 24% | 22% | **19%** | 31% | 26% | **33%** |

Risk falls through the flood to its minimum in the last hour before high
water, jumps immediately after the turn, and is highest late in the ebb —
near low water. Both series show the same shape. That is what creek-plume
transport predicts: hours of incoming ocean water push the plume back
against the creek mouth; hours of ebb draw it out across the beach face.
The station sits in the surf zone at the mouth — it samples whatever the
tide has been doing to the plume all morning.

## Height stays null

Tide-height terciles: 29% / 28% / 31% exceedance (geo-means 42/39/48).
Confirms v8: the folk intuition "high tide dilutes" fails. What matters is
the water's **direction**, not its level — consistent with a plume being
moved, not a harbor being filled.

## Limitations

- SF harmonic phase leads Pacifica by minutes-to-tens-of-minutes
  (register §6) — small against a 12.4 h cycle, and it can only blur the
  phase curve, not create it.
- Predictions, not observations: storm surge and wave setup are absent.
  They affect height (already null), not the timing of the turn.
- Single-grab noise (±half-log, register §9) still floors any single
  reading; n ≈ 1,100 is what makes these averages solid.
- Correlation shown against the *predicted* astronomical cycle — no
  plausible reverse causation exists, and the confounders that could mimic
  it (rain, season, hour) are controlled or balanced above.

## What follows

- The beach product's tide term is now independently demonstrated, with a
  dose-response curve, not just a fitted coefficient.
- Practical reading (beach-facing, consistent with the borderline-by-default
  frame): on equal weather, the hours around an incoming high tide run
  ~1.3× cleaner than the ebb; the late ebb near low water is the worst
  window. This never overrides the rain rules — it refines them.
- The curve is another argument that **the creek is the vector**: the beach
  reading responds to the machinery that moves creek water, in dry weather,
  on the astronomical clock.
