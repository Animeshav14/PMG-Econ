# Data redistribution review

Reviewed September 30, 2026 for a public GitHub research repository and portfolio
website. This records published source policies; it is not a permission grant or
a legal opinion. No provider has granted this project a separate license.

There are 35 downloaded series, with different owners and access terms. Thirteen
come from federal agencies with public-domain policies. That establishes a basis
for reusing their original data; it does not settle the access conditions attached
to the copies downloaded through FRED. The other 22 require the distinctions below.
Every downloaded series appears in [redistribution.csv](redistribution.csv).

## Original agency data

| Owner | Series in this project | Published policy |
|---|---|---|
| Bureau of Labor Statistics | PAYEMS, CPIAUCSL, CPILFESL, PPIACO | [BLS copyright information](https://www.bls.gov/opub/copyright-information.htm): statistical publications are public domain and may be reused without specific permission; cite BLS. The policy excludes previously copyrighted images. |
| Bureau of Economic Analysis | PCE, PCEPI, PCEC96 | [BEA FAQ 147](https://www.bea.gov/help/faq/147): material is public domain unless otherwise stated; use and reproduction do not require specific permission. Cite BEA. |
| Census Bureau | RSAFS | [Research Transparency and Public Access policy](https://www2.census.gov/foia/ds_policies/ds027.pdf): employee-created data generally has no U.S. copyright protection; exceptions include third-party works. Follow [Census citation guidance](https://www.census.gov/about/policies/citation.html). |
| Federal Reserve Board | INDPRO, DRTSCILM, DRBLACBS, FEDFUNDS, GS10 | [Board disclaimer](https://www.federalreserve.gov/disclaimer.htm): information is public domain unless otherwise indicated and may be copied and distributed without permission. Cite the Board and retain any third-party notices. |

These findings support publishing an independently acquired, attributed agency
dataset after checking the particular download for exceptions. They do not make
all Federal Reserve Bank products public domain: the regional Banks and the
Board publish different policies. Do not apply an invented CC0 or CC-BY license
to third-party data, or imply that a provider endorses this model.

## FRED delivery terms

[FRED's current terms](https://fred.stlouisfed.org/legal/) distinguish underlying
copyright from service permissions. The summary permits attributed publication
of public-domain and citation-required series, subject to prohibited uses. The
full terms also restrict caching, archiving and supplying stored content to third
parties under Prohibitions (p), and restrict machine-learning-related use in the
summary and API terms. These provisions affect this repository's snapshots and
PCA/clustering workflow, beyond the question of posting CSVs.

The permissive summary and restrictive clauses do not establish unqualified
clearance for the existing FRED copies. Seek written clarification from FRED or
institutional counsel, or independently source agency data under its own terms.
This access issue does not itself change the underlying facts' copyright status.
Ignoring local files in Git does not resolve model-use restrictions.

## Other inputs

| Input | Evidence and conclusion for this repository |
|---|---|
| BAA10Y | [Series notes](https://fred.stlouisfed.org/series/BAA10Y) contain Moody's explicit prior-written-consent requirement for reproduction and redistribution. FRED's citation-required tag is not treated as overriding that notice. No raw-data publication permission established. |
| BAMLH0A0HYM2 | [ICE notice](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) limits the supplied values to internal use and requires prior written approval for publication or distribution. Exclude the downloaded history without that approval. |
| VIXCLS | [FRED notes](https://fred.stlouisfed.org/series/VIXCLS) identify Cboe copyright and FRED's permission to reprint. [Cboe terms, section 2](https://www.cboe.com/terms/) permit limited personal use and otherwise require consent, subject to applicable exceptions such as fair use. This review does not establish permission for a GitHub data archive or decide a fair-use claim. |
| NFCI | [Series page](https://fred.stlouisfed.org/series/NFCI) labels it copyrighted with citation required. [Chicago Fed legal notices](https://www.chicagofed.org/utilities/legal-notices) allow credited noncommercial reproduction of written material but separately address republication/distribution permission. That does not clearly authorize a reusable NFCI CSV archive. Request clarification for that use. |
| T10Y2Y, T5YIE, USREC | These [spread](https://fred.stlouisfed.org/series/T10Y2Y), [breakeven](https://fred.stlouisfed.org/series/T5YIE), and [recession](https://fred.stlouisfed.org/series/USREC) series are St. Louis Fed calculations tagged as copyrighted with citation required. Attributed display has support in FRED's summary; the service restrictions above remain unresolved for repository copies and model use. |
| All 15 Yahoo ETFs | [Yahoo's provider notice](https://uk.help.yahoo.com/kb/SLN2352.html) says not to redistribute its information. [yfinance documentation](https://ranaroussi.github.io/yfinance/) directs users to Yahoo's data terms and describes personal-use access. The package's software license does not license the downloaded prices. No public price-history redistribution permission established. |

The Yahoo row covers IVV, RSP, IWM, IYW, XLB, XLC, XLE, XLF, XLI, XLK, XLP,
XLRE, XLU, XLV and XLY. Yahoo's help notice was available in the search index;
direct page requests returned access/rate-limit errors during this review. The
restriction is also consistent with the package's own usage notice. Its scope
should be confirmed with Yahoo before any publication of downloaded histories.

Optional ISM files are not part of the 35 downloads. Their redistribution must
be covered by the license supplied with them; free current releases do not
establish a license for a full historical archive.

## Generated results

| Artifact | Review outcome |
|---|---|
| Source catalogue, methods and test descriptions | These contain metadata and project descriptions rather than observation histories and are already published. |
| Raw snapshots, canonical caches, archived vintages | Apply the source and delivery conditions above. Current downloaded files remain excluded. |
| Monthly inputs, feature tables and current-state JSON | These contain source observations or transformed values. The JSON includes raw features and sector statistics, so it cannot be treated as a metadata-only file. |
| PCA scores, regime assignments, maps and backtests | Derived analysis requires a separate assessment of the applicable source and service terms. A transformation is not automatically a redistribution license; this review also does not conclude that every derived result is prohibited. |
| Sector tables and heatmap | Depend on Yahoo adjusted prices and composite assignments. Public release is not cleared by the software license or by the fact that returns are computed from prices. |

## What would resolve the remaining cases

For agency data, acquire the observations directly from BLS, BEA, Census and the
Board, retain source URLs and retrieval dates, and verify units and seasonal
adjustment before replacing model inputs. This review does not relabel existing
FRED snapshots as direct-agency downloads.

For other providers, request written confirmation covering: full-history CSV
redistribution on a public, forkable GitHub repository; noncommercial PMG research;
portfolio-site display; PCA/GMM model fitting; local snapshots; and publication
of transformed features, regime probabilities, charts and sector-return summaries.
Ask whether raw and derived data have different conditions and what citations,
notices or fees are required. An institutional subscription is sufficient only
if its actual terms cover these uses.

Use the contact routes in the linked provider terms. FRED lists
`stlsFRED@stls.frb.org` for data questions; Cboe's terms point to its content-use
request process. No permission request has been sent and no paid license has
been purchased as part of this review.
