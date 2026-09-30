"""Three-month relative adjusted-price momentum and volatility level."""
import numpy as np
from src.registry import MARKET_CORE


def build(raw):
    r = np.log(raw[MARKET_CORE]).diff(3) * 100
    f = {"breadth_3m": r.RSP - r.IVV, "small_large_3m": r.IWM - r.IVV,
         "technology_3m": r.IYW - r.IVV,
         "cyclical_defensive_3m": r[["XLI", "XLF"]].mean(axis=1, skipna=False) - r[["XLP", "XLV", "XLU"]].mean(axis=1, skipna=False),
         "negative_log_vix": -np.log(raw.VIXCLS)}
    return f, {code: 0 for code in f}
