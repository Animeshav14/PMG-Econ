"""
run_pillar3.py
--------------
Main entry point -- PMG Macro Engine, Pillar 3: Inflation & Policy Pressure

Pipeline:
    1. Load & merge CPI YoY, Core CPI YoY, PPI YoY, 5Y Breakeven, Fed Funds
    2. PCA  -> Inflation Pressure (PC1) + Policy Stance (PC2)
    3. K-Means -> discover inflation/policy regimes
    4. GMM     -> confidence score per regime

Usage:
    python run_pillar3.py
    python run_pillar3.py --k 3
    python run_pillar3.py --no-plots
"""

import argparse
import pandas as pd
from pathlib import Path

from data_loader  import load_pillar3, get_feature_matrix
from pca_analysis import (run_pca, plot_scree, plot_loadings,
                           plot_pc1_pc2_timeseries, save_pca_results)
from clustering   import (select_features, find_optimal_k, run_kmeans,
                           run_gmm, label_regimes, plot_regime_scatter,
                           plot_regime_timeline, save_cluster_results)

RESULTS_DIR = Path(__file__).parent / "outputs/results"


def build_summary_table(df_full, regime_assignments, pca_scores):
    return pd.concat([
        get_feature_matrix(df_full),
        pca_scores[["PC1", "PC2"]],
        regime_assignments[["kmeans_cluster", "regime",
                             "gmm_cluster", "regime_confidence"]],
    ], axis=1)


def print_current_state(summary: pd.DataFrame) -> None:
    latest = summary.iloc[-1]
    conf   = latest["regime_confidence"]
    regime = latest["regime"]

    if conf >= 0.80:
        conviction = "HIGH CONVICTION -- full allocation tilt recommended"
    elif conf >= 0.60:
        conviction = "MODERATE CONVICTION -- partial tilt; monitor closely"
    else:
        conviction = "LOW CONVICTION -- hold near-benchmark; await confirmation"

    # Policy signal interpretation
    if "Restrictive" in str(regime):
        signal = "Fed Headwind -- favor defensives, underweight rate-sensitive sectors"
    elif "Accommodative" in str(regime):
        signal = "Fed Tailwind -- favor cyclicals, rate-sensitive, and growth sectors"
    else:
        signal = "Neutral stance -- balanced allocation, watch for regime transition"

    print("\n" + "="*60)
    print("  PMG PILLAR 3 -- CURRENT INFLATION & POLICY STATE")
    print("="*60)
    print(f"  Date              : {summary.index[-1].strftime('%B %Y')}")
    print(f"  PC1 (Inflation)   : {latest['PC1']:+.3f}")
    print(f"  PC2 (Policy)      : {latest['PC2']:+.3f}")
    print(f"  K-Means Regime    : Cluster {int(latest['kmeans_cluster'])}")
    print(f"  GMM Regime        : {regime}")
    print(f"  Confidence        : {conf:.1%}")
    print("="*60)
    print(f"\n  Policy Signal     : {signal}")
    print(f"  Conviction        : {conviction}")
    print()


def main(force_k=None, make_plots=True):
    print("\n" + "-"*60)
    print("  PMG MACRO ENGINE -- PILLAR 3: INFLATION & POLICY")
    print("-"*60)

    # 1. Load
    df_full = load_pillar3()
    X = get_feature_matrix(df_full)

    # 2. PCA
    print("\n[Stage A] Running PCA...")
    pca_results = run_pca(X, n_components=X.shape[1])

    if make_plots:
        plot_scree(pca_results["explained"])
        plot_loadings(pca_results["loadings"])
        plot_pc1_pc2_timeseries(pca_results["scores"], df_full)

    save_pca_results(pca_results["scores"],
                     pca_results["loadings"],
                     pca_results["explained"])

    # 3. K-Means
    print("\n[Stage B] Running K-Means...")
    X_cluster = select_features(pca_results["scores"])

    if force_k is not None:
        best_k = force_k
        print(f"[K-Means] Using forced k = {best_k}")
    else:
        print("[K-Means] Searching for optimal k...")
        best_k = find_optimal_k(X_cluster)

    kmeans_results = run_kmeans(X_cluster, k=best_k)
    regime_names   = label_regimes(kmeans_results["labels"],
                                    kmeans_results["centers"])

    # 4. GMM
    print("\n[Stage C] Running GMM...")
    gmm_results = run_gmm(X_cluster, k=best_k)

    # 5. Save
    regime_assignments = save_cluster_results(
        kmeans_results["labels"], regime_names, gmm_results
    )

    if make_plots:
        plot_regime_scatter(X_cluster, regime_names, gmm_results["confidence"])
        plot_regime_timeline(regime_names, gmm_results["confidence"], df_full)

    # 6. Master output
    summary = build_summary_table(df_full, regime_assignments, pca_results["scores"])
    summary.to_csv(RESULTS_DIR / "pillar3_master_output.csv")
    print(f"\n[Output] Master table saved -> {RESULTS_DIR / 'pillar3_master_output.csv'}")

    print_current_state(summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PMG Pillar 3 -- Inflation & Policy Engine")
    parser.add_argument("--k",        type=int, default=None)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    main(force_k=args.k, make_plots=not args.no_plots)
