# Spring 2026 prototype audit

Baseline: main commit `2fdb18fcc507e67d3c9db86077b208afaa5c20df`.
GitHub connector inspection found only `main`, Pillars 1 and 3, eight Python
files, two READMEs, two requirements files, two raw workbooks, a breakeven CSV,
ten generated figures, ten result tables, and three tracked bytecode files.
All source modules, loader mappings, raw workbook sheets, result tables and
figures were inspected. There was no root README, downloader, test suite,
financial-conditions model, market model, composite, or sector analysis.

## Findings

- **Pillar 3 used future inflation.** `Model Data!D2` contains `= B14 / B2 - 1`;
  core and PPI columns use the same forward twelve-month formula. The final
  rows refer to empty future cells and cache `-1` (−100%). January/February
  2026 outputs label these errors “Accommodative” with 100% GMM confidence.
  This invalidates the old latest reading and historical timing.
- **Pillar 1 standardized levels.** The workbook's z-scores reflect raw levels,
  not the supplied growth columns. PC1 therefore largely follows secular
  increases in activity. The old sample starts in 2010, missing the 2008 cycle.
  The raw retail-sales sheet also contains a missing January 2026 level with
  cached −100% growth; the new pipeline never interprets a blank as zero.
- **Regime/probability mismatch.** Both pipelines assign names from K-Means
  and append probabilities from an independently fitted GMM. Different component
  numbering and assignments make the reported named confidence unreliable.
- **Look-ahead in estimation.** Both fit PCA and clustering on the entire sample;
  Pillar 3 also computes full-sample standardization. There is no historical
  availability, data-vintage, or held-out prediction implementation.
- **Interpretation overreach.** High inflation PC1 becomes “Restrictive” without
  an identified neutral rate or joint policy assessment. Confidence triggers
  untested allocation advice. Neither behavior is retained in the new engine.
- **Other issues.** Pillar 1's printed cumulative explained variance double-counts
  the current component. Plot palettes can be shorter than candidate k ranges.
  Loaders lack duplicate-date/freshness checks. Dates and raw units depend on
  manually updated Excel formulas. Bytecode is tracked.

## Reuse and preservation

The original source is preserved byte-for-byte under `legacy/spring2026/`.
Original commit history is unchanged. The new implementation retains the
PCA/K-Means/GMM workflow, sklearn estimator approach, deterministic seeds,
exported scores/loadings, and regime scatter/timeline deliverables. Shared
implementation replaces duplicated statistical/plotting routines, while
economic features remain visible in each `pillar_N/features.py`.

Old raw inputs and outputs remain local but are untracked on the new branch.
The old implementation can still be studied through its archive and original
commit; it is not presented as valid new-model output. No private planning
documents or source data are added to Git.
