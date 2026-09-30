"""Monthly panels in raw units; transformations are backward looking."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import load_cache, validate_series
from .registry import BY_CODE, MARKET_CORE


def completed_month(as_of=None):
    # Date-only cutoff: exclude its entire calendar month, including month-end.
    date = pd.Timestamp(as_of or pd.Timestamp.now().date())
    return date.to_period("M").start_time - pd.Timedelta(days=1)


def monthly(s, frequency, cutoff, market=False):
    s = s.loc[s.index <= pd.Timestamp(cutoff)]
    if s.empty:
        return s
    if frequency == "quarterly":
        # A labelled quarterly survey observation may be held for exactly two more
        # months. No extrapolation beyond its quarter; decision lags applied later.
        s = s.copy()
        s.index = s.index.to_period("M").to_timestamp("M")
        idx = pd.date_range(s.index.min(), min(s.index.max() + pd.offsets.MonthEnd(2), cutoff), freq="ME")
        return s.reindex(idx).ffill(limit=2)
    res = s.resample("ME").last() if market else s.resample("ME").mean()
    count = s.resample("ME").count()
    if frequency == "daily":
        # Holiday calendars vary: require >= 70% of generic business days.
        expected = pd.Series([len(pd.bdate_range(d.to_period('M').start_time, d)) for d in res.index], index=res.index)
        res = res.where(count >= expected * .7)
    if frequency == "weekly":
        res = res.where(count >= 3)
    return res.loc[:cutoff]


def pct(s, periods=12):
    # Calendar monthly reindexing happens before this call; never fill gaps.
    return s.pct_change(periods, fill_method=None) * 100


def transform_pillar(n, raw):
    from pillar_1.features import build as growth
    from pillar_2.features import build as financial
    from pillar_3.features import build as inflation
    from pillar_4.features import build as market
    f, lags = {1: growth, 2: financial, 3: inflation, 4: market}[n](raw)
    return pd.DataFrame(f, index=raw.index).replace([np.inf, -np.inf], np.nan), lags


def decision_panel(features, lags):
    # Shift each feature's observation month to a conservative availability month.
    # This approximates release delays, not historical data vintages.
    frames = []
    for code in features:
        s = features[code].copy()
        s.index = s.index + pd.offsets.MonthEnd(lags[code])
        frames.append(s.rename(code))
    return pd.concat(frames, axis=1).sort_index()


def prepare(root=Path("."), as_of=None, include_ism=False, cache_override=None, write=True):
    root = Path(root)
    cutoff = completed_month(as_of)
    cache = load_cache(root) if cache_override is None else cache_override
    panel = {}
    for code, s in cache.items():
        spec = BY_CODE.get(code)
        panel[code] = monthly(s, spec.frequency if spec else "daily", cutoff, market=spec is None)
    if include_ism:
        for code in ["ISM_MANUFACTURING", "ISM_SERVICES"]:
            p = root / "data/raw/local" / (code + ".csv")
            df = pd.read_csv(p, index_col="date", parse_dates=True)
            panel[code] = monthly(validate_series(df["value"].rename(code)), "monthly", cutoff)
    all_monthly = pd.DataFrame(panel).sort_index()
    if all_monthly.empty:
        raise ValueError("No raw observations. Run python update_data.py first.")
    all_monthly = all_monthly.reindex(pd.date_range(all_monthly.index.min(), cutoff, freq="ME"))
    all_monthly.index.name = "date"
    if {"PCE", "PCEPI"} <= set(all_monthly):
        all_monthly["REAL_PCE"] = 100 * all_monthly.PCE / all_monthly.PCEPI
    dest = root / "data/processed" / (str(pd.Timestamp(as_of).date()) if as_of else "latest")
    if write:
        dest.mkdir(parents=True, exist_ok=True)
        all_monthly.to_csv(dest / "monthly_observations.csv")
    pillars, failures = {}, {}
    required = {1: ["INDPRO", "RSAFS", "PAYEMS", "REAL_PCE"], 2: ["BAA10Y", "T10Y2Y", "NFCI", "DRTSCILM"],
                3: ["CPIAUCSL", "CPILFESL", "PPIACO", "FEDFUNDS", "T5YIE", "GS10"], 4: [*MARKET_CORE, "VIXCLS"]}
    for n, cols in required.items():
        missing = [c for c in cols if c not in all_monthly or all_monthly[c].dropna().empty]
        if missing:
            failures[n] = "Missing required inputs: " + ", ".join(missing)
            continue
        if n == 1 and include_ism:
            cols += ["ISM_MANUFACTURING", "ISM_SERVICES"]
        raw = all_monthly[cols].dropna(how="all")
        features, lags = transform_pillar(n, raw)
        available = decision_panel(features, lags).loc[:cutoff]
        if write:
            raw.dropna().to_csv(dest / f"pillar_{n}_monthly.csv")
            features.dropna().to_csv(dest / f"pillar_{n}_features.csv")
            available.to_csv(dest / f"pillar_{n}_available_features.csv")
        pillars[n] = {"raw": raw, "features": features, "available": available, "lags": lags}
    validation = {"cutoff": str(cutoff.date()), "failures": failures,
        "missing_fraction": all_monthly.isna().mean().to_dict(),
        "policy": "No monthly/daily forward filling. Quarterly survey hold is bounded to 2 months; availability lags are explicit."}
    if write:
        (dest / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    return pillars, all_monthly, failures
