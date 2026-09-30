# Methodology and specification decisions

## Governing instructions

All three supplied documents were read in full: the March 2 kickoff (four pages),
March 30 Python proposal (three pages), and Week 1 Data Guide. Their economic
questions and three-stage modeling pipeline govern the design. The user's
current implementation request overrides earlier assignment instructions.

| Document statement | Implementation decision |
|---|---|
| March 2 swaps pillars 2 and 3 | Use March 30/Week 1 numbering everywhere in the supported engine |
| Week 1 says not to build yet | Superseded by the explicit request to implement all four pillars |
| Week 1 requires Excel submissions | Source snapshots and CSV panels are the engine; old Excel is archival |
| Proposal suggests three master signals | Retain components based on measured variance; no fixed three-PC constraint |
| Proposal describes the engine as predictive | Descriptive and out-of-sample fits are distinguished; no unvalidated predictive claim |
| Proposal links confidence to position sizing | Produce historical statistics only; no allocation rule is implemented |
| “AI Catalyst” | Public name is Market Signals; IYW/IVV is a market rotation measure |
| Real rate: 10Y minus inflation | GS10 minus backward-looking CPI YoY, in percentage points; no neutral-rate estimate |

## Inputs and transformations

All dates are ISO formatted. Source observations are preserved in timestamped
snapshots. A separate canonical cache converts only dates and numeric values.
Missing FRED markers remain missing; duplicate dates and invalid/nonfinite data
are rejected. Cleaned pillar tables contain complete monthly rows; the wider
monthly panel and validation report preserve gaps for inspection.

Monthly FRED values are aligned to month-end. Daily macro series use arithmetic
monthly averages; ETF prices use the last available adjusted close. Daily inputs
require at least 70% of generic business days and weekly inputs at least three
observations. This is a completeness check, not an exchange-calendar model.
The entire calendar month containing `--as-of` is excluded, even when the supplied
date is month-end. This avoids presenting an incomplete month as final.

| Pillar | Feature | Transformation and reason |
|---|---|---|
| 1 | INDPRO, RSAFS, PAYEMS, real consumption | 100 × (x[t]/x[t−12]−1), plus 100 × ((x[t]/x[t−3])^4−1). Separate cycle trend and recent pace; no z-scores of trending levels |
| 1 | Real consumption | 100 × PCE/PCEPI, same BEA aggregate and price basis; retains long monthly history. PCEC96 is an independent overlap check |
| 1 | Optional PMI | Index minus 50; only used with licensed local files |
| 2 | BAA10Y | Spread level; yields alone conflate Treasury rates and credit risk |
| 2 | T10Y2Y | Negative slope so larger values represent more inversion; inversion and acute stress need not coincide |
| 2 | NFCI | Level; broader money/credit conditions |
| 2 | DRTSCILM | Quarterly net percentage tightening lending standards; held for at most two additional months |
| 3 | CPIAUCSL, CPILFESL, PPIACO | Backward-looking YoY percent growth. PPIACO is all-commodities, not final-demand PPI, and is not seasonally adjusted |
| 3 | FEDFUNDS, T5YIE | Levels in percent; nominal policy and market inflation compensation |
| 3 | GS10 − CPI YoY | Ex-post long real-yield proxy, not an expected real policy rate or a neutral-rate gap |
| 4 | RSP/IVV, IWM/IVV, IYW/IVV | Three-month change in log price ratio × 100, using adjusted prices |
| 4 | Cyclical/defensive rotation | Mean XLI/XLF three-month log return minus mean XLP/XLV/XLU log return. Transparent equal-weight proxy; not an optimized portfolio |
| 4 | VIX | Negative log of monthly mean VIX; higher means lower volatility/risk appetite orientation |

Retail sales remain nominal: price pressure can increase them without real
activity growth. Real consumption and production provide complementary evidence.
The PCE/PCEPI identity matched retrieved PCEC96 within 0.04% in overlapping levels
on the validation snapshot; small differences reflect source rounding/vintage
detail. It is used consistently over the full history, without splicing series.

The high-yield spread and business delinquency rate are downloaded reference
series, not silent substitutes for long-history core inputs. GDPNow and earnings
breadth are excluded from model fits. USREC is retrospective validation context
only, never a classifier input.

## PCA, clustering and interpretation

Fit means and standard deviations on the training matrix. PCA uses deterministic
full SVD. Flip each component so its largest absolute coefficient is positive;
this resolves sign ambiguity without claiming a fixed economic interpretation.
Export coefficients and largest contributors rather than calling every PC1
“growth” or every PC2 “policy.” Retain enough PCs for 80% variance with a two-PC
minimum for the map; the composite currently retains five.

K-Means evaluates k=2–5. Report silhouette, adjusted Rand agreement across three
initialization seeds, minimum cluster count, eligibility and selection score.
Require at least max(6, 4% of observations) in each K-Means cluster. Maximize
silhouette + 0.1 × seed stability, preferring the smaller k within 0.02. If no
candidate qualifies, report that explicitly. These are transparent research
defaults, not statistically proven optimal thresholds. Seed stability is not
bootstrap or cross-vintage stability.

