"""
pca_analysis.py
---------------
Stage A of the PMG Macro Engine: Principal Component Analysis

Goal: Compress four z-scored growth indicators (INDPRO, RSAFS, PAYEMS, PCEC96)
into a smaller set of uncorrelated "master signals" that explain most of the
variance in the data. The first principal component (PC1) typically becomes
our Growth Momentum composite index.

Why PCA here?
  - Our four indicators are correlated (they all track growth).
  - PCA finds orthogonal directions of maximum variance.
  - PC1 = the shared "growth cycle" signal stripped of variable-specific noise.
  - Downstream clustering (K-Means / GMM) works better in low-dimensional space.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from sklearn.decomposition import PCA

FIGURES_DIR = Path(__file__).parent / "outputs/figures"
RESULTS_DIR = Path(__file__).parent / "outputs/results"


def run_pca(X: pd.DataFrame, n_components: int = 4) -> dict:
    """
    Fits PCA on the feature matrix X.

    Parameters
    ----------
    X : DataFrame of shape (n_months, n_features)
        Z-scored growth indicators. Already standardized — no re-scaling needed.
    n_components : int
        Number of principal components to extract (max = n_features).

    Returns
    -------
    dict with keys:
        pca         – fitted sklearn PCA object
        scores      – DataFrame of PC scores (same index as X)
        loadings    – DataFrame showing how each variable loads on each PC
        explained   – Series of explained variance ratios per component
    """
    pca = PCA(n_components=n_components, random_state=42)
    scores_arr = pca.fit_transform(X.values)

    pc_cols = [f"PC{i+1}" for i in range(n_components)]

    scores = pd.DataFrame(scores_arr, index=X.index, columns=pc_cols)

    # Loadings: each row = one original variable, each col = one PC
    loadings = pd.DataFrame(
        pca.components_.T,
        index=X.columns,
        columns=pc_cols
    )

    explained = pd.Series(
        pca.explained_variance_ratio_,
        index=pc_cols,
        name="explained_variance_ratio"
    )

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n[PCA] Explained variance per component:")
    for pc, ev in explained.items():
        print(f"  {pc}: {ev:.1%}  (cumulative: {explained[:pc].sum() + ev:.1%})")

    print("\n[PCA] Loadings (how each indicator contributes to each PC):")
    print(loadings.round(3).to_string())

    return {
        "pca":      pca,
        "scores":   scores,
        "loadings": loadings,
        "explained": explained,
    }


# ── Plotting helpers ──────────────────────────────────────────────────────────

def plot_scree(explained: pd.Series, save: bool = True) -> None:
    """
    Scree plot: shows how much variance each PC captures.
    Helps decide how many PCs to keep (look for the 'elbow').
    """
    fig, ax = plt.subplots(figsize=(7, 4))
    cumulative = explained.cumsum()

    ax.bar(explained.index, explained.values * 100,
           color="#2563EB", alpha=0.85, label="Individual")
    ax.plot(explained.index, cumulative.values * 100,
            color="#DC2626", marker="o", linewidth=2, label="Cumulative")

    ax.axhline(80, color="gray", linestyle="--", linewidth=0.8, label="80% threshold")
    ax.set_ylabel("Variance Explained (%)")
    ax.set_title("Scree Plot — Pillar 1 Growth Momentum PCA")
    ax.legend()
    ax.set_ylim(0, 105)

    for i, (val, cum) in enumerate(zip(explained.values, cumulative.values)):
        ax.text(i, val * 100 + 1.5, f"{val:.1%}", ha="center", fontsize=9)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "scree_plot.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] Scree plot saved → {path}")
    plt.close()


def plot_loadings(loadings: pd.DataFrame, save: bool = True) -> None:
    """
    Heatmap of PC loadings.
    Shows which indicators drive each principal component.
    Positive loading = indicator moves WITH the PC.
    Negative loading = indicator moves AGAINST the PC.
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(loadings.values, cmap="RdBu_r", aspect="auto",
                   vmin=-1, vmax=1)

    ax.set_xticks(range(len(loadings.columns)))
    ax.set_xticklabels(loadings.columns)
    ax.set_yticks(range(len(loadings.index)))
    ax.set_yticklabels(loadings.index)

    # Annotate each cell with its loading value
    for i in range(len(loadings.index)):
        for j in range(len(loadings.columns)):
            val = loadings.values[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=9, color="black")

    plt.colorbar(im, ax=ax, label="Loading coefficient")
    ax.set_title("PCA Loadings — Pillar 1 Growth Indicators")
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "pca_loadings.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] Loadings heatmap saved → {path}")
    plt.close()


def plot_pc1_timeseries(scores: pd.DataFrame, save: bool = True) -> None:
    """
    Plots PC1 over time — this is our Growth Momentum composite index.
    PC1 > 0 = above-average growth conditions.
    PC1 < 0 = below-average growth conditions.
    Shades NBER-approximate recession periods for context.
    """
    pc1 = scores["PC1"]

    fig, ax = plt.subplots(figsize=(13, 4))

    # Shade below-zero (weak growth) vs above-zero (strong growth)
    ax.fill_between(pc1.index, pc1, 0,
                    where=(pc1 >= 0), alpha=0.3, color="#16A34A", label="Expansion")
    ax.fill_between(pc1.index, pc1, 0,
                    where=(pc1 < 0), alpha=0.3, color="#DC2626", label="Contraction")
    ax.plot(pc1.index, pc1, color="#1D4ED8", linewidth=1.2)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")

    # Approximate NBER recessions visible in our window
    recessions = [("2020-02-01", "2020-04-01")]
    for start, end in recessions:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                   color="gray", alpha=0.25, label="Recession (NBER approx.)")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.set_ylabel("PC1 Score (Growth Momentum)")
    ax.set_title("PMG Pillar 1 — Growth Momentum Index (PC1)")
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "pc1_growth_momentum.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] PC1 time series saved → {path}")
    plt.close()


def save_pca_results(scores: pd.DataFrame,
                     loadings: pd.DataFrame,
                     explained: pd.Series) -> None:
    """Saves PCA outputs to CSV for downstream use (clustering, reporting)."""
    scores.to_csv(RESULTS_DIR / "pca_scores.csv")
    loadings.to_csv(RESULTS_DIR / "pca_loadings.csv")
    explained.to_csv(RESULTS_DIR / "pca_explained_variance.csv")
    print(f"[PCA] Results saved → {RESULTS_DIR}")
