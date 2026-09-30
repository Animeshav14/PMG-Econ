# PMG Macro Regime Engine

I built this macro regime model for Georgia State University's Portfolio
Management Group (PMG). It combines economic, credit, inflation, and market data
to classify historical macro environments and study how U.S. equity sectors
behaved within them.

| Pillar | Question | Main inputs |
|---|---|---|
| Growth Momentum | Is activity strengthening or weakening? | Industrial production, retail sales, payrolls, real consumption |
| Financial Conditions | Is credit tightening or stress building? | Baa–Treasury spread, yield curve, NFCI, lending standards |
| Inflation & Policy | How are inflation and monetary conditions changing? | CPI, core CPI, PPI, fed funds, breakevens, ex-post real 10Y yield |
| Market Signals | Is market leadership becoming defensive? | RSP/IVV, IWM/IVV, IYW/IVV, cyclical/defensive ETFs, VIX |

## Run

Python 3.12 is the tested runtime. Create a virtual environment, then:

```sh
python -m pip install -r requirements-lock.txt
python update_data.py
python run_engine.py --backtest
python -m pytest -q
```

`update_data.py` retrieves observations, preserves source snapshots and hashes,
reports per-series success/failure and dates, and regenerates validated monthly
inputs. It uses the FRED API when `FRED_API_KEY` is set, otherwise FRED's official
keyless CSV downloads. Yahoo ETF history is retrieved through `yfinance`.
No API key is committed or printed. Excel is not required.

```sh
# Historical cutoff using today's revised data; excludes the cutoff calendar month
python run_engine.py --as-of 2020-03-01

# Download archived macro information sets for the COVID cycle (cached locally)
python backtest_vintages.py --start 2019-01-01 --end 2020-12-31

# Optional, only with appropriately licensed local PMI history
python run_engine.py --include-ism
```

## Outputs

`outputs/latest/current_state.json` records the run date, retrieval snapshot,
each pillar's month, regime, posterior probabilities, profiles and latest raw
features; composite state; sector statistics; failed, lagged and stale series.

- `data/processed/latest/`: cleaned monthly data and transformed/availability panels.
- `outputs/tables/pillar_1/` through `pillar_4/`: PCA scores, coefficients,
  explained/cumulative variance, clustering diagnostics, profiles and assignments.
- `outputs/figures/composite/regime_map.png`: **Macro Landscape Map** with current
  location, historical regimes, conditional regime regions and membership probability.
- `outputs/figures/sector_allocation_heatmap.png`: **Sector Allocation Heatmap**
  for all 11 SPDR sectors, with sample sizes and defined return statistics.
- `outputs/backtest/`: expanding fits, episode checks, false alarms and next-month
  sector associations. These use revised macro data with explicit release lags.
- `outputs/vintage_backtest/`: archived-macro tests, exact vintage provenance and
  unavailable months. Current Yahoo adjusted-price history is still a limitation.
- `outputs/as_of/YYYY-MM-DD/`: isolated historical-cutoff results.
- `outputs/latest/manual_download_requests.md`: exact requests for failed inputs.

## Method

Activity and price levels become backward-looking growth rates. Spreads, lending
standards and rates retain meaningful levels. Market features use three-month
relative log returns from consistently adjusted prices. Monthly gaps are not
filled; quarterly survey observations can be held for two subsequent months,
with an explicit availability lag in historical tests.

Within each pillar, PCA retains at least 80% of variance, with two components as
the minimum needed for the map. K-Means candidates k=2–5 are compared using
silhouette, seed stability and minimum cluster sizes. A separate GMM supplies
**both** authoritative regime assignments and their probabilities. Names `R1`,
`R2`, etc. refer to model-specific profiles, not known economic-cycle truths.

The composite refits pillar factors on a common sample, scales each pillar block
to equal total variance, and fits another PCA/K-Means/GMM sequence. It never
averages regime labels. Full coefficient, profile and diagnostic tables support
the economic interpretation. The map is a two-dimensional slice of a model that
can retain more than two PCs.

See [methodology](docs/methodology.md), [data sources](docs/sources.md), and
[validation](docs/validation.md) for details.

## Coverage and limitations

The verified download dated **2026-09-30** provides a common descriptive sample
from **August 2003 through July 2026** (275 complete months). Individual growth
inputs reach back further; Pillars 2–4 reach August 2026. The common date is
limited by consumption publication timing and missing observations. Every run
recomputes coverage; [the source catalogue](docs/data_coverage.csv) contains
first/latest observation dates and retrieval timestamps for every downloaded series.

Descriptive fits use the full available sample. Expanding tests refit all learned
parameters on strictly earlier months. Archived-macro tests additionally require
the exact ALFRED vintage and never substitute today's macro data. A complete
archived 2008 four-pillar test is unavailable because NFCI's ALFRED archive starts
in 2011. The 2008 result is therefore a revised-data historical diagnostic.

The model is sensitive to COVID outliers, training length, revisions and feature
choices. Posterior membership is not a calibrated forecasting probability. Sector
statistics use unequal inception-limited samples, omit transaction costs and
taxes, and do not validate allocation rules. XLRE starts in 2015 and XLC in 2018;
neither is backfilled into 2008. Earnings revision breadth is excluded because a
reproducible free historical breadth dataset was not established.

ISM history is optional. FRED's NAPM and NAPMNON downloads return 404. ICE high-yield history
now covers only three years, so it is downloaded as a reference supplement and
excluded from the long-history core. Raw data, processed data and generated
figures stay local: FRED access does not imply redistribution rights for Moody's,
ICE, Cboe or Yahoo-supplied data. No licensed observations are published here.

## Repository

```text
pillar_1/ ... pillar_4/   Pillar definitions
src/                    Data, modeling, composite, sector analysis and plotting
data/                   Local raw and processed data
outputs/                Generated results
tests/                  Pipeline and numerical tests
docs/                   Methodology, data sources and validation
```

The [data](data/README.md) and [outputs](outputs/README.md) folders include tracked
instructions and placeholders. Downloads, processed datasets and generated
results populate those folders locally and remain ignored by Git.
