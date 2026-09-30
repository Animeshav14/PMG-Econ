# Data

Run `python update_data.py` from the repository root to download source histories
and build the monthly input panels.

| Folder | Contents |
|---|---|
| `raw/` | Timestamped source snapshots, hashes, download metadata and local caches |
| `processed/` | Cleaned monthly observations, pillar features and validation reports |

The folder structure is tracked. Downloaded observations and processed datasets
remain ignored. The [rights review](../docs/redistribution.md) identifies which
original agency data can be reused and which provider or delivery terms still
need resolution. Optional licensed inputs also stay local.

See the [source catalogue](../docs/data_coverage.csv) for verified coverage and
[data sources](../docs/sources.md) for download details and optional input formats.