The validation snapshot selects k=2 for growth, financial conditions and market
signals; k=3 for inflation/policy; k=2 for the composite. Growth k=3 has a slightly
larger silhouette but creates a two-month cluster, so it is rejected. Composite
k=2 separates a broader stress/weak-market profile from a lower-stress profile;
k=3 and k=4 have substantially lower silhouette. This is economically readable
but coarse: do not present it as a validated four-stage business cycle. COVID
extremes remain visible and materially influence fitting.

GMM is authoritative: fit a regularized full-covariance mixture, require
convergence, map components to profile-ordered `R1`…`Rk`, and reorder probabilities
with the same mapping. Confidence is exactly the posterior probability of the
assigned regime. K-Means assignments are diagnostics only. Export the component
map, probability sums, posterior entropy and K-Means/GMM adjusted Rand agreement.
Regime numbers have no shared meaning across pillars or independent refits.

Regime profiles are probability-weighted standardized original features. Current
raw feature values are also reported, so a current observation is not mistaken
for its regime's historical average. Inflation and policy can diverge: no
“restrictive” label is inferred solely from a high inflation principal component.

Also flag observations whose mixture log density is below the training first
percentile as out of distribution. A far-away point can have near-100% relative
membership probability even when every component fits it poorly. This flag is a
basic extrapolation diagnostic, not a calibrated tail-risk probability.

## Composite

Independent pillar fits retain the longest complete sample for each pillar.
For the composite, refit all four pillar PCA blocks on the same common sample.
Divide each retained score block by the square root of its total training
variance. Each block therefore contributes variance 1 regardless of the number
of retained components. Concatenate blocks and center, but do not restandardize
their columns, before fitting composite PCA and regimes. Export the block
loadings separately because these differ from the independent long-history fits.

The composite GMM's economic profiles use the four mean-standardized feature
signals. These explanatory summaries do not replace the multivariate factors in
the classifier. Profiles and raw features, rather than arbitrary averaged regime
labels, support the interpretation. The map's two-dimensional regions hold
unplotted PCs at their latest values; historical points can legitimately appear
inside a different region when their omitted PC values differ.

## Historical information sets

Three modes must remain separate:

1. **Descriptive current vintage:** full-sample standardization, PCA and regimes.
   Useful for historical association; not out of sample.
2. **Expanding current vintage:** at month t, fit every learned transformation,
   k diagnostic, mixture and composite on months strictly before t. Release-lag
   approximations shift monthly features one month; consumption two months;
   lending surveys two months after the quarterly label; market inputs zero.
   These data still contain subsequent macro revisions.
3. **Archived macro vintage:** download each required macro series as recorded
   by ALFRED at decision month-end. Validate exact vintage column names, preserve
   responses/hashes, and reject unavailable vintages. Apply the conservative
   lags and prior-month fitting above. No current-macro fallback is permitted.
   Yahoo historical prices are current adjusted data, not an archived market
   database. Later multiplicative split/dividend adjustment factors cancel in
   percentage and relative-log returns, but vendor corrections remain possible.

All expanding fits require 48 prior common months. The revised-data diagnostic
begins August 2007, leaving only four pre-recession observations before December
2007. NFCI's ALFRED release history starts May 2011; a complete genuine archived
2008 four-pillar result cannot be reconstructed through this source. This is
reported rather than patched using future data.

The 16 `G±/S±/I±/M±` state buckets use signs of training-standardized economic
signals. They provide consistent definitions for pooling next-month sector
outcomes across refits. GMM IDs remain local to each fit and are not pooled.
The buckets are descriptive thresholds, not optimized allocation rules.

Stress alerts exceed the training 80th percentile; defensive/growth alerts fall
below the training 20th percentile. Episode reports cover 2008, 2020, 2011,
2015–16 and 2022, including misses. False alarms mean an alert month with no NBER
recession in that month or the following six months; incomplete follow-up is
excluded. This does not establish causation or a forecasting success rate.

## Sector statistics

Use all 11 Select Sector SPDR ETFs and IVV as benchmark. Returns are consecutive
calendar-month adjusted-price changes, with no fill before inception or across
missing prices. Descriptive statistics match the regime and return month.
Expanding statistics pair the decision at t with the return at t+1.

Report arithmetic mean, median, sample monthly volatility, fraction of positive
months, mean excess versus IVV, volatility of excess returns, fraction beating
IVV and sample size. Positive-month fraction means return >0; it is not a trading
strategy win rate. Flag samples below 24 observations. No portfolio weights,
overweight/underweight thresholds, transaction costs or execution assumptions
are inferred. Different inception dates and sector reclassifications limit
comparability; XLC and XLRE are absent from 2008 by construction.
