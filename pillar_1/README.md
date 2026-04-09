# PMG Macro Engine — Pillar 1: Growth Momentum

**Portfolio Management Group (PMG)**  
Part of the four-pillar forward-looking macro regime framework described in the PMG initiative brief.

---

## What This Does

This module implements **Stages A, B, and C** of the PMG macro engine for **Pillar 1 only**:

| Stage | Method | Output |
|-------|--------|--------|
| A | Principal Component Analysis (PCA) | Compresses 4 growth indicators into uncorrelated "master signals" |
| B | K-Means Clustering | Groups months with mathematically similar growth conditions into regimes |
| C | Gaussian Mixture Model (GMM) | Adds a confidence score (0–100%) to each regime assignment |

The final output is a **monthly regime label + confidence score** that feeds directly into sector allocation decisions.

---

## Folder Structure

```
pillar1_growth_momentum/
│
├── data/
│   └── raw/
│       └── Pillar1_-_Growth_Momentum.xlsx   ← your Excel data file goes here
│
├── outputs/
│   ├── figures/                             ← all charts saved here
│   │   ├── scree_plot.png
│   │   ├── pca_loadings.png
│   │   ├── pc1_growth_momentum.png
│   │   ├── regime_scatter.png
│   │   └── regime_timeline.png
│   │
│   └── results/                             ← all CSV outputs saved here
│       ├── pca_scores.csv
│       ├── pca_loadings.csv
│       ├── pca_explained_variance.csv
│       ├── regime_assignments.csv
│       └── pillar1_master_output.csv        ← main file for ML / next steps
│
├── data_loader.py      ← loads and merges the Excel sheets
├── pca_analysis.py     ← Stage A: PCA
├── clustering.py       ← Stage B + C: K-Means and GMM
├── run_pillar1.py      ← main entry point — run this
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

Make sure `Pillar1_-_Growth_Momentum.xlsx` is in `data/raw/`. The program expects these sheet names:
- `Industrial Production-INDPRO`
- `Retail Sales-RSAFS`
- `Nonfarm Payrolls-PAYEMS`
- `Real Personal Consumption Exp`

---

## Usage

**Run with auto-detected optimal clusters:**
```bash
python run_pillar1.py
```

**Force a specific number of clusters (e.g., k=4 for a finer regime breakdown):**
```bash
python run_pillar1.py --k 4
```

**Skip figure generation (faster, for CI or headless environments):**
```bash
python run_pillar1.py --no-plots
```

---

## Understanding the Output

### Terminal printout (end of run)

```
============================================================
  PMG PILLAR 1 — CURRENT MACRO STATE
============================================================
  Date           : December 2025
  PC1 (Momentum) : +3.100
  PC2            : -0.568
  K-Means Regime : Cluster 1
  GMM Regime     : Expansion
  Confidence     : 100.0%
============================================================
  Regime Signal  : Expansion
  Conviction     : HIGH CONVICTION — full allocation tilt recommended
