"""Train-only scaling/PCA, K-Means diagnostics, authoritative GMM regimes.

The PCA and sklearn modeling idioms extend the Spring 2026 prototype. Regime
confidence is now the probability of the very component supplying its label.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler


@dataclass
class RegimeModel:
    seed: int = 42
    variance_target: float = .80
    scale_input: bool = True

    def fit(self, X, semantic=None):
        if len(X) < 36 or X.isna().any().any() or not np.isfinite(X.to_numpy()).all():
            raise ValueError("Model requires >=36 finite complete monthly observations")
        self.columns = X.columns.tolist()
        self.scaler = StandardScaler(with_mean=True, with_std=self.scale_input).fit(X)
        Z = self.scaler.transform(X)
        full = PCA(svd_solver="full").fit(Z)
        self.n_pc = min(X.shape[1], max(2, int(np.searchsorted(full.explained_variance_ratio_.cumsum(), self.variance_target) + 1)))
        self.pca = full
        # Resolve arbitrary PCA signs by largest absolute coefficient.
        for j in range(len(full.components_)):
            if full.components_[j, np.abs(full.components_[j]).argmax()] < 0:
                full.components_[j] *= -1
        scores = full.transform(Z)[:, :self.n_pc]
        names = [f"PC{i+1}" for i in range(len(full.components_))]
        self.loadings = pd.DataFrame(full.components_.T, index=X.columns, columns=names)
        self.variance = pd.DataFrame({"explained": full.explained_variance_ratio_,
                                      "cumulative": full.explained_variance_ratio_.cumsum(),
                                      "retained": np.arange(len(names)) < self.n_pc}, index=names)
        diagnostics, candidates = [], {}
        for k in range(2, 6):
            km = KMeans(n_clusters=k, random_state=self.seed, n_init=10).fit(scores)
            counts = np.bincount(km.labels_, minlength=k)
            stability = []
            for seed in [self.seed+1, self.seed+2]:
                other = KMeans(n_clusters=k, random_state=seed, n_init=5).fit_predict(scores)
                stability.append(adjusted_rand_score(km.labels_, other))
            sil = silhouette_score(scores, km.labels_, sample_size=min(len(scores), 1500), random_state=self.seed)
            valid = counts.min() >= max(6, int(.04 * len(X)))
            diagnostics.append({"k": k, "silhouette": sil, "seed_stability_ari": np.mean(stability),
                                "min_cluster_months": counts.min(), "eligible": valid,
                                "selection_score": sil + .1 * np.mean(stability)})
            candidates[k] = km
        self.diagnostics = pd.DataFrame(diagnostics).set_index("k")
        eligible = self.diagnostics[self.diagnostics.eligible]
        self.selection_warning = None
        if eligible.empty:
            eligible = self.diagnostics
            self.selection_warning = "No candidate met the minimum cluster-size threshold. Inspect diagnostics."
        best = eligible.selection_score.max()
        # Prefer a simpler model when diagnostic scores differ by <=0.02.
        self.k = int(eligible[eligible.selection_score >= best - .02].index.min())
        self.kmeans = candidates[self.k]
        self.diagnostics["selected"] = self.diagnostics.index == self.k
        self.gmm = GaussianMixture(n_components=self.k, covariance_type="full", random_state=self.seed,
                                   n_init=3, max_iter=500, reg_covar=1e-4).fit(scores)
        if not self.gmm.converged_:
            raise ValueError("GMM failed to converge")
        probability = self.gmm.predict_proba(scores)
        semantic = semantic if semantic is not None else pd.DataFrame(Z, index=X.index, columns=X.columns)
        profiles = probability.T @ semantic.to_numpy() / probability.sum(axis=0)[:, None]
        # Names derive directly from GMM profiles; there is no assumed K-Means/GMM correspondence.
        self.order = np.argsort(profiles.mean(axis=1), kind="stable")
        self.names = [f"R{i+1}" for i in range(self.k)]
        self.profiles = pd.DataFrame(profiles[self.order], index=self.names, columns=semantic.columns)
        self.component_map = {int(component): self.names[rank] for rank, component in enumerate(self.order)}
        self.agreement_ari = float(adjusted_rand_score(self.kmeans.labels_, probability.argmax(axis=1)))
        self.density_floor = float(np.quantile(self.gmm.score_samples(scores), .01))
        self.training_end = X.index.max()
        self.training_start = X.index.min()
        self.training_count = len(X)
        self.score_scale = float(np.sqrt(np.var(scores, axis=0, ddof=0).sum()))
        return self

    def scores(self, X):
        X = X.loc[:, self.columns]
        if X.isna().any().any():
            raise ValueError("Cannot score incomplete features")
        return pd.DataFrame(self.pca.transform(self.scaler.transform(X))[:, :self.n_pc], index=X.index,
                            columns=[f"PC{i+1}" for i in range(self.n_pc)])

    def predict(self, X):
        scores = self.scores(X)
        proba = self.gmm.predict_proba(scores.to_numpy())[:, self.order]
        pred = proba.argmax(axis=1)
        out = pd.DataFrame({"regime": [self.names[i] for i in pred],
                            "confidence": proba.max(axis=1),
                            "kmeans_cluster": self.kmeans.predict(scores.to_numpy()),
                            "entropy": -(proba * np.log(proba.clip(1e-15))).sum(axis=1) / np.log(self.k)}, index=X.index)
        for i, name in enumerate(self.names):
            out[f"probability_{name}"] = proba[:, i]
        out["log_density"] = self.gmm.score_samples(scores.to_numpy())
        out["out_of_distribution"] = out.log_density < self.density_floor
        return out

    def standardized(self, X):
        return pd.DataFrame(self.scaler.transform(X[self.columns]), index=X.index, columns=self.columns)

    def interpretation(self):
        result = {}
        for c in self.loadings.columns[:self.n_pc]:
            v = self.loadings[c]
            top = v.abs().nlargest(3).index
            result[c] = "; ".join(f"{name}: {v[name]:+.3f}" for name in top)
        return result


def combine(models, panels):
    """Each pillar block contributes total training variance 1; preserve its PCs.

    Do not standardize these columns again in the composite fit, which would
    overweight pillars retaining more components.
    """
    blocks = []
    for n, model in models.items():
        scores = model.scores(panels[n]) / model.score_scale
        blocks.append(scores.add_prefix(f"pillar_{n}_"))
    return pd.concat(blocks, axis=1, join="inner").dropna()


def semantic_signals(models, panels):
    frames = {}
    for n, model in models.items():
        z = model.standardized(panels[n])
        frames[f"pillar_{n}"] = z.mean(axis=1)
    return pd.DataFrame(frames).dropna()
