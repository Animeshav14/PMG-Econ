# Sources, exclusions and redistribution

Each downloaded observation series has a registry entry in `src/registry.py` and
a run-specific provenance record in `data/raw/manifest.json`. Records include
code/name, source/page, frequency/units, first and latest observations, retrieval
timestamp, snapshot path and SHA-256. Source observations and source response
files remain separate from processed monthly features. The public coverage CSV
contains metadata only, not source values.

## Macro data choices

- The model uses [BAA10Y](https://fred.stlouisfed.org/series/BAA10Y), Moody's Baa yield less 10Y
  Treasury yield, as an investment-grade credit-spread proxy. It is not a broad
  investment-grade option-adjusted spread. A request for `BAAA` returned 404.
- [DRBLACBS](https://fred.stlouisfed.org/series/DRBLACBS) is business-loan
  **delinquency**, not lending standards. Download it as context. The model uses
  [DRTSCILM](https://fred.stlouisfed.org/series/DRTSCILM), the SLOOS net percentage
  of domestic banks tightening C&I standards for large/middle-market firms.
- [PCEC96](https://fred.stlouisfed.org/series/PCEC96) currently downloads only from
  2007. Construct the same real-consumption concept consistently from
  [PCE](https://fred.stlouisfed.org/series/PCE) and
  [PCEPI](https://fred.stlouisfed.org/series/PCEPI), both available from 1959.
  Keep the direct series for overlap validation, not as a silently spliced input.
- [BAMLH0A0HYM2](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) states that from
  April 2026 only three years are provided. The download confirms September 2023
  onward. The engine downloads this recent high-yield series but excludes it
  from the core long-history matrix because of its limited coverage.
- [GS10](https://fred.stlouisfed.org/series/GS10) minus backward CPI inflation is
  the ex-post real-rate proxy. It does not estimate a neutral rate.

All other FRED inputs are linked directly in the registry: INDPRO, RSAFS,
PAYEMS, CPIAUCSL, CPILFESL, PPIACO, FEDFUNDS, T5YIE, T10Y2Y, NFCI, VIXCLS and
the retrospective USREC reference. Their official series pages were checked
for identity, frequency and units before use.

## Market data

Use `yfinance.Ticker.history(period="max", auto_adjust=False, actions=True)`;
preserve the downloaded frame and select `Adj Close` consistently. See the
[official yfinance documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
Prices are dividend/split adjusted. Returns are called adjusted-price returns,
not an audited total-return series. Market features compare technology with
the broad market (IYW/IVV), equal with cap weight, small with large cap, and
cyclical with defensive sectors. VIX measures market volatility.

The eleven sectors are XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV and XLY.
Issuer inception dates differ from the first exchange-trading observation:

| ETFs | Issuer inception | First Yahoo trading observation in this snapshot |
|---|---|---|
| XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY | 1998-12-16 | 1998-12-22 |
| XLRE | 2015-10-07 | 2015-10-08 |
| XLC | 2018-06-18 | 2018-06-19 |

Verified with State Street's [sector comparison](https://www.ssga.com/library-content/pdfs/etf/us/target-a-lower-cost-of-ownership-with-sector-etfs.pdf),
[XLRE page](https://www.ssga.com/us/en/institutional/etfs/state-street-real-estate-select-sector-spdr-etf-xlre),
and [XLC page](https://www.ssga.com/us/en/individual/etfs/state-street-communication-services-select-sector-spdr-etf-xlc).
Early partial trading months fail the completeness rule; inception months are
never used to invent a full-month return.

## Optional unavailable data

Both official FRED ISM downloads were attempted:

- `https://fred.stlouisfed.org/graph/fredgraph.csv?id=NAPM&cosd=1900-01-01`: 404.
- `https://fred.stlouisfed.org/graph/fredgraph.csv?id=NAPMNON&cosd=1900-01-01`: 404.

ISM publishes current releases, but a reproducible free full-history download
with permission for this use was not established. Do not scrape or bypass access
controls. Optional request:

| Field | Manufacturing / services PMI |
|---|---|
| Pillar | 1 |
| Source | Institute for Supply Management |
| Page | https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/ |
| Series | ISM Manufacturing PMI / ISM Services PMI; former NAPM / NAPMNON are not working FRED downloads |
| Range | Longest permitted monthly history, preferably 2000-present or longer |
| Format | CSV, columns `date,value`; ISO observation dates and numeric PMI levels |
| Location | `data/raw/local/ISM_MANUFACTURING.csv`, `data/raw/local/ISM_SERVICES.csv` |
| Why manual | FRED endpoints unavailable; historical-use permission must be obtained from ISM |

See [ISM's terms](https://www.ismworld.org/footer/terms-of-use/). Files are optional:
the default four-pillar engine runs without them. To include them, supply both
licensed files and use `--include-ism`. Earnings revision breadth and GDPNow are
not required inputs and are not fabricated. Longer high-yield history would
require obtaining an authorized export from [ICE](https://www.ice.com/market-data/indices);
it is not required for the long-history core.

## Archived vintages

Use the [official FRED observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
with identical `realtime_start` and `realtime_end` if a key is available. Otherwise
use the official ALFRED CSV endpoint with one series and one `vintage_date` per
request. Exact date-stamped column names are mandatory. An experiment showed
that a multi-series request with one vintage date can return later vintages for
subsequent series; the engine therefore makes separate validated requests.

[NFCI's archive](https://alfred.stlouisfed.org/series?seid=NFCI) begins May 25, 2011.
The requested January 2008 vintage returned 404. Never substitute current NFCI
history into an archived-data test. Incomplete information sets are logged and
skipped rather than given a fictitious regime.

## Publication boundary

The [redistribution review](redistribution.md) covers all 35 downloaded series
and distinguishes original-agency permissions from delivery-service conditions.
Several agency datasets are public domain; the combined FRED/Yahoo download is
not covered by one license. The review also identifies unresolved terms affecting
local caching and model use, which Git exclusions alone do not resolve.

Raw inputs, processed observations, generated figures, vintage responses and
workbooks remain ignored. Source links, coverage metadata, methodology and
validation descriptions are published. The review documents the conditions for
releasing additional data and derived results.