```

- **PC1** is your Growth Momentum composite index. Positive = above-average growth; negative = below-average.
- **GMM Regime** is the human-readable regime label derived from K-Means cluster centroids.
- **Confidence** is the GMM soft probability. Use this to size your allocation conviction.

### Conviction tiers

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| ≥ 80% | High conviction | Full allocation tilt toward regime-favored sectors |
| 60–79% | Moderate conviction | Partial tilt; monitor for confirmation |
| < 60% | Low conviction | Hold near-benchmark; await signal confirmation |

---

## The Data: Four Growth Indicators

All four series are sourced from FRED and pre-processed into Z-scores in the Excel file. Z-scores are the primary input to PCA because they put all series on the same scale.

| Series | FRED Ticker | Why it matters |
|--------|-------------|----------------|
| Industrial Production | INDPRO | Hard output data; leads cyclical sector rotation |
| Retail Sales | RSAFS | Consumer demand signal; drives Discretionary vs. Staples rotation |
| Nonfarm Payrolls | PAYEMS | Labor market strength; broad earnings breadth signal |
| Real Personal Consumption | PCEC96 | Inflation-adjusted demand; reality check on consumer strength |

> **Note:** ISM PMI series (Manufacturing + Services) are not included in this version because FRED does not reliably carry them due to licensing. They can be added manually if you source them directly from ISM. GDPNow is included in the Excel as a reference-only sheet and is intentionally excluded from PCA.

---

## How the Math Works (Plain English)

### Stage A — PCA

Our four growth indicators are highly correlated — when the economy grows, all of them tend to rise together. PCA finds the single direction in data space that captures the most variance across all four at once. That direction becomes **PC1**, which we interpret as the shared "Growth Momentum" signal.

In this dataset, **PC1 explains ~81% of variance** across all four indicators. This means one number captures almost everything meaningful about growth conditions each month.

**Reading the loadings:** All four indicators load positively and roughly equally on PC1 (~0.37–0.54). This confirms that PC1 is a genuine "growth tide" — when the economy rises, all four rise with it.

### Stage B — K-Means Clustering

K-Means groups months that look similar in PC1–PC2 space. The algorithm discovers these groupings from the data without being told what "Expansion" or "Contraction" should look like. We use the **silhouette score** to objectively pick the optimal number of clusters (typically k=3: Expansion, Slowdown, Contraction).

**Why this beats the LEI:** The LEI uses a fixed rule. K-Means might discover a cluster that looks like "Stagflation" or a "Credit-driven Slowdown" — regimes the LEI would mislabel.

### Stage C — GMM

K-Means gives a hard label: "you are in Regime 2." GMM upgrades this by fitting Gaussian distributions to each cluster and computing the probability of belonging to each regime. Instead of a binary call, you get: **"Expansion with 88% confidence."**

Low confidence months (e.g., 55/45 Expansion vs. Slowdown) are exactly the transition periods where aggressive allocation tilts are most dangerous. GMM lets you size your conviction accordingly.

---

## Key Output Files

### `pillar1_master_output.csv`
The main file to use for downstream work (ML model input, sector heatmap, backtesting). Columns:

| Column | Description |
|--------|-------------|
| `INDPRO_Z`, `RSAFS_Z`, `PAYEMS_Z`, `PCEC96_Z` | Z-scored input features |
| `PC1`, `PC2` | Principal component scores |
| `kmeans_cluster` | Integer cluster label (0, 1, 2...) |
| `regime` | Human-readable regime name |
| `gmm_cluster` | GMM hard-assigned cluster |
| `regime_confidence` | GMM probability of assigned regime (0–1) |

### `regime_assignments.csv`
Regime labels + full GMM probability columns for every month. Useful for analyzing how often the model was in transition states.

### `pca_scores.csv`
All four PC scores per month. Feed these into your next-stage ML model.

---

## Interpreting the Charts

**`scree_plot.png`** — Tells you how many PCs to keep. Look for the "elbow." In this dataset, PC1 alone explains ~81%, so one component dominates.

**`pca_loadings.png`** — Heatmap showing how each indicator loads on each PC. All positive on PC1 = unified growth signal. PC2 captures the contrast between industrial output and consumer spending.

**`pc1_growth_momentum.png`** — The Growth Momentum index over time. Green shading = above-zero (expansion conditions). Red shading = below-zero (contraction conditions). Aligns visually with the 2020 COVID recession.

**`regime_scatter.png`** — 2D map of every month in PC space. Shows how well-separated the regimes are. The "Latest" star shows where the current month sits relative to history.

**`regime_timeline.png`** — Two-panel chart showing regime classification bands over time (top) and GMM confidence score (bottom). High-confidence months are shaded green.

---

## Next Steps

This Pillar 1 output feeds into the broader PMG engine. Once all four pillars are built:

1. **Combine pillar sub-indices** into a composite macro regime score
2. **Run sector backtesting** — compute average monthly returns per sector within each cluster
3. **Build the sector allocation heatmap** — rank 11 sector ETFs by historical win-rate per regime
4. **Automate data ingestion** via FRED API to replace the manual Excel workflow

For Pillar 2 (Financial Conditions), Pillar 3 (Inflation & Policy), and Pillar 4 (Market Signals), replicate this same folder structure and pipeline with their respective indicators.

---

## Authors & Context

Built for the PMG Macro Model Initiative, Spring 2026
Framework designed by Breanna Jones (Chief Economic Officer).  
Pillar 1 data collection: Milcah (Growth Lead).
Pillar 1 code and analysis: Animesh Shrestha (Economics Associate)