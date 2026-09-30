# PMG Macro Engine — Pillar 3: Inflation & Policy Pressure

**Portfolio Management Group (PMG) | SMIF Macro Model Initiative**  
Part of the four-pillar forward-looking macro regime framework described in the PMG initiative brief.

---

## What This Does

This module implements **Stages A, B, and C** of the PMG macro engine for **Pillar 3 only**:

| Stage | Method | Output |
|-------|--------|--------|
| A | Principal Component Analysis (PCA) | Separates realized inflation signal (PC1) from policy/expectations stance (PC2) |
| B | K-Means Clustering | Groups months with mathematically similar inflation and policy conditions into regimes |
| C | Gaussian Mixture Model (GMM) | Adds a confidence score (0–100%) to each regime assignment |

The final output is a **monthly regime label + confidence score** that feeds directly into sector allocation decisions.

---

## Folder Structure

```
pillar3_inflation_policy/
│
├── data/
│   └── raw/
│       └── PMG_Inflation_Policy_Historical_Data.xlsx   ← your Excel data file goes here
│
├── outputs/
│   ├── figures/                             ← all charts saved here
│   │   ├── scree_plot.png
│   │   ├── pca_loadings.png
│   │   ├── pc1_pc2_inflation_policy.png
│   │   ├── regime_scatter.png
│   │   └── regime_timeline.png
│   │
│   └── results/                             ← all CSV outputs saved here
│       ├── pca_scores.csv
│       ├── pca_loadings.csv
│       ├── pca_explained_variance.csv
│       ├── regime_assignments.csv
│       └── pillar3_master_output.csv        ← main file for ML / next steps
│
├── data_loader.py      ← loads and merges all sheets from the Excel file
├── pca_analysis.py     ← Stage A: PCA
├── clustering.py       ← Stage B + C: K-Means and GMM
├── run_pillar3.py      ← main entry point — run this
├── requirements.txt
└── README.md
```

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

Required packages: `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `openpyxl`

**2. Place your data file**

Make sure `PMG_Inflation_Policy_Historical_Data.xlsx` is in `data/raw/`. The program expects these sheet names:
- `Model Data` — CPI YoY, Core CPI YoY, PPI YoY (monthly, 2005–2026)
- `FEDFUNDS` — Federal Funds Rate (monthly)
- `5YearBreakeven` — 5Y Breakeven Inflation (daily, auto-resampled to monthly)

---

## Usage

**Run with auto-detected optimal clusters:**
```bash
python run_pillar3.py
```

**Force a specific number of clusters (k=3 recommended for Restrictive / Neutral / Accommodative):**
```bash
python run_pillar3.py --k 3
```

**Skip figure generation:**
```bash
python run_pillar3.py --no-plots
```

---

## Understanding the Output

### Terminal printout (end of run)

```
============================================================
  PMG PILLAR 3 -- CURRENT INFLATION & POLICY STATE
============================================================
  Date              : February 2026
  PC1 (Inflation)   : -7.728
  PC2 (Policy)      : -1.092
  K-Means Regime    : Cluster 1
  GMM Regime        : Accommodative
  Confidence        : 100.0%
============================================================
  Policy Signal     : Fed Tailwind -- favor cyclicals, rate-sensitive, and growth sectors
  Conviction        : HIGH CONVICTION -- full allocation tilt recommended
