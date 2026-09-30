"""Historical sector associations, with explicit forward-return alignment."""
import numpy as np
import pandas as pd
from .registry import SECTORS


def monthly_returns(prices):
    prices = prices.reindex(pd.date_range(prices.index.min(), prices.index.max(), freq="ME"))
    return prices.pct_change(fill_method=None)


def sector_statistics(prices, regimes, forward=False):
    returns = monthly_returns(prices)
    if "IVV" not in returns:
        raise ValueError("IVV benchmark missing")
    if forward:
        returns = returns.shift(-1)  # regime at t, subsequent full-month return t+1
    rows = []
    for ticker, sector in SECTORS.items():
        if ticker not in returns:
            continue
        frame = pd.concat([regimes.rename("regime"), returns[ticker].rename("return"), returns.IVV.rename("benchmark")], axis=1).dropna()
        for regime, g in frame.groupby("regime"):
            excess = g["return"] - g.benchmark
            rows.append({"regime": regime, "ticker": ticker, "sector": sector, "n": len(g),
                         "first_month": str(g.index.min().date()), "last_month": str(g.index.max().date()),
                         "mean_monthly_return": g["return"].mean(), "median_monthly_return": g["return"].median(),
                         "monthly_volatility": g["return"].std(ddof=1), "positive_month_fraction": (g["return"] > 0).mean(),
                         "mean_excess_vs_IVV": excess.mean(), "excess_monthly_volatility": excess.std(ddof=1),
                         "beat_IVV_fraction": (excess > 0).mean(), "return_alignment": "next_month" if forward else "same_month"})
    return pd.DataFrame(rows)


def historical_associations(prices, assignments, latest_regime):
    stats = sector_statistics(prices, assignments.regime)
    latest = stats[stats.regime == latest_regime].set_index("ticker").reindex(SECTORS).reset_index()
    latest["n"] = latest["n"].fillna(0).astype(int)
    latest["sector"] = latest.ticker.map(SECTORS)
    latest["low_sample"] = latest.n < 24
    return stats, latest
