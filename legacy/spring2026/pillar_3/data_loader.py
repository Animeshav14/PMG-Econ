"""
data_loader.py
--------------
Loads and merges all Pillar 3 series from the Excel workbook.

Sources:
    - CPI YoY, Core CPI YoY, PPI YoY  → 'Model Data' sheet (monthly, 2005-2026)
    - Federal Funds Rate               → 'FEDFUNDS' sheet  (monthly, trimmed to overlap)
    - 5Y Breakeven Inflation           → '5YearBreakeven' sheet (daily -> resampled to monthly avg)

All five series are then Z-scored so PCA receives a standardized feature matrix.

Overlap window: Jan 2005 -> Feb 2026  (~252 months)
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data/raw/PMG_Inflation_Policy_Historical_Data.xlsx"

FEATURE_COLS = [
    "CPI_YoY_Z",
    "CoreCPI_YoY_Z",
    "PPI_YoY_Z",
    "Breakeven_Z",
    "FedFunds_Z",
]


def _zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std()


def load_pillar3(path: Path = DATA_PATH) -> pd.DataFrame:
    """
    Returns a clean merged DataFrame indexed by date (monthly frequency).

    Columns:
        Raw:      CPI_YoY, CoreCPI_YoY, PPI_YoY, Breakeven, FedFunds
        Z-scored: CPI_YoY_Z, CoreCPI_YoY_Z, PPI_YoY_Z, Breakeven_Z, FedFunds_Z
    """

    # -- 1. Model Data: CPI YoY, Core CPI YoY, PPI YoY ------------------------
    df_model = pd.read_excel(path, sheet_name="Model Data")
    df_model.columns = df_model.columns.str.strip()
    df_model["Date"] = pd.to_datetime(df_model["Date"])
    df_model = df_model.set_index("Date")[["CPI YoY", "Core CPI YoY", "PPI YoY"]]
    df_model.columns = ["CPI_YoY", "CoreCPI_YoY", "PPI_YoY"]

    # -- 2. Federal Funds Rate -------------------------------------------------
    df_ff = pd.read_excel(path, sheet_name="FEDFUNDS")
    df_ff.columns = df_ff.columns.str.strip()
    df_ff["observation_date"] = pd.to_datetime(df_ff["observation_date"])
    df_ff = df_ff.set_index("observation_date")[["FEDFUNDS"]]
    df_ff.columns = ["FedFunds"]

    # -- 3. 5Y Breakeven: daily -> monthly average ----------------------------
    df_be = pd.read_excel(path, sheet_name="5YearBreakeven")
    df_be.columns = df_be.columns.str.strip()
    df_be["observation_date"] = pd.to_datetime(df_be["observation_date"])
    df_be = df_be.set_index("observation_date")[["T5YIE"]].dropna()
    monthly_be = df_be.resample("MS").mean()
    monthly_be.columns = ["Breakeven"]

    # -- 4. Merge on monthly date index ---------------------------------------
    merged = df_model \
        .join(df_ff,       how="left") \
        .join(monthly_be,  how="left")

    merged = merged.sort_index()
    merged = merged.dropna(subset=["CPI_YoY", "CoreCPI_YoY", "PPI_YoY",
                                    "FedFunds", "Breakeven"])

    # -- 5. Z-score each series -----------------------------------------------
    for raw, z in [
        ("CPI_YoY",     "CPI_YoY_Z"),
        ("CoreCPI_YoY", "CoreCPI_YoY_Z"),
        ("PPI_YoY",     "PPI_YoY_Z"),
        ("Breakeven",   "Breakeven_Z"),
        ("FedFunds",    "FedFunds_Z"),
    ]:
        merged[z] = _zscore(merged[raw])

    print(f"[data_loader] Loaded {len(merged)} months  "
          f"({merged.index[0].date()} -> {merged.index[-1].date()})")
    print(f"[data_loader] Features: {FEATURE_COLS}")

    return merged


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Returns only the five Z-scored columns for PCA input."""
    return df[FEATURE_COLS].copy()
