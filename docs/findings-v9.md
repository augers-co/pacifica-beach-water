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
the arbiter of *what* the material is.

**The era × weather split sharpens the question.** Beach behavior by era
and rain state:

| era | dry ≥7d: geo-mean / over / clean | wet <3d: geo-mean / over / clean |
|---|---|---|
| 2000–2013 (pre-bridge) | 16 / **5%** / 48% | 34 / 23% / 25% |
| 2014–15 (construction) | 24 / 15% / 38% | 85 / 36% / 41% |
| 2016–2026 (post) | 75 / **46%** / 14% | 284 / 71% / 4% |

Before 2014 the beach behaved like a place with **only storm-driven
pollution**: bone-dry weeks failed 5% of the time and were completely
clean half the time. Since 2016 it behaves like a place with a
**year-round source**: dry weeks fail 46% of the time. Both regimes
worsened by roughly the same factor (~8× in geo-mean), which fits either
hypothesis — a widened channel conveys in all weathers, and a larger
source loads in all weathers — so the beach record alone cannot separate
them.

**The BWTF creek-mouth record now speaks to this** (Surfrider SMC's public
export, `pipeline/fetch_bwtf.py`, fetched 2026-08-15). Two things it settles
and one it can't:

- **Two independent programs agree the surf was clean before 2014.**
  Surfrider's own beach transects (Linda Mar North/South) read geo-mean 14,
  4% over the standard across 2012–early 2014 (n=112) — matching the county
  station's clean pre-2014 beach exactly. Not one program's artifact.
- **The creek mouth was already heavily contaminated before construction.**
  Surfrider's creek-mouth station (same reach as SPCM) read geo-mean 412,
  **96% over the standard**, in the Dec 2013 – May 2014 window (n=24) — the
  six months *before* the June 2014 bridge work began. In that same window
  the surf 200 m away sat at 14. The contamination was in the creek and not
  yet in the surf zone.
- **What it can't settle:** creek-mouth sampling began Dec 2013 — ~6 months
  pre-construction, winter/spring only — so this is a narrow, wet-season
  window, not a multi-year baseline. "Polluted for years before" is
  plausible but unproven; and post-construction the creek mouth did not
  worsen (geo-mean 211), though season confounds that.

**Net:** the source predates the bridge, and before 2014 the creek's load
was not reaching the surf zone the way it does now — which is exactly the
conveyance picture, and matches the intuition that the creek "was polluted
all along." It is corroboration, not proof: the pre-construction creek
window is thin, and the source clearly also moves on its own (the 2020–21
dip and 2022 jump happened with no channel change). The remaining
tie-breaker is documentary — city/Caltrans records on whether sewer or
utility lines were relocated or disturbed during the bridge project. For context, the mouth itself was
rebuilt much earlier (managed retreat, constructed 2001–2003 — including
the Anza pump station renovation), predating every shift in this record.

**Current-work note:** the RCD of San Mateo County is replacing the Adobe
Drive culvert with a free-span bridge (CEQA NOE Feb 2026; in-creek work in
the 2026 dry season) — in the ADMS reach, the exact stretch the source
hunt targets. 2026 samples land during and after this construction;
interpret the year's creek data with that in mind.

### The fuller construction timeline (verified 2026-08-15)

Beyond the Hwy-1 bridge, several dated creek projects bracket the record.
Each below was checked against a primary source (an LLM-drafted list was the
starting point; unverifiable items were dropped):

