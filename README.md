# Pacifica Beach Water

A dashboard for ocean and beach water quality in Pacifica, CA — surf/swim safety at Linda Mar (Pacifica State Beach), Rockaway Beach, and Sharp Park, with a focus on the San Pedro Creek outflow at Linda Mar.

Built in support of the **Linda Mar Water Quality Coalition**, a grassroots alliance of Surfrider San Mateo County's Blue Water Task Force, Salted Roots, the San Pedro Creek Watershed Coalition, Cultivar Foundation, and the Pedro Point Surf Club. The Coalition runs weekly bacteria testing along San Pedro Creek (85% of creek samples over the past two years exceeded state fecal-bacteria standards, with DNA source-tracking pointing at human contamination from suspected sewer leaks) and is documenting community health impacts via the [Linda Mar Health Impacts Survey](https://survey.alchemer.com/s3/8923478/Linda-Mar-Health-Impacts-Survey) — earaches, eye/sinus infections, rashes, GI illness after water contact — to inform public agencies and elected officials.

## Why

Linda Mar Beach has some of the worst measured water quality in San Mateo County. In 2025, samples taken where San Pedro Creek meets the ocean failed state/federal fecal-bacteria standards ~72% of the time. Both the creek and the beach are on the Clean Water Act impaired water bodies list. There is real, regularly collected data — but it's scattered across county pages, a Surfrider portal, and state aggregators.

## Who monitors the water

| Organization | What they test | Cadence | Where data lands |
|---|---|---|---|
| **San Mateo County Environmental Health** (with County Public Health Lab) | 43 sites countywide incl. Linda Mar #5 (at San Pedro Creek) and San Pedro Creek; total coliform, E. coli, enterococcus | Weekly (Monday sampling) | [smchealth.org/beaches](https://www.smchealth.org/beaches) — advisories map, email list, hotline (650) 599-1266 |
| **Surfrider San Mateo County — Blue Water Task Force** | Beach + creek bacteria at ~7 local sites, 12+ years of history | Weekly | [bwtf.surfrider.org](https://bwtf.surfrider.org/) |
| **Linda Mar Water Quality Coalition** (Surfrider SMC, Salted Roots, San Pedro Creek Watershed Coalition, Cultivar Foundation, Pedro Point Surf Club) | Enterococcus + E. coli at 4 sites along San Pedro Creek to localize pollution sources; DNA-based source tracking since July 2025 | Weekly | Via BWTF portal, annual report, Instagram |
| **CA State Water Board — BeachWatch / Safe to Swim** | Aggregates all recreational-water sampling statewide | Aggregator | [Safe to Swim map](https://mywaterquality.ca.gov/safe_to_swim/) |
| **Heal the Bay — Beach Report Card** | Letter grades derived from agency sampling data | Weekly grades | [beachreportcard.org](https://beachreportcard.org/) |

## Candidate data sources for the dashboard

- **County results + advisory status** — smchealth.org beach map/postings (needs scraping or a feed; format TBD)
- **BWTF portal** — bwtf.surfrider.org, per-site historical results (inspect for JSON API)
- **CEDEN / Safe to Swim** — state data warehouse behind the map; has bulk/query access
- **Heal the Bay BRC** — grades API used by beachreportcard.org (inspect)

## Repo layout

- [`pipeline/fetch.py`](pipeline/fetch.py) — pulls county bacteria records (CEDEN + BeachWatch via data.ca.gov), advisory postings, and daily watershed rainfall (ERA5) into `data/pacifica.db` (SQLite; gitignored)
- [`pipeline/analyze.py`](pipeline/analyze.py) — builds antecedent-rain features, computes exceedance vs. single-sample standards
- [`pipeline/charts.py`](pipeline/charts.py) — renders the findings charts
- [`docs/data-sources.md`](docs/data-sources.md) — verified source map (what exists, what's machine-readable, what's missing)
- [`docs/findings-v1.md`](docs/findings-v1.md) — first results: the creek has a dry-weather source; the beach is rain-driven; Linda Mar deteriorated starting ~2014

```bash
python3 -m venv .venv && .venv/bin/pip install pandas requests matplotlib
.venv/bin/python pipeline/fetch.py && .venv/bin/python pipeline/analyze.py
```

## Data hierarchy

**Creek measurements are the primary signal.** Single grab samples in the surf
zone are inherently noisy (bacteria vary by orders of magnitude over meters and
minutes), so ocean-station data here serves as context and validation — it
shows how creek influence expresses at the beach, and is not treated as a
measure of ocean water quality. The modeling target is **creek state and creek
influence** (rain-driven amplification, clearance timing, transport conditions),
not ocean quality per se.

## Status

v2 findings done. Next: Surfrider BWTF export (requested), stacked creek-state model with honest cross-validation, then live dashboard.

## North star

This project exists to (1) produce clear, defensible insight into what drives
pollution in San Pedro Creek, (2) help locate the sources, (3) make the
information useful enough to ordinary beach users that it builds public and
political will, and (4) support actual fixes. Every analysis and product
choice should trace to one of those four. Evidence standards are set for
skeptical review: the likely remedies are expensive and land on homeowners,
so claims ship with stated falsifiable tests, dated predictions, and the raw
record alongside every summary.
