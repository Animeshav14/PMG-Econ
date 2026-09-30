# Validation record

Validation snapshot: September 30, 2026, using Python 3.12.

## End-to-end execution

The downloader retrieved all 35 enabled series/instruments: 20 FRED macro and
reference series and 15 ETFs. FRED's keyless official CSV endpoint and Yahoo's
adjusted-price history both worked. The optional NAPM, NAPMNON and BAAA downloads
were attempted and returned 404. Snapshot hashes and retrieval timestamps are
stored locally. No enabled source was stale under the documented thresholds.

All four pillar fits, composite PCA/regimes, 11-sector statistics and figures
completed. Latest pillar observation months are July 2026 for growth and
August 2026 for the other pillars. The composite's latest complete observation
month is July 2026. Per-series dates appear in `data_coverage.csv` and the
run-generated `outputs/tables/data_coverage.csv`.

Generated maps, sector heatmap, PCA diagnostics, pillar timelines and historical
signal figures were inspected. The 2D landscape holds the omitted principal
components at their latest values when drawing regime boundaries.
Dark heatmap cells use contrasting light text. No generated figure is added to
the public branch without resolving underlying data redistribution rights.

## Numerical and alignment checks

`python -m pytest -q` passed all **15 tests** on Python 3.12. The real-data
`python run_engine.py --backtest` run also completed, together with separate
historical cutoffs at `2009-01-01` and `2020-05-01`. Archived-vintage runs covered
January 2019–December 2020 and the unavailable January 2008 information set.

The lightweight tests cover official download parsing/route selection, expected
columns, duplicates, missing values, finite inputs, frequency conversion,
incomplete months, bounded quarterly holds, backward growth rates, availability
lags, stale-data detection, deterministic PCA/regimes, component/probability
mapping, equal composite block variance, future-data perturbations, historical
cutoffs, sector return alignment and final JSON output. A vintage-header test
rejects silently returned current data, and an extrapolation test distinguishes
high posterior confidence from low absolute likelihood.

Tests use synthetic fixtures for deterministic CI. Live retrieval was validated
separately with real downloads; a green unit suite is not a claim that an external
provider will always be available. Historical `--as-of` runs use separate output
directories. Current revised data are explicitly labelled in those runs.

## Revised-data historical diagnostics

The expanding diagnostic uses 48 prior common monthly observations and starts
August 2007. It refits scaling, PCA, k selection and GMM at every decision date.
COVID and other outliers remain in the training sets; no successful episodes
were selected to tune thresholds.

| Episode | Six-month pre-period result | Limitation |
|---|---|---|
| 2008 cycle | Stress, defensive rotation and weak growth all appear in the available pre-period | Only four pre-months after warmup; later revised macro data |
| 2020 cycle | No advance stress threshold crossing; one defensive alert in August 2019 | A distant isolated alert does not establish useful COVID prediction |
| 2011 slowdown | No advance stress/rotation warning | A miss, retained in the report |
| 2015–16 slowdown | No advance stress/rotation warning | A miss, retained in the report |
| 2022 tightening | Defensive alerts before onset; no advance stress alert | This is a tightening episode, not an NBER recession |

Across 222 months with complete six-month follow-up, stress alerts occur 61 times,
with 37 having no recession in that month or the following six months. Defensive
alerts occur 52 times, with 37 such false alarms. Weak-growth alerts occur 56
times, with 32 such false alarms. These are alert-month counts, not independent
events, and do not validate a trading strategy.

## Archived macro data

The 2019–2020 run requests exact month-end vintages for every required macro
input. It classifies 21 of 24 months; January–March 2019 lack a complete eligible
released panel and are skipped: retail-sales growth is missing in all three,
and real-consumption growth is also missing in February. The 2020 pre-period
again has no advance stress alert and one defensive alert (August 2019).
The revised-data weak-growth alert
before 2020 does not survive the archived-macro test, illustrating revision risk.

An official January 2008 NFCI vintage request returns 404. ALFRED lists NFCI's
release history beginning May 2011. A full point-in-time 2008 four-pillar result
is therefore unavailable from these archives. The code records failures instead
of substituting a future NFCI history.
The full January 2008 attempt also reports unavailable BAA10Y, T10Y2Y, DRTSCILM,
T5YIE and VIXCLS vintages. Successful series remain cached with their exact
requested-vintage headers; they are not enough for the full four-pillar test.

Even the archived-macro test uses current Yahoo adjusted-price histories, not a
vendor archive of prices as originally seen. Split/dividend rescaling cancels in
the selected return ratios, but later vendor corrections remain possible. The
result is a macro-vintage-aware historical diagnostic, not a fully audited live
portfolio backtest. Exact unavailable dates and source errors are saved locally
under `outputs/vintage_backtest/`.

## Repository checks

Source code and documentation are reviewed separately from ignored raw data,
processed panels, generated outputs, private planning files and credentials.
Tracked files exclude raw observations, generated figures, result tables and
bytecode. Download and run locally to reproduce the charts.

## Optional inputs

All required core data was acquired programmatically.
Optional licensed ISM history and longer ICE history are described in
`sources.md`. These do not block the four-pillar pipeline. Missing archival
vintages limit which historical information sets can be tested.