- **2000–2003 — flood control + managed retreat.** Army Corps / city
  rebuilt the lower channel to a meander, removed two oceanfront homes, and
  restored the mouth wetlands ([ResilientCA](https://resilientca.org/projects/0d7cdcb8-3035-46f1-9042-b852f8d38bb9/)).
  Predates the record's shifts.
- **2004 — Capistrano Ave bridge fish passage.** A failed fish ladder was
  removed and the mid-reach channel regraded around a 19-ft bed drop
  ([CEQA 2003052028](https://ceqanet.lci.ca.gov/2003052028/3); [SCC](https://scc.ca.gov/webmaster/ftp/pdf/sccbb/2004/0405/0405Board08_San_Pedro_Creek.pdf)).
  Upstream, fish-focused; low beach relevance.
- **2014–2016 — Hwy 1 bridge replaced + channel widened** (above). The one
  spanning the beach's break.
- **2018–2020 — storm runoff diverted from the pump stations to treatment
  wetlands.** This one is directly on point and cuts the other way from the
  bridge hypothesis. Funded by Prop 13, the city diverted the **first flush**
  of storm runoff away from the **Linda Mar and Anza pump stations** — the
  Anza station discharges at the lower third of Linda Mar beach — into
  constructed treatment wetlands, **expressly to reduce the coliform / E.
  coli reaching the beach** ([City of Pacifica](https://www.cityofpacifica.org/departments/public-works/wastewater-treatment/calera-creek-water-recycling/linda-mar-san-pedro-creek-wetlands), Prop 13 funding). *Construction dates not
  independently verified* — the LLM list's "2018–2020" and its CEQA number
  (2012061091, which is actually a Pacific Grove project) did not check out;
  the project's existence and purpose are confirmed by the city, the exact
  build window is not. Prop 13 (a 2000 water bond) hints it may predate 2018.
  **A project built to make the beach cleaner was completed before the recent
  era — and the beach did not recover** (2022–2024 were among the worst years on
  record). Read carefully: it treats *storm* first-flush, so it targets the
  wet-weather pathway, not the chronic *dry-weather* source. Its apparent
  failure to move the beach is therefore evidence *for* the project's central
  claim — the beach's problem is the year-round dry-weather source, not storm
  runoff or the pump stations, which were addressed without effect.
- **2026 — Adobe Drive culvert → bridge** (above).

**The missing 2016–2026 project — and a confound it creates.** A CEQAnet
sweep (2026-08-15) found the item that fills the gap: the **Wet Weather
Equalization Basin** at 540 Crespi Dr (SCH 2016122016) — a ~$19M, 2.1-
million-gallon sanitary-sewer equalization basin with diversion structures
off the Linda Mar and Arguello sewer lines (the recurring-SSO locations in
our CIWQS data), built under a Regional Board Cease-and-Desist order to end
capacity-driven sewer overflows. MND December 2016, construction from ~July
2017, completion accepted 2020 (City Resolution 37-2020). It is creek-
*adjacent* sewer infrastructure, not in-channel work.

Its ~2019–2020 completion **coincides with the 2020–21 clean stretch** that
findings v7 attributes to dry-winter carryover — and the sewer-overflow
record now lets us test the basin's effect directly. It comes out *against*
reported spills as the chronic driver, and hard. The chronic capacity-
overflow cluster (483–500 Linda Mar Blvd, the Linda Mar lift station,
Anza @ Arguello) sits within ~200 m of the creek-mouth reach, 100%
surface-reaching. Routine wet-winter capacity overflows there **ceased after
the basin**: valley SSO totals ran 17 spills / 886,210 gal in 2013–mid-2017
and 2 / 48,150 during construction, and post-basin the routine cluster
overflows stopped (the large post-2020 volumes are the Oct-2021 lift-station
failure — a pump facility, not the gravity lines the basin relieves — and
the Jan-2023 atmospheric-river sequence, not routine capacity). **Yet the
creek's storm-window response is statistically unchanged** (samples ≤3 days
after rain, E. coli vs 320; verified against `data/pacifica.db`):

| era | n | geo-mean | % over 320 | median storm |
|---|---|---|---|---|
| pre-basin 2015–19 | 61 | 734 | 67% | 19.4 mm |
| dry 2020–21 | 19 | 255 | 42% | 5.0 mm |
| post-basin 2022–26 | 63 | 654 | 60% | 12.6 mm |

2022–26 ≈ pre-basin, and the 2020–21 dip tracks the *small median storm*
those years (5 mm vs ~13–19 mm — dry winters) far more than the basin. The
beach ran the same way: 59% → 58% → 75% over 104. So a completed, verified
fix to the reported-overflow pathway did not change the storm response and
did not hold the beach — the **strongest evidence yet that reported /
preventable sewer overflows are not the chronic driver**. The 2020–21
attribution stays honestly two-cause (dry winters vs. a marginal basin
contribution that cannot be excluded), but nothing about the basin explains
the chronic dry-weather signal that dominates the record. Sources: SCH
2016122016, City Resolution 37-2020, the Regional Board Cease-and-Desist
order.

**Shown on the ledger** (Josh's call, 2026-08-15) as a distinct slate-blue
Construction band (2017–20), deliberately set apart from the grey in-channel
blocks, with a hover note that it is creek-*adjacent* sewer infrastructure,
not in-channel creek work. Rationale: it was a ~$19M, beach-health-motivated
fix Pacifica paid for on the premise it would help the beach — an attempted
remedy shouldn't be invisible just because our read is that the source is
upstream — while the different shade keeps it honestly separate from the
channel changes that could actually alter how the creek reaches the surf.

Also verified, not added as construction bands: **Serra Drive outfall
repair** (SCH 2021020381, in-channel rip-rap, approved Feb 2021 — build date
unconfirmed); 505 San Pedro Ave and 570 Crespi developments (creek-adjacent,
2018 / 2025 approvals); Pedro Point Headlands sediment work (watershed,
~2021–23). A CEQAnet "Las Vegas/San Pedro Creeks" record (2011051083) is a
Goleta project, not ours — flagged to avoid the trap.

Dropped as unverifiable or not construction: a 2021–2022 CDFW *study* (no
in-creek work) and 2024–2025 volunteer debris clearing (minor, not
flow-altering).

**The net for the 2014 question:** there is now more than one infrastructure
change that could touch beach bacteria (the 2014 bridge; the 2018–2020
diversion). That widens, not narrows, the caution: the beach record alone
can't assign the 2014 break to the bridge specifically. But the 2018–2020
result is a genuine, independent data point — the one project *designed* to
clean the beach did not, which fits a chronic dry-weather source that none of
these projects addressed.

## Advocacy read

Clean is not a hypothetical for this beach — it is the **demonstrated
former normal**: 43% of mornings, with months-long clean runs, inside the
same lab record that now fails half the time. Whatever changed around 2014
took that away, and nothing in the weather record explains it (v7). The
target of the source hunt is, concretely, the restoration of a state this
beach held for a decade of measurement.
