"""Run all four pillars, composite landscape and sector history."""
import argparse
from pathlib import Path
from src.engine import run, backtest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--as-of", help="Date cutoff; excludes its incomplete calendar month. Uses current revised data.")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--include-ism", action="store_true", help="Include locally licensed monthly ISM files")
    parser.add_argument("--backtest", action="store_true", help="Also run expanding historical diagnostics")
    parser.add_argument("--backtest-only", action="store_true")
    args = parser.parse_args()
    if not args.backtest_only:
        run(args.root, args.as_of, not args.no_plots, args.include_ism)
    if args.backtest or args.backtest_only:
        backtest(args.root, args.as_of)
