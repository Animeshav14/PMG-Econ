"""Meeting-ready research figures; maps show conditional 2D slices."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

COLORS = ["#2364aa", "#e5a33a", "#388977", "#a55384", "#ac473e"]


def model_figures(model, X, assignments, folder, title):
    folder.mkdir(parents=True, exist_ok=True)
    scores = model.scores(X)
    cmap = ListedColormap(COLORS[:model.k])
    latest = assignments.iloc[-1]
    fig, ax = plt.subplots(figsize=(11, 7), layout="constrained")
    bounds = [(scores[c].min() - .5, scores[c].max() + .5) for c in scores.columns[:2]]
    gx, gy = np.meshgrid(np.linspace(*bounds[0], 150), np.linspace(*bounds[1], 150))
    grid = np.tile(scores.iloc[-1].to_numpy(), (gx.size, 1))
    grid[:, 0], grid[:, 1] = gx.ravel(), gy.ravel()
    regions = model.gmm.predict_proba(grid)[:, model.order].argmax(axis=1).reshape(gx.shape)
    ax.contourf(gx, gy, regions, levels=np.arange(model.k+1)-.5, cmap=cmap, alpha=.13)
    for i, name in enumerate(model.names):
        sel = assignments.regime == name
        ax.scatter(scores.loc[sel, "PC1"], scores.loc[sel, "PC2"], s=15, color=COLORS[i], alpha=.65, label=f"{name} ({sel.sum()} months)")
    ax.scatter(*scores.iloc[-1, :2], marker="*", s=240, color="#142536", edgecolors="white", zorder=5,
               label=f"Latest: {X.index[-1]:%b %Y}, {latest.regime}, p={latest.confidence:.1%}")
    ax.set(xlabel=f"PC1 ({model.variance.explained.iloc[0]:.0%} variance)", ylabel=f"PC2 ({model.variance.explained.iloc[1]:.0%} variance)",
           title=title + "\nFull-sample descriptive regimes")
    ax.legend(fontsize=9, loc="best")
    fig.text(.5, -.025, "Regions: 2D slice at latest values of other PCs. Confidence is model membership, not a forecast probability.", ha="center", fontsize=9)
    fig.savefig(folder / "regime_map.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 5), sharex=True, layout="constrained")
    number = assignments.regime.map({n: i for i, n in enumerate(model.names)})
    axes[0].scatter(assignments.index, number, c=number, cmap=cmap, vmin=0, vmax=model.k-1, marker="s", s=14)
    axes[0].set(yticks=range(model.k), yticklabels=model.names, title=title + " | descriptive timeline")
    axes[1].plot(assignments.index, assignments.confidence, color="#2364aa", lw=1)
    axes[1].set(ylabel="GMM membership", ylim=(0, 1.05))
    fig.savefig(folder / "regime_timeline.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, max(4, len(model.columns)*.35)), layout="constrained")
    axes[0].bar(model.variance.index, model.variance.explained, color="#2364aa")
    axes[0].plot(model.variance.index, model.variance.cumulative, marker="o", color="#ac473e")
    axes[0].axhline(.8, color="gray", ls="--", lw=.8)
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set(title=f"Variance; {model.n_pc} PCs retained", ylim=(0, 1.08))
    load = model.loadings.iloc[:, :model.n_pc]
    im = axes[1].imshow(load, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    axes[1].set(yticks=range(len(load)), yticklabels=load.index, xticks=range(load.shape[1]), xticklabels=load.columns, title="PCA coefficients")
    fig.colorbar(im, ax=axes[1], shrink=.6)
    fig.savefig(folder / "pca_diagnostics.png", dpi=150)
    plt.close(fig)


def heatmap(table, path, regime, month):
    fields = ["mean_monthly_return", "median_monthly_return", "monthly_volatility", "mean_excess_vs_IVV", "positive_month_fraction"]
    labels = ["Mean return", "Median return", "Volatility", "Excess vs IVV", "Positive months"]
    table = table.sort_values("mean_excess_vs_IVV", ascending=False, na_position="last")
    values = table[fields].to_numpy() * 100
    colors = values.copy()
    for j in range(colors.shape[1]):
        finite = colors[:, j][np.isfinite(colors[:, j])]
        if len(finite):
            colors[:, j] = (colors[:, j] - np.median(finite)) / max(np.std(finite), .001)
    colors[:, 2] *= -1
    fig, ax = plt.subplots(figsize=(11, 7), layout="constrained")
    ax.imshow(np.ma.masked_invalid(colors), cmap="RdBu", vmin=-2, vmax=2, aspect="auto")
    for i in range(len(table)):
        for j in range(len(fields)):
            ax.text(j, i, f"{values[i,j]:.2f}%" if np.isfinite(values[i,j]) else "N/A", ha="center", va="center", fontsize=10,
                    color="white" if abs(colors[i,j]) > 1.25 else "black")
    ax.set(xticks=range(len(fields)), xticklabels=labels, yticks=range(len(table)),
           yticklabels=[f"{r.ticker}  {r.sector}  (n={r.n})" for r in table.itertuples()],
           title=f"Sector Allocation Heatmap | {month} | {regime}\nHistorical same-month associations; adjusted-price returns")
    fig.text(.5, -.035, "Colors are relative within each column; lower volatility is blue. n<24 is a small sample. No allocation rule is implied.", ha="center", fontsize=9)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
