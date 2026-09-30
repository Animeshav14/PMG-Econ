"""Download archived macro vintages and run strictly prior-month model fits."""
import argparse
from pathlib import Path
from src.vintages import archived_backtest

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--end", default="2020-12-31")
    p.add_argument("--root", type=Path, default=Path(__file__).parent)
    args = p.parse_args()
    rows, failures = archived_backtest(args.root, args.start, args.end)
    print(f"Finished: {len(rows)} classified months, {len(failures)} unavailable months. See outputs/vintage_backtest.")
