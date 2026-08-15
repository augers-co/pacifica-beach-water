# Findings v9 — the beach record up close: tide at the sampling minute; the clean readings (2026-08-15)

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

---

# The clean readings

The other end of the distribution: mornings when the lab finds **no
detectable enterococcus at all** (`<10`, qualifier `<`). 368 of 1,255
sample-days — 29% of the whole LM5 record. (A date counts as clean only if
every replicate that morning was a non-detect.)

**The measurement is stable, so the trend is real.** One method across the
entire record (Enterolert, 2000–2026), one reporting floor (10 MPN/100 mL),
and the `<` vs `=` coding at the floor appears in both eras at similar
rates — the collapse below is not a lab artifact. Independently, the
over-104 trend cannot be a detection-floor artifact at all.

## The beach used to be clean half the time

| era | clean (ND) mornings | over-104 mornings | n |
|---|---|---|---|
| 2001–2013 | **43.3%** | 9.4% | 640 |
| 2014–2026 | **14.8%** | 44.9% | 615 |

The two eras have nearly identical sampling coverage. Before 2014 the modal
morning at the creek mouth was *zero detectable indicator*; since 2014 the
clean morning is one in seven and the failing morning is one in two. This is
the v1 "deterioration began ~2014" finding restated from the clean end,
where it is starkest.

**Clean streaks have vanished.** The record holds 18 runs of ≥4 consecutive
clean weeks — including a 14-week run (Mar–Jun 2008) when the beach tested
clean for over three months straight. The most recent such run ended
**August 15, 2016**. In the decade since, the beach has never once strung
together four clean weeks.

## When clean mornings happen

- **Dry weather:** 33% of mornings ≥7 days after rain are clean vs 18%
  within 3 days of rain (plateaus past ~3 dry days — the 2.2-day risk
  half-life seen from the other side).
- **Season:** Apr–Jun best (36%), Jul–Oct 31%, storm season worst (24%) —
  the late-summer warm-water penalty and winter storm penalty both visible.
- **Tide: indifferent** (flood 30.3% vs ebb 30.1% clean). Contrast with the
  exceedance analysis above: tide phase moves the **top** of the
  distribution (whether a plume-influenced sample crosses 104), not the
  **bottom** (whether the plume is present at all). Presence is set by the
  source and the weather; the tide just steers what's there.
- **The creek, again:** on beach-clean weeks the creek's nearest sample
  geo-means 165 (35% over its standard); on beach-failing weeks, 566 (63%
  over). Even the cleanest beach mornings sit over a creek that rarely goes
  quiet — the beach goes clean when the creek is *quieter* and the weather
  gives the plume no help.

## Method note

Register §7 treats `<10` at face value 10, so geo-means on clean days are
biased *high* by up to the floor — conservative in the beach's favor is the
wrong way to read that: it means every geo-mean cited for LM5 slightly
**overstates** how much bacteria was present. Exceedance statistics are
unaffected (the floor sits far below 104).

## Advocacy read

Clean is not a hypothetical for this beach — it is the **demonstrated
former normal**: 43% of mornings, with months-long clean runs, inside the
same lab record that now fails half the time. Whatever changed around 2014
took that away, and nothing in the weather record explains it (v7). The
target of the source hunt is, concretely, the restoration of a state this
beach held for a decade of measurement.
