"""
clustering.py
-------------
Stage B + C of the PMG Macro Engine: Regime Discovery

Stage B — K-Means Clustering
    Finds mathematically similar months in PC-space and groups them into
    regimes. We do NOT pre-define what "Expansion" looks like — the data
    discovers it. This avoids the subjective thresholds in the legacy LEI model.

Stage C — Gaussian Mixture Model (GMM)
    Upgrades K-Means by adding a confidence (probability) score to each
    regime assignment. Instead of a hard "you are in Regime 2," GMM outputs
    "you are in Regime 2 with 88% confidence." Low confidence = smaller
    position sizes. High confidence = high-conviction allocation tilt.

Both models operate on the PCA scores (PC1, PC2, optionally PC3) rather
than the raw variables — this ensures we cluster on the *essence* of the
macro environment, not correlated noise.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

FIGURES_DIR = Path(__file__).parent / "outputs/figures"
RESULTS_DIR = Path(__file__).parent / "outputs/results"

# How many PCs to use as clustering features.
# PC1 + PC2 explains ~80–90% of growth variance and keeps 2D plots intuitive.
N_PCS_FOR_CLUSTERING = 2


def select_features(scores: pd.DataFrame) -> pd.DataFrame:
    """Returns the first N_PCS_FOR_CLUSTERING columns of PCA scores."""
    return scores.iloc[:, :N_PCS_FOR_CLUSTERING]


# ── Stage B: K-Means ─────────────────────────────────────────────────────────

def find_optimal_k(X_cluster: pd.DataFrame,
                   k_range: range = range(2, 8)) -> int:
    """
    Tests K-Means for k = 2..7 using the silhouette score.
    Silhouette measures how well-separated the clusters are (-1 to +1;
    higher is better). We pick the k with the highest score.
    """
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
    """
    Fits K-Means with k clusters.

    Returns
    -------
    dict with:
        model    – fitted KMeans object
        labels   – Series of integer cluster labels (same index as X_cluster)
        centers  – DataFrame of cluster centroids in PC space
    """
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

    # Count months per cluster
    print("\n[K-Means] Months per cluster:")
    print(labels.value_counts().sort_index().to_string())

    return {"model": km, "labels": labels, "centers": centers}


# ── Stage C: GMM ─────────────────────────────────────────────────────────────

def run_gmm(X_cluster: pd.DataFrame, k: int) -> dict:
    """
    Fits a Gaussian Mixture Model with k components.
    GMM generalizes K-Means by fitting elliptical Gaussian distributions
    rather than spherical clusters, and outputs soft probability assignments.

    Returns
    -------
    dict with:
        model        – fitted GaussianMixture object
        labels       – Series of hard-assigned cluster labels (argmax of proba)
        probabilities– DataFrame of per-cluster probabilities for each month
        confidence   – Series of max probability = regime confidence score
    """
    gmm = GaussianMixture(
        n_components=k,
        covariance_type="full",   # Each cluster gets its own covariance matrix
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
    print(f"[GMM] % of months with >80% confidence: "
          f"{(confidence > 0.80).mean():.1%}")

    return {
        "model":         gmm,
        "labels":        labels,
        "probabilities": proba_df,
        "confidence":    confidence,
    }


# ── Regime labelling ──────────────────────────────────────────────────────────

def label_regimes(kmeans_labels: pd.Series,
                  centers: pd.DataFrame) -> pd.Series:
    """
    Assigns human-readable names to K-Means clusters based on their
    PC1 centroid value.

    PC1 is the Growth Momentum index:
        High PC1 → strong growth  → "Expansion"
        Mid  PC1 → moderate growth → "Moderate Growth" / "Slowdown"
        Low  PC1 → weak growth    → "Contraction"

    This mapping is heuristic and may need tuning as you add more pillars.
    """
    # Sort clusters by their PC1 centroid (descending = strongest first)
    # centers.index is like ["Cluster 0", "Cluster 1", ...]
    # kmeans_labels contains integer cluster IDs, so we parse the int from index
    pc1_rank = centers["PC1"].rank(ascending=False).astype(int)
    k = len(centers)

    def assign_name(rank, total):
        if total == 2:
            return {1: "Expansion", 2: "Contraction"}[rank]
        if total == 3:
            return {1: "Expansion", 2: "Slowdown", 3: "Contraction"}[rank]
        if total == 4:
            return {1: "Strong Expansion", 2: "Moderate Growth",
                    3: "Slowdown", 4: "Contraction"}[rank]
        # Generic fallback for k > 4
        return f"Regime {rank} (Strong→Weak)"

    # Key must be int (matching kmeans integer labels), parse from "Cluster N"
    cluster_names = {
        int(cluster_id.split()[-1]): assign_name(rank, k)
        for cluster_id, rank in pc1_rank.items()
    }

    named = kmeans_labels.map(cluster_names).rename("regime")
    # Forward-fill any NaN that can arise if the last row has a new cluster id
    named = named.ffill()
    print("\n[Regimes] Cluster → Regime mapping:")
    for cid, name in cluster_names.items():
        print(f"  Cluster {cid} → {name}")
    return named


# ── Plotting helpers ──────────────────────────────────────────────────────────

CLUSTER_COLORS = ["#2563EB", "#16A34A", "#DC2626", "#D97706", "#7C3AED", "#DB2777"]


def plot_regime_scatter(X_cluster: pd.DataFrame,
                        kmeans_labels: pd.Series,
                        regime_names: pd.Series,
                        gmm_confidence: pd.Series,
                        save: bool = True) -> None:
    """
    2D scatter in PC1–PC2 space, colored by regime.
    Point size = GMM confidence (larger dot = more certain assignment).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    regimes = regime_names.unique()
    palette = {r: CLUSTER_COLORS[i] for i, r in enumerate(sorted(regimes))}

    for ax_idx, (labels, title) in enumerate([
        (regime_names, "K-Means Regimes"),
        (regime_names, "GMM Confidence (dot size)")
    ]):
        ax = axes[ax_idx]
        for regime in sorted(regimes):
            mask = labels == regime
            sizes = (gmm_confidence[mask].values * 80) if ax_idx == 1 else 30
            ax.scatter(
                X_cluster.loc[mask, "PC1"],
                X_cluster.loc[mask, "PC2"],
                c=palette[regime], s=sizes,
                alpha=0.75, label=regime, edgecolors="none"
            )

        # Highlight most recent point
        ax.scatter(X_cluster["PC1"].iloc[-1], X_cluster["PC2"].iloc[-1],
                   c="black", s=120, marker="*", zorder=5, label="Latest")

        ax.set_xlabel("PC1 — Growth Momentum")
        ax.set_ylabel("PC2")
        ax.set_title(title)
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.legend(fontsize=8)

    plt.suptitle("Pillar 1 — Macro Regime Map (PC Space)", fontweight="bold")
    plt.tight_layout()

    if save:
        path = FIGURES_DIR / "regime_scatter.png"
        fig.savefig(path, dpi=150)
        print(f"[Clustering] Regime scatter saved → {path}")
    plt.close()


