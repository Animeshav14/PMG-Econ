"""
pca_analysis.py
---------------
Stage A: PCA for Pillar 3 - Inflation & Policy Pressure

Five Z-scored inputs:
    CPI_YoY_Z, CoreCPI_YoY_Z, PPI_YoY_Z, Breakeven_Z, FedFunds_Z

Expected PC interpretation:
    PC1 -> Broad Inflation Pressure (all series rise together)
    PC2 -> Policy Stance (Fed Funds vs. market-based inflation expectations)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from sklearn.decomposition import PCA

FIGURES_DIR = Path(__file__).parent / "outputs/figures"
RESULTS_DIR = Path(__file__).parent / "outputs/results"


def run_pca(X: pd.DataFrame, n_components: int = 5) -> dict:
    """
    Fits PCA on the standardized feature matrix X.

    Returns dict with: pca, scores, loadings, explained
    """
    pca = PCA(n_components=n_components, random_state=42)
    scores_arr = pca.fit_transform(X.values)

    pc_cols  = [f"PC{i+1}" for i in range(n_components)]
    scores   = pd.DataFrame(scores_arr, index=X.index, columns=pc_cols)
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

    print("\n[PCA] Explained variance per component:")
    cumulative = 0
    for pc, ev in explained.items():
        cumulative += ev
        print(f"  {pc}: {ev:.1%}  (cumulative: {cumulative:.1%})")

    print("\n[PCA] Loadings:")
    print(loadings.round(3).to_string())

    return {"pca": pca, "scores": scores,
            "loadings": loadings, "explained": explained}


def plot_scree(explained: pd.Series, save: bool = True) -> None:
    """Scree plot showing variance explained per PC."""
    fig, ax = plt.subplots(figsize=(7, 4))
    cumulative = explained.cumsum()

    ax.bar(explained.index, explained.values * 100,
           color="#DC2626", alpha=0.85, label="Individual")
    ax.plot(explained.index, cumulative.values * 100,
            color="#1D4ED8", marker="o", linewidth=2, label="Cumulative")
    ax.axhline(80, color="gray", linestyle="--", linewidth=0.8, label="80% threshold")

    for i, val in enumerate(explained.values):
        ax.text(i, val * 100 + 1.5, f"{val:.1%}", ha="center", fontsize=9)

    ax.set_ylabel("Variance Explained (%)")
    ax.set_title("Scree Plot -- Pillar 3 Inflation & Policy PCA")
    ax.legend()
    ax.set_ylim(0, 110)
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "scree_plot.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] Scree plot saved -> {path}")
    plt.close()


def plot_loadings(loadings: pd.DataFrame, save: bool = True) -> None:
    """Heatmap of PC loadings."""
    # Only show first 3 PCs for clarity
    load_plot = loadings.iloc[:, :3]

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(load_plot.values, cmap="RdBu_r",
                   aspect="auto", vmin=-1, vmax=1)

    ax.set_xticks(range(len(load_plot.columns)))
    ax.set_xticklabels(load_plot.columns)
    ax.set_yticks(range(len(load_plot.index)))

    # Clean up y-axis labels
    ylabels = [c.replace("_Z", "").replace("_", " ") for c in load_plot.index]
    ax.set_yticklabels(ylabels)

    for i in range(len(load_plot.index)):
        for j in range(len(load_plot.columns)):
            val = load_plot.values[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=9, color="black")

    plt.colorbar(im, ax=ax, label="Loading coefficient")
    ax.set_title("PCA Loadings -- Pillar 3 Inflation & Policy Indicators")
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "pca_loadings.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] Loadings heatmap saved -> {path}")
    plt.close()


def plot_pc1_pc2_timeseries(scores: pd.DataFrame,
                             df_raw: pd.DataFrame,
                             save: bool = True) -> None:
    """
    Two-panel chart:
      Top    -> PC1 (Broad Inflation Pressure) over time
      Bottom -> PC2 (Policy Stance) over time
    Overlays the raw Fed Funds rate as context on the bottom panel.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [1, 1]})

    # -- PC1: Inflation Pressure ----------------------------------------------
    pc1 = scores["PC1"]
    ax1.fill_between(pc1.index, pc1, 0,
                     where=(pc1 >= 0), alpha=0.3, color="#DC2626",
                     label="High Inflation Pressure")
    ax1.fill_between(pc1.index, pc1, 0,
                     where=(pc1 < 0), alpha=0.3, color="#16A34A",
                     label="Low Inflation Pressure")
    ax1.plot(pc1.index, pc1, color="#1D4ED8", linewidth=1.2)
    ax1.axhline(0, color="black", linewidth=0.8, linestyle="--")

    # Shade COVID inflation spike period
    ax1.axvspan(pd.Timestamp("2021-03-01"), pd.Timestamp("2023-06-01"),
                color="orange", alpha=0.12, label="Inflation Surge (2021-23)")

    ax1.set_ylabel("PC1 Score")
    ax1.set_title("PMG Pillar 3 -- Inflation Pressure Index (PC1)")
    ax1.legend(loc="upper left", fontsize=8)

    # -- PC2: Policy Stance ---------------------------------------------------
    pc2 = scores["PC2"]
    ax2.plot(pc2.index, pc2, color="#7C3AED", linewidth=1.2, label="PC2 (Policy Stance)")
    ax2.fill_between(pc2.index, pc2, 0, alpha=0.2, color="#7C3AED")
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")

    # Overlay Fed Funds (right axis) for context
    ax2b = ax2.twinx()
    ax2b.plot(df_raw.index, df_raw["FedFunds"], color="#D97706",
              linewidth=1.0, linestyle="--", alpha=0.7, label="Fed Funds Rate (%)")
    ax2b.set_ylabel("Fed Funds Rate (%)", color="#D97706")
    ax2b.tick_params(axis="y", labelcolor="#D97706")

    ax2.set_ylabel("PC2 Score")
    ax2.set_title("Policy Stance (PC2) vs. Fed Funds Rate")
    ax2.legend(loc="upper left", fontsize=8)
    ax2b.legend(loc="upper right", fontsize=8)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "pc1_pc2_inflation_policy.png"
        fig.savefig(path, dpi=150)
        print(f"[PCA] PC1/PC2 time series saved -> {path}")
    plt.close()


def save_pca_results(scores: pd.DataFrame,
                     loadings: pd.DataFrame,
                     explained: pd.Series) -> None:
    scores.to_csv(RESULTS_DIR / "pca_scores.csv")
    loadings.to_csv(RESULTS_DIR / "pca_loadings.csv")
    explained.to_csv(RESULTS_DIR / "pca_explained_variance.csv")
    print(f"[PCA] Results saved -> {RESULTS_DIR}")
