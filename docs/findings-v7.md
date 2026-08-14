# Findings v7 — rain context per sample; the winter-carryover effect (2026-08-14)

New: `pipeline/features.py` builds `rain_context` — 13 knowable-at-sample-time
rain features for every day 1998→present (antecedent windows, days since last
rain/storm, size of the most recent event, water-year cumulative and
percent-of-normal-to-date, fast/slow API stores). Every sample table joins on
`date`.

## Do we have enough precipitation data? Yes.

28 years daily + 11 years hourly (ERA5; one grid cell — upgradeable to
gauge/radar but sufficient). The 523 creek samples cover every rain-distance
stratum:

| last rain | share | exceed | median size of that event |
|---|---|---|---|
| 0–1d ago | 15% | **75%** | 23mm |
| 2–3d | 12% | 44% | 8mm |
| 4–7d | 15% | 44% | 11mm |
| 8–14d | 12% | 38% | 7mm |
| 15–30d | 12% | 44% | 5mm |
| >30d | 33% | **53%** | — |

Note the U-shape: fresh rain spikes it, mid-range settles near the chronic
baseline, and the >30d bucket rises again (the late-summer chronic signal).
Size of the most recent event grades risk on top of recency: 0–3d after
<5mm → creek 56% / beach 25%; after >40mm → creek 70% / beach 63%.

## The winter-carryover effect (Josh's saturation intuition, sharpened)

Split stable-weather samples (>7 days since any rain) by water-year
percent-of-normal-to-date, then control for season:

**Jun–Sep (warm season, n=170):**

| preceding winter | geo-mean | exceed |
|---|---|---|
| dry (<70% of normal) | 161 | 27% |
| normal | 360 | 56% |
| wet (>130%) | **496** | **68%** |

**Oct–May (n=116):** 227 → 320 → 286 (42→41→47%) — weak/absent.

A wet winter sets the *following summer's* dry-weather baseline: ~3× geo-mean,
27%→68% exceedance, with similar month composition across terciles. Mechanism
consistent with a winter-recharged water table sustaining subsurface
transport/exfiltration into the creek all summer (and/or winter-replenished
sediment stores). This also resolves the v5 puzzle: dilution scaling failed
because **load rises with wetness** — wetter conditions raise both flow and
load, so concentration doesn't fall.

Within-season saturation (Oct–May) is the weak version; across-year carryover
is the strong one. The 2014 drought-era *rise* remains explained by the
long-term trend, not this effect (drought summers here run cleaner).

## El Niño implication (direct answer to the record-winter question)

The strongest predictable consequence of a record-wet winter is **the summer
after it**: expect the chronic stable-weather regime near the wet-year class
(~68% exceedance, geo-mean ~500) through summer 2027 even during long dry
gaps. That is a falsifiable, dated prediction this model makes today — and a
year-scale feature (`wy_pct_normal`) the forecast now carries. During the
winter itself, between-storm windows still grade by recency/size as measured
above; the tool's between-storm value compresses but does not vanish.

## Synthesis after v7

Creek stable-weather level = chronic source (ADMS→PRLT entry) ×
**winter-carryover level-set (±3×, year scale)** × warm/dim weather axis
(±2×, week scale) × diurnal cycle (±2×, hour scale) × grab/assay noise
(±half-log). Storm response stacks on top, graded by event size and recency.