def plot_regime_timeline(regime_names: pd.Series,
                         gmm_confidence: pd.Series,
                         save: bool = True) -> None:
    """
    Two-panel timeline:
      Top    — Regime classification over time (color-coded bands)
      Bottom — GMM confidence score over time
    """
    regimes = sorted(regime_names.unique())
    palette = {r: CLUSTER_COLORS[i] for i, r in enumerate(regimes)}
    regime_to_int = {r: i for i, r in enumerate(regimes)}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7),
                                    gridspec_kw={"height_ratios": [2, 1]},
                                    sharex=True)

    # ── Top panel: regime bands ───────────────────────────────────────────────
    dates = regime_names.index
    for i in range(len(dates) - 1):
        regime = regime_names.iloc[i]
        ax1.axvspan(dates[i], dates[i + 1],
                    color=palette[regime], alpha=0.6)

    # Legend patches
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=palette[r], label=r) for r in regimes]
    ax1.legend(handles=handles, loc="upper left", fontsize=8)
    ax1.set_ylabel("Macro Regime")
    ax1.set_title("PMG Pillar 1 — Regime Classification Over Time")
    ax1.set_yticks([])

    # ── Bottom panel: confidence ──────────────────────────────────────────────
    ax2.plot(gmm_confidence.index, gmm_confidence.values,
             color="#7C3AED", linewidth=1.2)
    ax2.fill_between(gmm_confidence.index, gmm_confidence.values,
                     0.5, where=(gmm_confidence >= 0.8),
                     alpha=0.3, color="#16A34A", label="High confidence (>80%)")
    ax2.axhline(0.8, color="gray", linestyle="--", linewidth=0.8)
    ax2.axhline(0.5, color="red",  linestyle="--", linewidth=0.8)
    ax2.set_ylabel("GMM Confidence")
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "regime_timeline.png"
        fig.savefig(path, dpi=150)
        print(f"[Clustering] Regime timeline saved → {path}")
    plt.close()


def save_cluster_results(kmeans_labels: pd.Series,
                         regime_names: pd.Series,
                         gmm_results: dict) -> None:
    """Merges all cluster outputs and saves to CSV."""
    out = pd.concat([
        kmeans_labels,
        regime_names,
        gmm_results["labels"].rename("gmm_cluster"),
        gmm_results["confidence"],
        gmm_results["probabilities"],
    ], axis=1)

    path = RESULTS_DIR / "regime_assignments.csv"
    out.to_csv(path)
    print(f"[Clustering] Regime assignments saved → {path}")
    return out
