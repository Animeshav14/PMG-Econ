"""Download sources and rebuild validated monthly input panels."""
from pathlib import Path
from src.data import update

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    update(args.root)
    from src.transforms import prepare
    pillars, _, failures = prepare(args.root)
    common = None
    for n, inputs in pillars.items():
        complete = inputs["features"].dropna().index
        common = complete if common is None else common.intersection(complete)
        print(f"Pillar {n} latest usable observation month: {complete.max()}")
    print("Latest common model month:", common.max() if common is not None and len(pillars) == 4 else "unavailable")
    print("Failed pillars:", failures)
    from src.engine import freshness
    _, coverage = freshness(args.root, None)
    print("Stale series:", coverage.loc[coverage.get("stale", False) == True, "code"].tolist())
    print("Failed series:", coverage.loc[coverage.status != "ok", "code"].tolist())
