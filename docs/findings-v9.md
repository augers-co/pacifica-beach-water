# Findings v9 — the beach record up close: tide at the sampling minute; the clean readings (2026-08-15)

The beach model carries an ebb-tide coefficient; this note shows the
correlation directly, using the recorded collection time of every sample
rather than leaving the claim inside a ridge fit. `pipeline/tide_beach.py`.

## Data

- **Samples:** CEDEN LM5 (Linda Mar Beach #5) enterococcus, 2001–2026.
  1,255 sample-days; 1,106 carry a real `CollectionTime` (149 rows hold the
  `00:00:00` missing-time sentinel and are dropped). Times cluster 8–11 AM,
  median 9:00. Same-date replicates collapse to the max (register §7).
- **Tide:** NOAA CO-OPS harmonic predictions, hourly, 2000–2026,
  **Princeton/Half Moon Bay station 9414131** — an open-coast reference
  station 14 miles south of Linda Mar. (The first publication of this note
  used the SF Golden Gate gauge 9414290; the open coast turns 30–65 minutes
  before that gauge — register §6 — and the switch materially changed the
  result. See the correction below.) Height and rate at the sampling minute
  are interpolated; each sample gets a **phase** = signed hours from the
  nearest high water (parabola-refined maxima): negative = before high
  (rising), positive = after (falling).

The sampling program never chose its times by tide — samplers arrive on a
morning schedule while the tide drifts ~50 minutes later each day — so tide
phase at the sampling minute is close to naturally randomized
(corr with hour-of-day = +0.01). One imbalance does exist and matters: ebb
samples land disproportionately in winter (50% vs 37%) and on rainier weeks
(prev-7d 11.7 vs 9.1 mm), so every claim below is checked in dry weather.

## CORRECTION (same day): the effect is high-vs-low phase, not ebb-vs-flood

The first publication of this note, timed on the SF Golden Gate gauge,
reported "ebb tide raises the odds 1.37× (p=0.001)." Re-timing every sample
on the open-coast clock (Princeton 9414131, which Pacifica tracks to within
minutes) **collapses that binary**: ebb/flood becomes 1.12 [0.93–1.34],
p=0.26, and the controlled OLS ebb coefficient falls to +0.05. The SF gauge
runs ~an hour behind the coast, so the genuinely clean hours *around* local
high water were being wholesale mislabeled "flood," manufacturing an
ebb-vs-flood split. Direction at the sampling moment does not matter.

What survives — and is the correct claim — is the **phase structure**.
Exceedance by hours-from-local-high-water (`docs/charts/tide_phase_lm5.png`):

| phase | −5.2h | −3.1h | −1.0h | +1.0h | +3.1h | +5.2h |
|---|---|---|---|---|---|---|
| all days | 33% | 30% | **23%** | 28% | 34% | 34% |
| dry ≥3d | 30% | 25% | **17%** | 27% | 25% | 30% |

The clean window straddles high water; risk is highest in the hours around
low water, approaching from either direction. Windowed contrast (within
~2 h of high vs within ~2 h of low):

| subset | around high | around low | RR low/high [95% CI] | perm p |
|---|---|---|---|---|
| all days (n=419/332) | 25.3% | 32.2% | **1.27 [1.01–1.60]** | 0.040 |
| dry ≥3 days (n=329/259) | 21.9% | 27.8% | 1.27 [0.95–1.69] | 0.103 |

A real but **modest** effect — about 1.3× between the best and worst
windows, borderline significance once rain days are excluded — not the
strong directional result first reported. Mechanistically it now reads as
excursion, not direction: at low water the creek's plume has been drawn
farthest across the beach face and the station stands closest to it; at
high water the ocean holds it pinned at the mouth. Consistent with that,
same-morning tide *height* terciles stay flat (next section) — what varies
is the phase geometry, not the water level.

**Era restriction (same day).** The Ledger's explorer defaults this
comparison to 2014→ — when the beach's decline began (see the
clean-readings analysis below) — so the levels shown reflect today's beach
rather than an average diluted by the clean decade. The contrast by era:
full record RR 1.27 [1.01–1.60] p=0.04 (n=419/332); **2014→ RR 1.24,
p=0.06** (n=226/193, window geo-means 70 vs 86 — every window well above
the 35 geometric-mean standard); 2020→ RR 1.07, p=0.69 (n=126/99) — on the
recent, saturated beach (typical results ≈100, about half of single tests
failing at every phase) the tide's modest push is undetectable in a small
sample. The practical statement for today's beach is therefore: **no tide
window is reliably clean**; the phase pattern is a full-record finding.

