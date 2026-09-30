import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits
from src.data import read_fred_csv, fetch_fred, validate_series
from src.transforms import monthly, pct, decision_panel, completed_month, transform_pillar
from src.model import RegimeModel, combine
from src.sectors import sector_statistics
from src.engine import one_step, run, freshness


@pytest.fixture(autouse=True)
def single_thread():
    with threadpool_limits(limits=1):
        yield


@pytest.fixture
def panels():
    rng = np.random.default_rng(18)
    idx = pd.date_range("2000-01-31", periods=100, freq="ME")
    return {n: pd.DataFrame(rng.normal(size=(100, 4)) + np.repeat([-1.5, 1.5], 50)[:, None],
                            index=idx, columns=[f"x{j}" for j in range(4)]) for n in range(1, 5)}


def test_fred_columns_missing_and_duplicates():
    s = read_fred_csv("observation_date,INDPRO\n2000-01-01,1\n2000-02-01,.\n", "INDPRO")
    assert len(s) == 2 and s.isna().sum() == 1
    with pytest.raises(ValueError, match="columns"):
        read_fred_csv("date,wrong\n2000-01-01,1", "INDPRO")
    with pytest.raises(ValueError, match="Duplicate"):
        read_fred_csv("DATE,INDPRO\n2000-01-01,1\n2000-01-01,2", "INDPRO")


def test_fred_keyless_official_endpoint(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    class Response:
        text = "observation_date,INDPRO\n2000-01-01,1\n"
        def raise_for_status(self):
            pass
    class Session:
        def get(self, url, **kwargs):
            assert url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO")
            return Response()
    s, raw, url, ext = fetch_fred("INDPRO", Session())
    assert s.iloc[0] == 1 and ext == ".csv" and "observation_date" in raw


def test_backward_growth_and_no_fill():
    s = pd.Series(np.arange(100., 125.), index=pd.date_range("2000-01-31", periods=25, freq="ME"))
    change = pct(s)
    assert change.iloc[12] == pytest.approx(12)
    assert change.iloc[:12].isna().all()
    modified = s.copy()
    modified.iloc[20:] *= 50
    pd.testing.assert_series_equal(pct(s).iloc[:20], pct(modified).iloc[:20])
    s.iloc[15] = np.nan
    assert pd.isna(pct(s, 1).iloc[16])


def test_monthly_conversion_and_incomplete_month():
    s = pd.Series(2., index=pd.bdate_range("2020-01-01", "2020-03-10"))
    m = monthly(s, "daily", pd.Timestamp("2020-03-31"))
    assert m.iloc[0] == 2 and pd.isna(m.iloc[-1])
    assert completed_month("2020-03-31") == pd.Timestamp("2020-02-29")
    q = pd.Series([10., 20.], index=pd.to_datetime(["2020-01-01", "2020-07-01"]))
    qm = monthly(q, "quarterly", pd.Timestamp("2020-12-31"))
    assert qm.loc["2020-03-31"] == 10 and pd.isna(qm.loc["2020-04-30"])
    assert qm.index.max() == pd.Timestamp("2020-09-30")


def test_availability_never_backfills():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    p = decision_panel(pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}, index=idx), {"a": 2, "b": 0})
    assert pd.isna(p.loc["2020-01-31", "a"]) and p.loc["2020-03-31", "a"] == 1


def test_pca_deterministic_gmm_authority(panels):
    X = panels[1]
    a, b = RegimeModel().fit(X), RegimeModel().fit(X)
    assert a.scores(X).shape == (len(X), a.n_pc)
    assert a.variance.explained.sum() == pytest.approx(1)
    pd.testing.assert_frame_equal(a.predict(X), b.predict(X))
    pred = a.predict(X)
    prob = pred[["probability_" + n for n in a.names]]
    assert np.allclose(prob.sum(axis=1), 1)
    assert np.allclose(prob.max(axis=1), pred.confidence)
    assert (prob.idxmax(axis=1).str.replace("probability_", "") == pred.regime).all()
    # A permutation of unrelated K-Means IDs cannot change authoritative names.
    a.kmeans.cluster_centers_ = a.kmeans.cluster_centers_[::-1].copy()
    pd.testing.assert_series_equal(a.predict(X).regime, pred.regime)


def test_composite_equal_block_variance(panels):
    models = {n: RegimeModel().fit(X) for n, X in panels.items()}
    factors = combine(models, panels)
    assert len(factors) == 100
    for n in range(1, 5):
        assert factors.filter(like=f"pillar_{n}_").var(ddof=0).sum() == pytest.approx(1)


def test_asof_training_excludes_future(panels):
    date = panels[1].index[75]
    first = one_step(panels, date)
    changed = {n: X.copy() for n, X in panels.items()}
    for X in changed.values():
        X.loc[X.index > date] = 99999
    second = one_step(changed, date)
    for key in first:
        if isinstance(first[key], (float, np.floating)):
            assert first[key] == pytest.approx(second[key], abs=1e-12)
        else:
            assert first[key] == second[key]
    assert first["train_end"] < date


