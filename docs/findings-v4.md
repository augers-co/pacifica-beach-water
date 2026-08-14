# Findings v4 — first analysis of the Coalition's own dataset (2026-08-14)

Source: lindamarwaterquality.org/test-results — the canonical dataset per the
Coalition (Surfrider feeds and draws from it). Two Excel files (Enterococcus,
E. coli, both through 2026-07-20; PDFs on the site are print mirrors of the
same tables; verified byte-identical with independently downloaded copies).
Parsed by `pipeline/parse_lmwq.py` into ~1,200 observations, 14 series,
2024-07 → 2026-07 weekly. Raw files are deliberately not committed.

What the dataset adds over public records: four creek sites sampled the same
morning (spatial profile), a categorical **Creek Level** (Low/Med/High) and
**Rain** flag per sampling, county ocean stations LM5 **and LM7** (pump
station, ~200 yd north of the creek mouth — not in our CEDEN pulls), and a
Surfrider BWTF creek-mouth series (Thursdays, n=33, ends 2025-05).

## 1. Stable-weather load appears to enter HIGH in the watershed

Geo-mean E. coli (cfu/100mL) by site in stable weather (<2mm rain/14d),
assumed upstream → downstream order:

| Peralta Bridge | Adobe Sanchez | Linda Mar Bridge | Creek Mouth |
|---|---|---|---|
| **357** | 161 | 243 | 208 |

The most upstream site is the dirtiest when it hasn't rained (enterococcus
shows the same rank-order, 268 at Peralta). On rain days the pattern shifts
(everything rises; mouth peaks at 2,059 ent geo-mean) — consistent with
distributed wash-in during storms vs a concentrated upper-valley dry-weather
input. ⚠ **Caveat: site order is assumed from Pacifica street geography**
(Peralta Rd = upper valley; Sanchez Adobe = mid; Linda Mar Blvd/Hwy 1 = lower)
— needs confirmation before anything is built on it.

## 2. The Creek Level column can't test dilution (yet)

In stable weather, every single sample is level "Low" (n=112 ecoli / 169 ent) —
the Low/Med/High variation is entirely rain-driven, so it's collinear with
rain and can't separate dilution from wash-in. The donor-catchment continuous
flow proxy (findings v3) remains the way to test the dilution hypothesis.

## 3. Same-morning duplicate measurements disagree 20% of the time

74 same-day pairs of Coalition vs County at the identical creek-mouth reach:
log-log r = 0.56, county geo-mean 1.41× higher, and **pass/fail agreement at
the 320 standard only 80%**. Two competent measurements of the same water on
the same morning flip the label 1 time in 5 — direct, quantified confirmation
of the findings-v3 thesis (near-threshold baseline + ~half-log grab/assay
noise ⇒ label flips). Modeling must target log-concentration, and forecast
verification must tolerate label noise (~0.56 inter-source r is an effective
ceiling on single-grab predictability).

## 4. LM7 is the modern spatial control — contamination stays at the creek mouth

County enterococcus, 2024-07 → 2026-07:

| | LM5 (creek mouth) | LM7 (pump station, +200 yd) |
|---|---|---|
| exceed >104 overall | 65% (n=93) | **8%** (n=90) |
| exceed, stable weather | **78%** (n=41) | **2%** (n=40) |
| geo-mean | 147 | 20 |

When LM5 fails, LM7 fails the same morning only 12% of the time. The old
LM6 contrast (1998–2008) is thus confirmed with current data: the plume is
tightly confined. LM7's two big spikes (8,664 on 2024-12-16; 2026-01-19) are
consistent with the site's note about rare pump-station discharges.
Note LM5's stable-weather rate (78%) is far above its long-run historical dry
rate (~20%) — the modern creek-mouth surf zone fails most calm mornings.

## Immediate implications

- The Coalition's "surf north of the pump station" guidance is strongly
  supported by their own paired county data.
- Cross-source calibration noise (±half-log) is now measured, not assumed —
  it sets both the modeling target (log-concentration) and the honest
  verification floor.
- Next analyses: confirm site geography; donor-catchment flow proxy vs the
  11-year concentration record; join CIWQS SSO records against the LM7/creek
  spike dates.
