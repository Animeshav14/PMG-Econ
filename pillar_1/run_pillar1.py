"""
run_pillar1.py
--------------
Main entry point for the PMG Macro Engine — Pillar 1: Growth Momentum

Pipeline:
    1. Load & merge all four growth series from Excel
    2. PCA  → extract principal components (Growth Momentum factors)
    3. K-Means → discover macro regimes mathematically
    4. GMM     → assign confidence scores to each regime

Usage:
    python run_pillar1.py
    python run_pillar1.py --k 4        # force a specific number of clusters
    python run_pillar1.py --no-plots   # skip figure generation
"""

import argparse
import pandas as pd
from pathlib import Path

from data_loader  import load_pillar1, get_feature_matrix
from pca_analysis import (run_pca, plot_scree, plot_loadings,
                           plot_pc1_timeseries, save_pca_results)
from clustering   import (select_features, find_optimal_k, run_kmeans,
                           run_gmm, label_regimes,
                           plot_regime_scatter, plot_regime_timeline,
                           save_cluster_results)

RESULTS_DIR = Path(__file__).parent / "outputs/results"


def build_summary_table(df_full: pd.DataFrame,
                         regime_assignments: pd.DataFrame,
                         pca_scores: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs the final output table that will be used for downstream
    ML / sector allocation work.

    Columns:
        - Original z-score features
        - PC1, PC2 scores
        - kmeans_cluster, regime, gmm_cluster
        - regime_confidence
    """
    summary = pd.concat([
        get_feature_matrix(df_full),
        pca_scores[["PC1", "PC2"]],
        regime_assignments[["kmeans_cluster", "regime",
                             "gmm_cluster", "regime_confidence"]],
    ], axis=1)

    return summary


def print_current_state(summary: pd.DataFrame) -> None:
    """Prints the most recent month's macro reading."""
    latest = summary.iloc[-1]
    print("\n" + "="*60)
    print("  PMG PILLAR 1 — CURRENT MACRO STATE")
    print("="*60)
    print(f"  Date           : {summary.index[-1].strftime('%B %Y')}")
    print(f"  PC1 (Momentum) : {latest['PC1']:+.3f}")
    print(f"  PC2            : {latest['PC2']:+.3f}")
    print(f"  K-Means Regime : Cluster {int(latest['kmeans_cluster'])}")
    print(f"  GMM Regime     : {latest['regime']}")
    print(f"  Confidence     : {latest['regime_confidence']:.1%}")
    print("="*60)

    # Investment signal
    conf = latest["regime_confidence"]
    regime = latest["regime"]
    if conf >= 0.80:
        conviction = "HIGH CONVICTION — full allocation tilt recommended"
    elif conf >= 0.60:
        conviction = "MODERATE CONVICTION — partial tilt; monitor closely"
    else:
        conviction = "LOW CONVICTION — hold near-benchmark; await confirmation"

    print(f"\n  Regime Signal  : {regime}")
    print(f"  Conviction     : {conviction}")
    print()


def main(force_k: int = None, make_plots: bool = True) -> None:

    print("\n" + "─"*60)
    print("  PMG MACRO ENGINE — PILLAR 1: GROWTH MOMENTUM")
    print("─"*60)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    df_full = load_pillar1()
    X = get_feature_matrix(df_full)

    # ── 2. PCA ────────────────────────────────────────────────────────────────
    print("\n[Stage A] Running PCA...")
    pca_results = run_pca(X, n_components=X.shape[1])

    if make_plots:
        plot_scree(pca_results["explained"])
        plot_loadings(pca_results["loadings"])
        plot_pc1_timeseries(pca_results["scores"])

    save_pca_results(
        pca_results["scores"],
        pca_results["loadings"],
        pca_results["explained"]
    )

    # ── 3. K-Means clustering ─────────────────────────────────────────────────
    print("\n[Stage B] Running K-Means...")
    X_cluster = select_features(pca_results["scores"])

    if force_k is not None:
        best_k = force_k
        print(f"[K-Means] Using forced k = {best_k}")
    else:
        print("[K-Means] Searching for optimal number of clusters...")
        best_k = find_optimal_k(X_cluster)

    kmeans_results = run_kmeans(X_cluster, k=best_k)
    regime_names   = label_regimes(kmeans_results["labels"],
                                    kmeans_results["centers"])

    # ── 4. GMM ────────────────────────────────────────────────────────────────
    print("\n[Stage C] Running GMM...")
    gmm_results = run_gmm(X_cluster, k=best_k)

    # ── 5. Save & visualise ───────────────────────────────────────────────────
    regime_assignments = save_cluster_results(
        kmeans_results["labels"],
        regime_names,
        gmm_results
    )

    if make_plots:
        plot_regime_scatter(X_cluster, kmeans_results["labels"],
                            regime_names, gmm_results["confidence"])
        plot_regime_timeline(regime_names, gmm_results["confidence"])

    # ── 6. Final summary table ────────────────────────────────────────────────
    summary = build_summary_table(df_full, regime_assignments, pca_results["scores"])
    summary.to_csv(RESULTS_DIR / "pillar1_master_output.csv")
    print(f"\n[Output] Master table saved → {RESULTS_DIR / 'pillar1_master_output.csv'}")

    print_current_state(summary)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PMG Pillar 1 — Growth Momentum Engine")
    parser.add_argument("--k",         type=int,  default=None,
                        help="Force a specific number of clusters (default: auto)")
    parser.add_argument("--no-plots",  action="store_true",
                        help="Skip generating figures")
    args = parser.parse_args()

    main(force_k=args.k, make_plots=not args.no_plots)