The v8 beach-model "ebb+" coefficient and the "flood 0.86×" good-news line
were computed on SF timing and carry the same alias; their predictive value
was validated out-of-sample and stands, but their mechanistic label should
be read as "tide phase," and model v2 should refit tide features on
Princeton timing with a phase term.

## The creek itself shows no tide pattern

Same phase windows on the county creek station's timed samples (n=523):
**49.7% over the standard around high water vs 44.6% around low** (perm
p=0.35; the middle bin is highest — noise, not trend). This matches direct
observation by residents: the creek visibly flows out; the tide does not
push upstream past the beach. The tide does not change what the creek
carries — it changes where the plume sits on the beach face. The pairing
sharpens the source argument: the source runs on its own schedule, and the
ocean only moves the result around.

## Height stays null

Tide-height terciles (Princeton datum): 29.5% / 30.7% / 27.9% exceedance.
Confirms v8: the folk intuition "high tide dilutes" fails. Height terciles
mix spring and neap cycles, so this is not in tension with the phase
result — what matters is *where the water is in its cycle*, not its
absolute level.

## Limitations

- Princeton is 14 miles south; the coastal tide propagates northward, so
  Pacifica turns an estimated ~5–10 minutes after Princeton — genuinely
  small against a 12.4 h cycle. (The lesson of the correction above: an
  hour-scale clock error does not merely blur — it can *relabel*. The
  residual minutes here cannot.)
- Predictions, not observations: storm surge and wave setup are absent.
  They affect height (already null), not the timing of the turn.
- Single-grab noise (±half-log, register §9) still floors any single
  reading; n ≈ 1,100 is what makes these averages solid.
- Correlation shown against the *predicted* astronomical cycle — no
  plausible reverse causation exists, and the confounders that could mimic
  it (rain, season, hour) are controlled or balanced above.

## What follows

- The beach product's tide term is demonstrated as a **phase** effect with
  a dose-response curve — and the correction is itself a result: the
  measurement clock matters at the hour scale, and the analysis now runs on
  the right one.
- Practical reading (beach-facing, consistent with the borderline-by-default
  frame): on equal weather, the couple of hours around high water run
  ~1.3× cleaner than the hours around low water. A modest refinement that
  never overrides the rain rules.
- The phase curve remains an argument that **the creek is the vector**: the
  beach reading responds to where the tide has moved creek water, in dry
  weather, on the astronomical clock — just via excursion, not direction.

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

## What changed in 2014? A documented candidate

The record's break has a dated, in-creek event that exactly spans it:
**Caltrans replaced the Highway 1 bridge over San Pedro Creek and widened
the creek channel** (approved July 2013; in-creek construction began June
2014, detour through ~October 2015) at the crossing just above the mouth.
The county's creek station began sampling September 2015 — immediately
after — so no creek data exists from before the bridge work.

Two distinct hypotheses fit, and they are not exclusive:

1. **Conveyance:** a widened channel at the crossing delivers the creek's
   existing load to the surf-zone station more efficiently — the beach's
   "new normal" without any change in the source. Consistent with the
   coalition's localization of the dry-weather load *upstream* at
   ADMS→PRLT, far above the bridge.
2. **Source:** construction-era damage or disturbance to buried
   infrastructure near the crossing, or a coincidental change elsewhere
   (sewer aging does not follow the calendar). Whether utility lines were
   relocated during the bridge project is a city-records question worth
   asking.

Neither is asserted; both are testable, and DNA source-tracking remains
the arbiter of *what* the material is. For context, the mouth itself was
rebuilt much earlier (managed retreat, constructed 2001–2003 — including
the Anza pump station renovation), predating every shift in this record.

**Current-work note:** the RCD of San Mateo County is replacing the Adobe
Drive culvert with a free-span bridge (CEQA NOE Feb 2026; in-creek work in
the 2026 dry season) — in the ADMS reach, the exact stretch the source
hunt targets. 2026 samples land during and after this construction;
interpret the year's creek data with that in mind.

## Advocacy read

Clean is not a hypothetical for this beach — it is the **demonstrated
former normal**: 43% of mornings, with months-long clean runs, inside the
same lab record that now fails half the time. Whatever changed around 2014
took that away, and nothing in the weather record explains it (v7). The
target of the source hunt is, concretely, the restoration of a state this
beach held for a decade of measurement.
