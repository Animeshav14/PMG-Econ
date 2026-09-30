"""
clustering.py
-------------
Stage B + C: Regime Discovery for Pillar 3 - Inflation & Policy

Regime labels are anchored to inflation/policy context:
    High PC1  -> "Restrictive"   (high inflation, tight policy)
    Mid  PC1  -> "Neutral"       (moderate inflation)
    Low  PC1  -> "Accommodative" (low inflation, loose policy)

The key insight: a "Slowdown" during a Restrictive regime (2022-23)
demands a very different sector tilt than one during an Accommodative regime (2020).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

FIGURES_DIR = Path(__file__).parent / "outputs/figures"
RESULTS_DIR = Path(__file__).parent / "outputs/results"

N_PCS_FOR_CLUSTERING = 2


def select_features(scores: pd.DataFrame) -> pd.DataFrame:
    return scores.iloc[:, :N_PCS_FOR_CLUSTERING]


def find_optimal_k(X_cluster: pd.DataFrame,
                   k_range: range = range(2, 8)) -> int:
    scores = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = km.fit_predict(X_cluster.values)
        scores[k] = silhouette_score(X_cluster.values, labels)
        print(f"  k={k}  silhouette={scores[k]:.3f}")

    best_k = max(scores, key=scores.get)
    print(f"\n[K-Means] Optimal k = {best_k}  (silhouette = {scores[best_k]:.3f})")
    return best_k


def run_kmeans(X_cluster: pd.DataFrame, k: int) -> dict:
    km = KMeans(n_clusters=k, random_state=42, n_init=20)
    label_arr = km.fit_predict(X_cluster.values)

    labels = pd.Series(label_arr, index=X_cluster.index, name="kmeans_cluster")
    centers = pd.DataFrame(
        km.cluster_centers_,
        columns=X_cluster.columns,
        index=[f"Cluster {i}" for i in range(k)]
    )

    print("\n[K-Means] Cluster centroids (in PC space):")
    print(centers.round(3).to_string())
    print("\n[K-Means] Months per cluster:")
    print(labels.value_counts().sort_index().to_string())

    return {"model": km, "labels": labels, "centers": centers}


def run_gmm(X_cluster: pd.DataFrame, k: int) -> dict:
    gmm = GaussianMixture(
        n_components=k,
        covariance_type="full",
        random_state=42,
        n_init=10,
        max_iter=300,
    )
    gmm.fit(X_cluster.values)

    proba_arr  = gmm.predict_proba(X_cluster.values)
    label_arr  = gmm.predict(X_cluster.values)

    pc_cols    = [f"Cluster_{i}_prob" for i in range(k)]
    proba_df   = pd.DataFrame(proba_arr, index=X_cluster.index, columns=pc_cols)
    labels     = pd.Series(label_arr,    index=X_cluster.index, name="gmm_cluster")
    confidence = proba_df.max(axis=1).rename("regime_confidence")

    print(f"\n[GMM] Log-likelihood: {gmm.lower_bound_:.3f}")
    print(f"[GMM] Mean regime confidence: {confidence.mean():.1%}")
    print(f"[GMM] % of months with >80% confidence: {(confidence > 0.80).mean():.1%}")

    return {
        "model":         gmm,
        "labels":        labels,
        "probabilities": proba_df,
        "confidence":    confidence,
    }


def label_regimes(kmeans_labels: pd.Series,
                  centers: pd.DataFrame) -> pd.Series:
    """
    Labels clusters by PC1 centroid (Inflation Pressure axis).
    High PC1 = Restrictive (high inflation/tight policy)
    Low PC1  = Accommodative (low inflation/loose policy)
    """
    pc1_rank = centers["PC1"].rank(ascending=False).astype(int)
    k = len(centers)

    def assign_name(rank, total):
        if total == 2:
            return {1: "Restrictive", 2: "Accommodative"}[rank]
        if total == 3:
            return {1: "Restrictive", 2: "Neutral", 3: "Accommodative"}[rank]
        if total == 4:
            return {1: "Highly Restrictive", 2: "Restrictive",
                    3: "Neutral", 4: "Accommodative"}[rank]
        return f"Regime {rank}"

    cluster_names = {
        int(cid.split()[-1]): assign_name(rank, k)
        for cid, rank in pc1_rank.items()
    }

    named = kmeans_labels.map(cluster_names).rename("regime").ffill()

    print("\n[Regimes] Cluster -> Regime mapping:")
    for cid, name in cluster_names.items():
        print(f"  Cluster {cid} -> {name}")

    return named


CLUSTER_COLORS = ["#DC2626", "#D97706", "#16A34A", "#2563EB", "#7C3AED"]


def plot_regime_scatter(X_cluster: pd.DataFrame,
                        regime_names: pd.Series,
                        gmm_confidence: pd.Series,
                        save: bool = True) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    regimes = sorted(regime_names.unique())
    palette = {r: CLUSTER_COLORS[i] for i, r in enumerate(regimes)}

    for ax_idx, (sizes_mode, title) in enumerate([
        ("fixed",      "K-Means Regimes"),
        ("confidence", "GMM Confidence (dot size)")
    ]):
        ax = axes[ax_idx]
        for regime in regimes:
            mask = regime_names == regime
            sizes = (gmm_confidence[mask].values * 80) if sizes_mode == "confidence" else 30
            ax.scatter(
                X_cluster.loc[mask, "PC1"],
                X_cluster.loc[mask, "PC2"],
                c=palette[regime], s=sizes,
                alpha=0.75, label=regime, edgecolors="none"
            )

        ax.scatter(X_cluster["PC1"].iloc[-1], X_cluster["PC2"].iloc[-1],
                   c="black", s=120, marker="*", zorder=5, label="Latest")
        ax.set_xlabel("PC1 -- Inflation Pressure")
        ax.set_ylabel("PC2 -- Policy Stance")
        ax.set_title(title)
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.legend(fontsize=8)

    plt.suptitle("Pillar 3 -- Inflation & Policy Regime Map", fontweight="bold")
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "regime_scatter.png"
        fig.savefig(path, dpi=150)
        print(f"[Clustering] Regime scatter saved -> {path}")
    plt.close()


def plot_regime_timeline(regime_names: pd.Series,
                         gmm_confidence: pd.Series,
                         df_raw: pd.DataFrame,
                         save: bool = True) -> None:
    """
    Three-panel chart:
      Top    -> Regime bands over time
      Middle -> GMM confidence
      Bottom -> Raw CPI YoY and Fed Funds for interpretability
    """
    regimes = sorted(regime_names.unique())
    palette = {r: CLUSTER_COLORS[i] for i, r in enumerate(regimes)}

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9),
                                         gridspec_kw={"height_ratios": [2, 1, 1.5]},
                                         sharex=True)

    # -- Top: regime bands ----------------------------------------------------
    dates = regime_names.index
    for i in range(len(dates) - 1):
        ax1.axvspan(dates[i], dates[i + 1],
                    color=palette[regime_names.iloc[i]], alpha=0.6)

    handles = [mpatches.Patch(facecolor=palette[r], label=r) for r in regimes]
    ax1.legend(handles=handles, loc="upper left", fontsize=8)
    ax1.set_ylabel("Inflation Regime")
    ax1.set_title("PMG Pillar 3 -- Inflation & Policy Regime Classification")
    ax1.set_yticks([])

    # -- Middle: confidence ---------------------------------------------------
    ax2.plot(gmm_confidence.index, gmm_confidence.values,
             color="#7C3AED", linewidth=1.2)
    ax2.fill_between(gmm_confidence.index, gmm_confidence.values, 0.5,
                     where=(gmm_confidence >= 0.8),
                     alpha=0.3, color="#16A34A", label="High confidence (>80%)")
    ax2.axhline(0.8, color="gray", linestyle="--", linewidth=0.8)
    ax2.set_ylabel("GMM Confidence")
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=8)

    # -- Bottom: raw CPI YoY + Fed Funds for context --------------------------
    ax3.plot(df_raw.index, df_raw["CPI_YoY"] * 100,
             color="#DC2626", linewidth=1.2, label="CPI YoY (%)")
    ax3b = ax3.twinx()
    ax3b.plot(df_raw.index, df_raw["FedFunds"],
              color="#D97706", linewidth=1.0, linestyle="--",
              alpha=0.8, label="Fed Funds (%)")
    ax3.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax3.set_ylabel("CPI YoY (%)", color="#DC2626")
    ax3b.set_ylabel("Fed Funds (%)", color="#D97706")
    ax3.legend(loc="upper left", fontsize=8)
    ax3b.legend(loc="upper right", fontsize=8)

    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax3.xaxis.set_major_locator(mdates.YearLocator(2))

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "regime_timeline.png"
        fig.savefig(path, dpi=150)
        print(f"[Clustering] Regime timeline saved -> {path}")
    plt.close()


def save_cluster_results(kmeans_labels, regime_names, gmm_results):
    out = pd.concat([
        kmeans_labels,
        regime_names,
        gmm_results["labels"].rename("gmm_cluster"),
        gmm_results["confidence"],
        gmm_results["probabilities"],
    ], axis=1)
    path = RESULTS_DIR / "regime_assignments.csv"
    out.to_csv(path)
    print(f"[Clustering] Regime assignments saved -> {path}")
    return out
