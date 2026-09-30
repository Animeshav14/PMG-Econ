"""Orchestration, reporting, and expanding-window historical diagnostics."""
import json
import platform
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from .registry import PILLARS, SECTORS, BY_CODE
from .transforms import prepare, completed_month
from .model import RegimeModel, combine, semantic_signals
from .sectors import historical_associations, sector_statistics
from .plots import model_figures, heatmap


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False, default=str), encoding="utf-8")


def reading(model, X, name):
    row = model.predict(X.tail(1)).iloc[0]
    profile = model.profiles.loc[row.regime]
    strongest = profile.abs().nlargest(min(3, len(profile))).index
    return {"name": name, "model_month": str(X.index[-1].date()), "regime": row.regime,
            "confidence": float(row.confidence), "entropy": float(row.entropy),
            "out_of_distribution": bool(row.out_of_distribution), "log_density": float(row.log_density),
            "probabilities": {n: float(row[f'probability_{n}']) for n in model.names},
            "latest_raw_features": X.iloc[-1].to_dict(),
            "regime_profile": profile.to_dict(),
            "interpretation": "; ".join(f"{c} {profile[c]:+.2f} relative to training mean" for c in strongest),
            "training_start": str(model.training_start.date()), "training_end": str(model.training_end.date()),
            "n_months": model.training_count, "retained_pcs": model.n_pc,
            "missing_calendar_months_in_sample": len(pd.date_range(X.index.min(), X.index.max(), freq="ME")) - len(X),
            "retained_variance": float(model.variance.explained.iloc[:model.n_pc].sum()),
            "k": model.k, "warning": model.selection_warning,
            "confidence_definition": "GMM posterior membership of the reported regime; uncalibrated, not a probability of future returns or recession"}


def save_model(root, key, model, X, name, make_plots=True):
    out = root / "tables" / key
    out.mkdir(parents=True, exist_ok=True)
    assignments = model.predict(X)
    for filename, frame in {"features": X, "standardized_features": model.standardized(X), "pca_scores": model.scores(X),
                            "pca_loadings": model.loadings, "explained_variance": model.variance,
                            "clustering_diagnostics": model.diagnostics, "regime_assignments": assignments,
                            "regime_profiles": model.profiles}.items():
        frame.to_csv(out / (filename + ".csv"), index_label="date" if isinstance(frame.index, pd.DatetimeIndex) else None)
    latest = reading(model, X, name)
    write_json(out / "latest.json", latest)
    write_json(out / "method.json", {"component_to_regime": model.component_map, "pca_interpretation": model.interpretation(),
                                     "kmeans_gmm_agreement_ari": model.agreement_ari,
                                     "label_authority": "GMM", "selection": "max silhouette + 0.1 seed ARI, min cluster >= max(6,4% sample); prefer lower k within .02"})
    if make_plots:
        model_figures(model, X, assignments, root / "figures" / key, name)
    return assignments, latest


def freshness(root, as_of):
    manifest = json.loads((root / "data/raw/manifest.json").read_text(encoding="utf-8"))
    rows = []
    as_of = pd.Timestamp(as_of or pd.Timestamp.now().date())
    for r in manifest["series"]:
        row = dict(r)
        if r.get("latest_observation"):
            age = (as_of - pd.Timestamp(r["latest_observation"])).days
            threshold = {"daily": 7, "weekly": 21, "monthly": 100, "quarterly": 210}[r["frequency"]]
            row.update(age_days=age, stale=age > threshold, lagged=age > 7)
        rows.append(row)
    return manifest, pd.DataFrame(rows)