def test_sector_forward_alignment_no_preinception():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    prices = pd.DataFrame({"IVV": [100, 100, 100, 100], "XLK": [100, 110, 99, 99],
                           "XLC": [np.nan, np.nan, 100, 120]}, index=idx)
    regimes = pd.Series(["A", "B", "C", "D"], index=idx)
    s = sector_statistics(prices, regimes, forward=True).set_index(["regime", "ticker"])
    assert s.loc[("A", "XLK"), "mean_monthly_return"] == pytest.approx(.1)
    assert s.loc[("B", "XLK"), "mean_monthly_return"] == pytest.approx(-.1)
    assert ("A", "XLC") not in s.index
    assert s.loc[("C", "XLC"), "n"] == 1


def test_stale_reporting(tmp_path):
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    (raw / "manifest.json").write_text(json.dumps({"series": [{"code": "X", "frequency": "daily", "latest_observation": "2020-01-01"}]}))
    _, f = freshness(tmp_path, "2020-03-01")
    assert bool(f.stale.iloc[0])


def test_final_composite_output(tmp_path, panels, monkeypatch):
    import src.engine as e
    from src.registry import SECTORS
    idx = panels[1].index
    monthly_prices = pd.DataFrame({c: 100 * np.exp(np.arange(len(idx)) * .01) for c in ["IVV", *SECTORS]}, index=idx)
    monkeypatch.setattr(e, "prepare", lambda *a: ({n: {"features": X} for n, X in panels.items()}, monthly_prices, {}))
    meta = {"retrieved_at": "2020-01-01T00:00:00Z", "snapshot": "test"}
    f = pd.DataFrame([{"code": "X", "status": "ok", "latest_observation": "2020-01-01", "stale": False, "lagged": False}])
    monkeypatch.setattr(e, "freshness", lambda *a: (meta, f))
    state = run(tmp_path, plots=False)
    assert all(f"pillar_{n}" in state for n in range(1, 5))
    assert len(state["sector_history"]["sectors"]) == 11
    assert sum(state["composite_regime"]["probabilities"].values()) == pytest.approx(1)
    assert (tmp_path / "outputs/latest/current_state.json").exists()


def test_rejects_nonfinite_and_missing_model_input(panels):
    x = panels[1].copy()
    x.iloc[5, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        RegimeModel().fit(x)
    with pytest.raises(ValueError, match="Nonfinite"):
        validate_series(pd.Series([1, np.inf], index=pd.date_range("2000-01-01", periods=2)))


def test_vintage_parser_rejects_silent_current_data():
    from src.vintages import parse_vintage
    s = parse_vintage("observation_date,CPIAUCSL_20200229\n2020-01-01,100", "CPIAUCSL", "2020-02-29")
    assert s.iloc[0] == 100
    with pytest.raises(ValueError, match="Rejected"):
        parse_vintage("observation_date,CPIAUCSL_20260929\n2020-01-01,100", "CPIAUCSL", "2020-02-29")
    with pytest.raises(ValueError, match="after"):
        parse_vintage("observation_date,CPIAUCSL_20200229\n2020-03-01,100", "CPIAUCSL", "2020-02-29")


def test_out_of_distribution_is_separate_from_confidence(panels):
    model = RegimeModel().fit(panels[1])
    extreme = panels[1].tail(1).copy() + 1000
    assert bool(model.predict(extreme).out_of_distribution.iloc[0])


def test_prepare_asof_uses_only_completed_observations(tmp_path):
    from src.transforms import prepare
    from src.registry import FRED, MARKET
    idx = pd.date_range("1999-01-31", "2021-12-31", freq="ME")
    cache = {}
    for spec in FRED:
        freq = {"monthly": "MS", "quarterly": "QS", "weekly": "W-FRI", "daily": "B"}[spec.frequency]
        dates = pd.date_range("1999-01-01", "2021-12-31", freq=freq)
        cache[spec.code] = pd.Series(100 + np.arange(len(dates)) * .01, index=dates, name=spec.code)
    for c in MARKET:
        dates = pd.bdate_range("1999-01-01", "2021-12-31")
        cache[c] = pd.Series(100 + np.arange(len(dates)) * .01, index=dates, name=c)
    panels, monthly_data, failures = prepare(tmp_path, "2020-03-15", cache_override=cache, write=False)
    assert not failures and len(panels) == 4
    assert monthly_data.index.max() == pd.Timestamp("2020-02-29")
    for s in cache.values():
        s.loc[s.index >= "2020-03-01"] = 999999
    _, changed, _ = prepare(tmp_path, "2020-03-15", cache_override=cache, write=False)
    pd.testing.assert_frame_equal(monthly_data, changed)
