"""
data_loader.py
--------------
Loads and merges all Pillar 1 sheets from the Excel workbook.
We use the Z-score columns as our PCA features because they are already
standardized across series — exactly what PCA needs.

Z-scores were computed in Excel as rolling z-scores relative to the
full sample mean/std for each series (INDPRO, RSAFS, PAYEMS, PCEC96).
"""

import pandas as pd
from pathlib import Path

# ── Sheet → (raw level column, z-score column) mapping ──────────────────────
SHEET_MAP = {
    "Industrial Production-INDPRO": ("INDPRO",  "INDPRO_Z"),
    "Retail Sales-RSAFS":           ("RSAFS",   "RSAFS_Z"),
    "Nonfarm Payrolls-PAYEMS":      ("PAYEMS",  "PAYEMS_Z"),
    "Real Personal Consumption Exp":("PCEC96",  "PCEC96_Z"),
}

DATA_PATH = Path(__file__).parent / "data/raw/Pillar1_-_Growth_Momentum.xlsx"


def load_pillar1(path: Path = DATA_PATH) -> pd.DataFrame:
    """
    Returns a clean, merged DataFrame indexed by observation_date.

    Columns returned:
        INDPRO_Z, RSAFS_Z, PAYEMS_Z, PCEC96_Z
        (plus _YoY, _1M, _3M variants for reference)

    Rows with any NaN in the Z-score columns are dropped so PCA
    always receives a complete matrix.
    """
    frames = []

    for sheet, (raw_col, z_col) in SHEET_MAP.items():
        df = pd.read_excel(path, sheet_name=sheet, header=1)

        # Rename the first column to a standard name
        df = df.rename(columns={df.columns[0]: "date"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # Keep all momentum columns for that series
        keep = [c for c in df.columns if c != raw_col]
        frames.append(df[keep])

    merged = pd.concat(frames, axis=1)
    merged.index.name = "date"
    merged = merged.sort_index()

    # ── Drop rows where ANY z-score is missing ───────────────────────────────
    z_cols = [v for _, v in SHEET_MAP.values()]
    merged = merged.dropna(subset=z_cols)

    print(f"[data_loader] Loaded {len(merged)} months  "
          f"({merged.index[0].date()} → {merged.index[-1].date()})")
    print(f"[data_loader] Z-score features: {z_cols}")

    return merged


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts only the four Z-score columns used as PCA input features.
    These are already standardized, so we do NOT re-standardize in sklearn.
    """
    z_cols = [v for _, v in SHEET_MAP.values()]
    return df[z_cols].copy()