def run(root=Path("."), as_of=None, plots=True, include_ism=False):
    root = Path(root)
    output = root / "outputs" / ("as_of/" + str(pd.Timestamp(as_of).date()) if as_of else "")
    output.mkdir(parents=True, exist_ok=True)
    pillars, monthly, failures = prepare(root, as_of, include_ism)
    manifest, fresh = freshness(root, as_of)
    (output / "tables").mkdir(exist_ok=True)
    fresh.to_csv(output / "tables/data_coverage.csv", index=False)
    state = {"schema_version": 1, "as_of": str(pd.Timestamp(as_of or pd.Timestamp.now().date()).date()),
             "run_at": datetime.now(timezone.utc).isoformat(), "retrieved_at": manifest["retrieved_at"],
             "data_snapshot": manifest["snapshot"], "mode": "descriptive_current_vintage",
             "release_policy": "Completed months only; no monthly forward fill. Descriptive dates are observation months.",
             "failures": failures, "series_failed": fresh.loc[fresh.status != "ok", "code"].tolist(),
             "series_stale": fresh.loc[fresh.get("stale", False) == True, "code"].tolist(),
             "series_lagged": fresh.loc[fresh.get("lagged", False) == True, "code"].tolist(),
             "limitations": ["Current revised macro vintages; not an historical real-time information set.",
                             "Posterior confidence is not calibrated predictive accuracy.",
                             "Sector results are associations, not allocation recommendations."]}
    print("Retrieved:", manifest["retrieved_at"])
    print(fresh[["code", "latest_observation", "status", "stale"]].to_string(index=False))
    models, panels = {}, {}
    with threadpool_limits(limits=1):
        for n, inputs in pillars.items():
            X = inputs["features"].dropna()
            try:
                model = RegimeModel().fit(X)
                models[n], panels[n] = model, X
                _, state[f"pillar_{n}"] = save_model(output, f"pillar_{n}", model, X, PILLARS[n], plots)
                print(f"Pillar {n}: {X.index[-1]:%Y-%m}, {state[f'pillar_{n}']['regime']}, p={state[f'pillar_{n}']['confidence']:.1%}")
            except ValueError as exc:
                failures[n] = str(exc)
        if len(models) == 4:
            # Refit pillar blocks over the SAME common sample so each block has
            # exactly equal total training variance in the composite.
            common = panels[1].index
            for X in panels.values():
                common = common.intersection(X.index)
            block_panels = {n: X.loc[common] for n, X in panels.items()}
            block_models = {n: RegimeModel().fit(X) for n, X in block_panels.items()}
            factors = combine(block_models, block_panels)
            semantic = semantic_signals(block_models, block_panels)
            composite = RegimeModel(scale_input=False).fit(factors, semantic)
            assignments, latest = save_model(output, "composite", composite, factors, "PMG Macro Landscape Map", plots)
            # Persist common-sample block loadings; independent pillar loadings
            # above use their longer histories and must not be substituted here.
            for n, m in block_models.items():
                m.loadings.to_csv(output / "tables/composite" / f"pillar_{n}_block_loadings.csv")
            factors.to_csv(output / "tables/composite/factor_panel.csv")
            semantic.to_csv(output / "tables/composite/pillar_signals.csv")
            state["composite_regime"] = latest
            state["latest_usable_model_month"] = latest["model_month"]
            stats, current = historical_associations(monthly, assignments, latest["regime"])
            stats.to_csv(output / "tables/sector_history.csv", index=False)
            current.to_csv(output / "tables/current_sector_history.csv", index=False)
            state["sector_history"] = {"return_type": "Yahoo adjusted-price returns (dividend/split adjusted), not an audited total-return index",
                                       "benchmark": "IVV", "alignment": "same observation month; full-sample descriptive",
                                       "positive_month_definition": "Adjusted monthly return > 0",
                                       "beat_benchmark_definition": "Adjusted monthly return > IVV in same month",
                                       "sectors": json.loads(current.to_json(orient="records"))}
            if plots:
                heatmap(current, output / "figures/sector_allocation_heatmap.png", latest["regime"], latest["model_month"])
            print("Composite:", latest["model_month"], latest["regime"], f"p={latest['confidence']:.1%}")
        else:
            state["composite_regime"] = {"status": "unavailable", "reason": "Requires four operational pillars"}
    write_json(output / "latest/current_state.json", state)
    if failures:
        raise RuntimeError(f"Partial run saved; missing/failed pillars: {failures}")
    return state


def one_step(panels, date, min_train=48):
    date = pd.Timestamp(date)
    common = panels[1].dropna().index
    for X in panels.values():
        common = common.intersection(X.dropna().index)
    train_dates = common[common < date]
    if len(train_dates) < min_train or date not in common:
        return None
    train = {n: X.loc[train_dates] for n, X in panels.items()}
    current = {n: X.loc[[date]] for n, X in panels.items()}
    models = {n: RegimeModel().fit(X) for n, X in train.items()}
    factors = combine(models, train)
    now = combine(models, current)
    sem = semantic_signals(models, train)
    model = RegimeModel(scale_input=False).fit(factors, sem)
    pred = model.predict(now).iloc[0]
    z = semantic_signals(models, current).iloc[0]
    row = {"date": date, "train_end": train_dates.max(), "train_months": len(train_dates),
           "regime_within_fit": pred.regime, "confidence": pred.confidence, "k": model.k,
           "out_of_distribution": bool(pred.out_of_distribution),
           "state_bucket": "/".join(f"{letter}{'+' if z[f'pillar_{n}'] >= 0 else '-'}" for n, letter in enumerate("GSIM", 1))}
    for n in range(1, 5):
        p = models[n].predict(current[n]).iloc[0]
        row.update({f"pillar_{n}_signal": z[f"pillar_{n}"], f"pillar_{n}_regime_within_fit": p.regime,
                    f"pillar_{n}_confidence": p.confidence, f"pillar_{n}_out_of_distribution": bool(p.out_of_distribution)})
    row["stress_alert"] = bool(z.pillar_2 > sem.pillar_2.quantile(.8))
    row["defensive_alert"] = bool(z.pillar_4 < sem.pillar_4.quantile(.2))
    row["weak_growth_alert"] = bool(z.pillar_1 < sem.pillar_1.quantile(.2))
    return row