```

- **PC1** is the Realized Inflation Pressure index. High = inflation running hot. Low = inflation cooling.
- **PC2** captures the Policy and Expectations Stance (Fed Funds + 5Y Breakeven). High = tight policy/high market rates. Low = loose policy/low expectations.
- **GMM Regime** is the human-readable label. Use this to drive sector tilt decisions.
- **Confidence** is the GMM soft probability. Size your conviction accordingly.

### Conviction tiers

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| ≥ 80% | High conviction | Full allocation tilt toward regime-favored sectors |
| 60–79% | Moderate conviction | Partial tilt; monitor for confirmation |
| < 60% | Low conviction | Hold near-benchmark; await signal confirmation |

### Policy signal interpretation

| Regime | Signal | Sector Implication |
|--------|--------|--------------------|
| Restrictive | Fed Headwind | Favor defensives; underweight rate-sensitive and growth sectors |
| Neutral | Balanced | Moderate tilts; watch for transition signals |
| Accommodative | Fed Tailwind | Favor cyclicals, rate-sensitive, and growth-oriented holdings |

---

## The Data: Five Inflation & Policy Indicators

| Series | Source Sheet | Frequency | Why it matters |
|--------|-------------|-----------|----------------|
| CPI YoY | Model Data | Monthly | Headline inflation; primary Fed mandate target |
| Core CPI YoY | Model Data | Monthly | Strips food and energy; cleaner signal of underlying inflation |
| PPI YoY | Model Data | Monthly | Producer prices; leads CPI and flags pipeline inflation pressure |
| 5Y Breakeven | 5YearBreakeven | Daily → Monthly avg | Market-implied inflation expectations; forward-looking signal |
| Federal Funds Rate | FEDFUNDS | Monthly | Current policy rate; measures how restrictive or accommodative the Fed is |

> **Note:** Real Rates (Fed Funds minus inflation) are listed in the PMG brief as a Pillar 3 candidate but were not available in the current dataset. They can be added in a future version by computing `FedFunds - CPI_YoY` directly from the existing series.

---

## How the Math Works

### Stage A — PCA

Unlike Pillar 1 where one factor explained 81% of variance, Pillar 3 requires **two components** to tell the full story — because realized inflation (CPI, Core CPI, PPI) and monetary policy expectations (Fed Funds, 5Y Breakeven) do not always move together.

**PC1 — Realized Inflation Pressure:** CPI, Core CPI, and PPI all load positively and evenly (0.54–0.56). PC1 rises when hard inflation data runs hot. This is the "Is inflation a problem right now?" signal.

**PC2 — Policy and Expectations Stance:** The 5Y Breakeven (0.71) and Fed Funds Rate (0.64) load heavily on PC2 while realized inflation series load near zero. PC2 captures the market and policy rate environment independently — the Fed Headwind vs. Fed Tailwind dimension in the PMG brief.

Together PC1 + PC2 explain **87.2%** of total variance.

### Stage B — K-Means Clustering

K-Means groups months that are mathematically similar in PC1–PC2 space. The recommended setting is **k=3**, producing Restrictive, Neutral, and Accommodative regimes. The silhouette score auto-selects k=2, but k=3 is preferred because it separates the high-inflation tightening cycle (2022–23) from normal above-average inflation periods.

### Stage C — GMM

GMM adds a probability score to each regime assignment. A month sitting clearly in the Restrictive cluster scores near 100%. A month transitioning between Restrictive and Neutral might score 65/35 — a signal to reduce position sizing until the regime clarifies.

---

## Key Output Files

### `pillar3_master_output.csv`
The main file for downstream ML and sector allocation work.

| Column | Description |
|--------|-------------|
| `CPI_YoY_Z`, `CoreCPI_YoY_Z`, `PPI_YoY_Z`, `Breakeven_Z`, `FedFunds_Z` | Z-scored input features |
| `PC1`, `PC2` | Principal component scores |
| `kmeans_cluster` | Integer cluster label |
| `regime` | Human-readable regime name |
| `gmm_cluster` | GMM hard-assigned cluster |
| `regime_confidence` | GMM probability of assigned regime (0–1) |

---

## Interpreting the Charts

**`scree_plot.png`** — PC1 explains 61.1%, PC2 adds 26.0%. The two-component structure is the key difference from Pillar 1 and reflects that inflation and policy are partially independent signals.

**`pca_loadings.png`** — Shows the split clearly: CPI/Core CPI/PPI dominate PC1; Breakeven/Fed Funds dominate PC2. Clean separation validates the two-factor interpretation.

**`pc1_pc2_inflation_policy.png`** — Dual panel: PC1 over time (inflation pressure) with the 2021–23 surge highlighted, and PC2 (policy stance) with the raw Fed Funds rate overlaid for context.

**`regime_scatter.png`** — 2D map of every month in PC space colored by regime. The 2022–23 inflation spike cluster should appear as a clearly isolated group in the upper-right quadrant.

**`regime_timeline.png`** — Three-panel chart: regime bands over time (top), GMM confidence (middle), and raw CPI YoY + Fed Funds rate for interpretability (bottom).

---

## Key Finding to Flag

The auto-detected optimal k is 2, but **k=3 is strongly recommended** for this pillar. The k=2 solution isolates only the extreme 2020 COVID period (12 months) vs. everything else (241 months), which is too coarse for sector allocation decisions. Running with `--k 3` produces a much more actionable Restrictive / Neutral / Accommodative breakdown.

---

## Next Steps

This Pillar 3 output feeds into the broader PMG engine alongside Pillar 1. Once all four pillars are complete:

1. **Combine pillar sub-indices** into a composite macro regime score
2. **Cross-reference Pillar 1 and Pillar 3** — the current divergence (Pillar 1: Expansion, Pillar 3: Accommodative) is a meaningful signal worth investigating before building the composite
3. **Run sector backtesting** — compute average monthly returns per sector within each inflation regime
4. **Build the sector allocation heatmap** — rank 11 sector ETFs by historical win-rate per regime
5. **Automate data ingestion** via FRED API to replace the manual Excel workflow

---

## Authors & Context

Built for the PMG SMIF Macro Model Initiative, Spring 2026.  
Framework designed by Breanna Jones (Chief Economic Officer).  
Python pipeline and analysis by Animesh.
```
