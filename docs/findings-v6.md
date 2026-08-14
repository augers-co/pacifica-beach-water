# Findings v6 — what modulates the chronic signal (2026-08-14)

Discriminating tests for the late-summer stable-weather peak (findings v5).
Subset: county creek E. coli, stable weather (<2mm/14d), n=249 (190 in
Jun–Oct), with ERA5 daily solar radiation + air temperature joined
(`wx_extra_daily`).

## 1. A warm/dim vs cool/bright axis moves the chronic signal ~2×

Season-controlled (Jun–Oct only), geo-mean cfu/100mL by tercile:

| prior-7d air temp | C | | prior-3d solar | C |
|---|---|---|---|---|
| cool | 241 | | low sun | 428 |
| mid | 340 | | mid | 355 |
| warm | **452** | | high sun | **242** |

r(logC, temp7) = +0.22; r(logC, solar3) = −0.19. The solar effect survives
hour control (within 09–10h samples only, prior-day sun high→low: 230→394),
so it is not the diurnal artifact. But temp and solar are themselves
correlated (r = −0.29 in Jun–Oct): warm weeks tend to be dim weeks here, so
the two covariates largely define **one axis — warm/low-sun stable weeks run
~2× cool/bright weeks**. Both proposed mechanisms (warm-water
survival/regrowth in sediments; reduced solar die-off) remain live, push the
same direction, and peak together in Aug–Sep — jointly explaining the
late-summer peak. Separating them needs water temperature or fog/clear
contrasts at fixed temperature; not possible with current data.

## 2. The weekend-usage fingerprint fails a same-lab test

Cross-organization comparison looked dramatic — Coalition Monday creek-mouth
geo-mean 414 vs Surfrider Thursday 214 in the same weeks (n=30 paired,
2024-07→2025-05) — but Mondays-after-weekends vs Thursdays is confounded by
**different labs** (recall the measured 1.41× county-vs-Coalition offset) and
unknown sampling hour. The county's own record contains a clean same-lab
contrast: 209 stable-weather Mondays vs 39 Tuesdays. Result: **Tuesday 349
(59% exceed) vs Monday 317 (50%)** — no weekend elevation (Tuesday samples
are also taken ~1h earlier, which diurnally inflates them). The
weekend-occupancy version of the usage hypothesis is not supported; a
*diurnal* usage pulse remains compatible with the morning-high pattern
(findings v3), as does morning-accumulated overnight loading with daytime
die-off.

## Standing model of the stable-weather creek signal

Chronic load entering in the ADMS→PRLT reach (v4), pinned near the standard
(v3), modulated by:

- **hour of day** (~2× decline 07h→11h+) — v3
- **warm/dim weather axis** (~2×) — this doc
- **multi-week persistence** (r≈0.6-equivalent out to a month) — v3
- *not* dilution (v5), *not* reported spills (v5), *not* day-of-week (this doc),
  *not* tide (v3)

Modeling consequence: stable-weather forecast features are hour, temp7,
solar3, and lagged creek state. Weekly Monday county samples + these
covariates now explain the seasonal shape without invoking flow.

## Revision (same day): the "dim" half was partly season in disguise

Normalizing solar by clear-sky radiation (FAO-56 Ra; `csi = solar/0.75·Ra`)
removes daylength/season and isolates true cloudiness. Result: season-free
cloudiness alone shows little (r = −0.06; terciles non-monotonic), so the raw
solar3 effect above was substantially seasonal. **The temperature effect
stands** (monotonic, r = +0.22). Two caveats cut the other way: (1) ERA5's
grid cell hardly sees the marine layer — median Jun–Oct csi is 0.87
("mostly clear"), which is not the coastal reality — so true fog variation is
measured with a poor instrument; (2) the warm/cloudy interaction cell runs
highest (warm+cloudy 531 vs warm+clear 369; cool cells 226/282, n≈46–49
each), consistent with fog shielding UV when warmth matters. Verdict:
warmth confirmed; the fog-shielding hypothesis is open pending a real fog
record (Half Moon Bay AWOS ceilometer via the IEM archive — access
confirmed — and/or GOES/MODIS satellite cloud products).

## Caveats

- ERA5 grid cell (37.585, −122.47) sits partly inland of the fog belt; air
  temperature proxies water temperature.
- Jun–Oct n=190; tercile contrasts are ~2× with wide but non-overlapping
  uncertainty; treat coefficients as provisional until the stacked model
  cross-validates them.
- BWTF Thursday series ended 2025-05; if it resumes (or richer time-stamped
  multi-day data is ever shared), the lab-offset and day-of-week questions
  become properly testable.