def backtest(root=Path("."), as_of=None, start="2006-01-01", min_train=48):
    root = Path(root)
    pillars, monthly, failures = prepare(root, as_of)
    if failures:
        raise ValueError(failures)
    panels = {n: p["available"] for n, p in pillars.items()}
    common = panels[1].dropna().index
    for X in panels.values():
        common = common.intersection(X.dropna().index)
    dates = common[(common >= pd.Timestamp(start)) & (common <= completed_month(as_of))]
    out = root / "outputs" / ("as_of/" + str(pd.Timestamp(as_of).date()) if as_of else "") / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with threadpool_limits(limits=1):
        for i, date in enumerate(dates):
            row = one_step(panels, date, min_train)
            if row is not None:
                rows.append(row)
            if i % 12 == 0:
                print(f"Expanding diagnostic {date:%Y-%m}: {len(rows)} predictions", flush=True)
    if not rows:
        raise ValueError("No eligible test months after training warmup")
    history = pd.DataFrame(rows).set_index("date")
    history.to_csv(out / "expanding_assignments.csv")
    # Cross-fit GMM labels are local identifiers, never pooled as identical states.
    stats = sector_statistics(monthly, history.state_bucket, forward=True)
    stats.to_csv(out / "next_month_sector_history.csv", index=False)
    episodes = episode_report(history, monthly)
    episodes.to_csv(out / "episodes.csv", index=False)
    write_json(out / "method.json", {"mode": "expanding_current_vintage_with_release_lags",
        "true_realtime": False, "revision_bias": "Uses current revised macro data, so results cannot establish historical tradability or predictive accuracy.",
        "fit_policy": "All scaling, PCA, k selection and GMM fits use strictly earlier monthly rows; current month is held out.",
        "min_training_months": min_train, "common_start": str(common.min().date()),
        "first_prediction": str(history.index.min().date()), "last_prediction": str(history.index.max().date()),
        "sector_alignment": "State at decision month t versus adjusted return in t+1; 16 sign buckets avoid pooling changing GMM IDs.",
        "signal_thresholds": "Stress > prior 80th percentile; market/growth < prior 20th percentile. Exploratory; not optimized."})
    plot_episodes(history, out)
    return history, episodes


def episode_report(history, monthly):
    episodes = [("2008 cycle", "2007-12-31", "2009-06-30"), ("2020 cycle", "2020-02-29", "2020-04-30"),
                ("2011 slowdown", "2011-07-31", "2011-12-31"), ("2015-16 slowdown", "2015-08-31", "2016-03-31"),
                ("2022 tightening", "2022-01-31", "2022-12-31")]
    rows = []
    for name, onset, end in episodes:
        onset = pd.Timestamp(onset)
        before = history.loc[onset-pd.offsets.MonthEnd(6):onset-pd.offsets.MonthEnd(1)]
        during = history.loc[onset:end]
        row = {"episode": name, "onset": str(onset.date()), "pre_months_available": len(before), "episode_months_available": len(during)}
        for signal in ["stress_alert", "defensive_alert", "weak_growth_alert"]:
            hits = before.index[before[signal]]
            row[signal+"_pre_count"] = len(hits)
            row[signal+"_first_pre_month"] = str(hits.min().date()) if len(hits) else None
            row[signal+"_during_fraction"] = float(during[signal].mean()) if len(during) else None
        row["assessment"] = "Insufficient six-month prehistory" if len(before) < 6 else "No advance stress/rotation warning" if row["stress_alert_pre_count"] == 0 and row["defensive_alert_pre_count"] == 0 else "Advance alert present; inspect persistence and false positives"
        rows.append(row)
    # Retrospective USREC evaluates false alarms; it never enters a feature fit.
    if "USREC" in monthly:
        rec = monthly.USREC.reindex(history.index)
        future6 = pd.concat([monthly.USREC.shift(-i).reindex(history.index) for i in range(7)], axis=1)
        eligible = future6.notna().all(axis=1)
        quiet = future6.max(axis=1) == 0
        for signal in ["stress_alert", "defensive_alert", "weak_growth_alert"]:
            alert = history[signal] & eligible
            rows.append({"episode": f"Full history {signal}", "episode_months_available": int(eligible.sum()),
                         "alerts": int(alert.sum()), "alerts_without_recession_within_6m": int((alert & quiet).sum()),
                         "assessment": "Retrospective false-alarm count; missing future six months excluded"})
    return pd.DataFrame(rows)


def plot_episodes(history, out):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True, layout="constrained")
    for n, ax in enumerate(axes, 1):
        ax.plot(history.index, history[f"pillar_{n}_signal"], color="#2364aa", lw=1)
        for start, end in [("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30")]:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="gray", alpha=.2)
        ax.axhline(0, color="gray", ls="--", lw=.6)
        ax.set_ylabel(PILLARS[n], fontsize=9)
    mode = "archived macro vintages" if "vintage_backtest" in str(out) else "current revised data"
    axes[0].set_title(f"Expanding-window diagnostics | {mode}, explicit release lags\nShading: 2008 and 2020 recessions; signals use training-only standardization")
    fig.savefig(out / "historical_signals.png", dpi=150)
    plt.close(fig)
