"""Record only the installed dependency closure used by this project."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement

roots = ["pandas", "numpy", "scikit-learn", "scipy", "matplotlib", "requests",
         "yfinance", "openpyxl", "threadpoolctl", "pytest"]
seen, pending = {}, list(roots)
while pending:
    d = distribution(pending.pop())
    name = d.metadata["Name"].lower()
    if name in seen:
        continue
    seen[name] = d.version
    for value in d.requires or []:
        req = Requirement(value)
        if req.marker is None or req.marker.evaluate({"extra": ""}):
            pending.append(req.name)
Path("requirements-lock.txt").write_text(
    "# Validated Python 3.12 dependency closure; regenerate deliberately when upgrading.\n"
    + "\n".join(k + "==" + v for k, v in sorted(seen.items())) + "\n", encoding="utf-8")
print(len(seen), "locked distributions")
