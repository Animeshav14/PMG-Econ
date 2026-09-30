"""Download source observations, preserve snapshots, and report provenance."""
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
from .registry import FRED, MARKET, INCEPTION


def read_fred_csv(content, code):
    df = pd.read_csv(io.StringIO(content), na_values=["."])
    if code not in df or not ({"observation_date", "DATE"} & set(df.columns)):
        raise ValueError(f"Unexpected FRED columns for {code}: {list(df.columns)}")
    dates = pd.to_datetime(df.iloc[:, 0], errors="raise")
    s = pd.Series(pd.to_numeric(df[code], errors="raise").values, index=dates, name=code)
    return validate_series(s)


def validate_series(s):
    if s.index.has_duplicates:
        raise ValueError(f"Duplicate dates: {s.name}")
    if s.index.isna().any():
        raise ValueError(f"Invalid dates: {s.name}")
    s = s.sort_index()
    if s.dropna().empty:
        raise ValueError(f"Empty series: {s.name}")
    if not s.dropna().map(lambda v: float('-inf') < v < float('inf')).all():
        raise ValueError(f"Nonfinite observations: {s.name}")
    s.index.name = "date"
    return s


def fetch_fred(code, session=None):
    session = session or requests.Session()
    key = os.environ.get("FRED_API_KEY")
    # Never return/log a request URL containing the key.
    if key:
        url = "https://api.stlouisfed.org/fred/series/observations"
        try:
            r = session.get(url, params={"series_id": code, "api_key": key, "file_type": "json"}, timeout=45)
            if r.status_code == 200:
                df = pd.DataFrame(r.json()["observations"])
                s = pd.Series(pd.to_numeric(df.value.replace(".", None)).values,
                              index=pd.to_datetime(df.date), name=code)
                return validate_series(s), r.text, url, ".json"
        except (requests.RequestException, ValueError, KeyError):
            pass
    url = f"https://fred.stlouisfed.org/graph/?id={code}"
    download = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd=1900-01-01"
    r = session.get(download, timeout=45)
    r.raise_for_status()
    return read_fred_csv(r.text, code), r.text, download, ".csv"


def safe_error(exc):
    msg = str(exc)
    key = os.environ.get("FRED_API_KEY")
    return msg.replace(key, "[redacted]") if key else msg


def update(root=Path("."), probe_optional=True):
    root = Path(root)
    raw = root / "data/raw"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    retrieved = datetime.now(timezone.utc).isoformat()
    snapshot = raw / "snapshots" / stamp
    snapshot.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    print(f"Retrieval timestamp: {retrieved}", flush=True)
    for spec in FRED:
        record = {**spec.metadata(), "retrieved_at": retrieved}
        try:
            s, content, url, ext = fetch_fred(spec.code)
            dest = snapshot / (spec.code + ext)
            dest.write_text(content, encoding="utf-8")
            target = raw / "fred" / (spec.code + ".csv")
            target.parent.mkdir(parents=True, exist_ok=True)
            # Source response remains intact in snapshots; canonical cache is only date/value.
            s.to_csv(target)
            record.update(status="ok", first_observation=str(s.first_valid_index().date()),
                          latest_observation=str(s.last_valid_index().date()),
                          rows=int(s.notna().sum()), missing=int(s.isna().sum()),
                          download_url=url, snapshot=str(dest.relative_to(root)),
                          sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
            print(f"{spec.code}: {record['first_observation']} .. {record['latest_observation']}", flush=True)
        except Exception as exc:
            record.update(status="failed", error=safe_error(exc))
            failures.append(record)
            print(f"FAILED {spec.code}: {safe_error(exc)}", flush=True)
        records.append(record)

    import yfinance as yf
    cache = raw / "yfinance_cache"
    cache.mkdir(exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    for ticker in MARKET:
        record = {"code": ticker, "name": ticker, "source": "Yahoo Finance / yfinance",
                  "url": f"https://finance.yahoo.com/quote/{ticker}/history/",
                  "frequency": "daily", "units": "USD adjusted close", "retrieved_at": retrieved,
                  "inception": INCEPTION.get(ticker), "optional": False}
        try:
            df = yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=True, raise_errors=True)
            if "Adj Close" not in df or df.empty:
                raise ValueError("Yahoo returned no adjusted-price history")
            df.index = df.index.tz_localize(None).normalize()
            df.index.name = "date"
            s = validate_series(df["Adj Close"].rename(ticker))
            if (s.dropna() <= 0).any():
                raise ValueError("Nonpositive adjusted prices")
            dest = snapshot / (ticker + ".csv")
            df.to_csv(dest)
            target = raw / "yahoo" / (ticker + ".csv")
            target.parent.mkdir(exist_ok=True)
            s.to_csv(target)
            record.update(status="ok", first_observation=str(s.first_valid_index().date()),
                          latest_observation=str(s.last_valid_index().date()), rows=int(s.notna().sum()),
                          missing=int(s.isna().sum()), snapshot=str(dest.relative_to(root)),
                          sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
            print(f"{ticker}: {record['first_observation']} .. {record['latest_observation']}", flush=True)
        except Exception as exc:
            record.update(status="failed", error=safe_error(exc))
            failures.append(record)
            print(f"FAILED {ticker}: {safe_error(exc)}", flush=True)
        records.append(record)
    probes = []
    if probe_optional:
        for code in ["NAPM", "NAPMNON", "BAAA"]:
            try:
                s, content, url, ext = fetch_fred(code)
                (snapshot / (code + ext)).write_text(content, encoding="utf-8")
                probes.append({"code": code, "status": "retrieved_not_enabled", "first": str(s.first_valid_index()), "last": str(s.last_valid_index())})
            except Exception as exc:
                probes.append({"code": code, "status": "unavailable", "error": safe_error(exc)})
    manifest = {"retrieved_at": retrieved, "snapshot": stamp, "series": records, "optional_probes": probes}
    (snapshot / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_manual_requests(root, failures, probes)
    return manifest


def write_manual_requests(root, failures, probes):
    lines = ["# Files still needed", "", "Only failed core inputs are required. ISM is optional.", ""]
    for r in failures:
        c = r["code"]
        folder = "fred" if r["source"] == "FRED" else "yahoo"
        lines += [f"## {c}", f"Variable: {r['name']}; pillar: {r.get('pillar', '4 / sector analysis')}",
                  f"Source: {r['source']}; page: {r['url']}",
                  "Range: longest available history through current date (at least 2000-present where available).",
                  f"Frequency: {r['frequency']}; format: CSV; columns: date,{c}",
                  f"File: data/raw/{folder}/{c}.csv", f"Automatic retrieval failed: {r['error']}",
                  f"Direct download: https://fred.stlouisfed.org/graph/fredgraph.csv?id={c}" if folder == "fred" else "Export adjusted close; unadjusted close is not an acceptable substitute.", ""]
    if not failures:
        lines += ["None required: all enabled core data was acquired programmatically.", ""]
    lines += ["## Optional ISM history", "Pillar 1; manufacturing and services PMI; monthly, longest licensed history through present.",
              "Source: https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/",
              "Request licensed historical data from ISM; do not scrape historical releases.",
              "Files: data/raw/local/ISM_MANUFACTURING.csv and ISM_SERVICES.csv; columns: date,value.",
              "Use --include-ism only when you have permission to use these data. They are never committed.",
              "Official FRED legacy-code attempts: " + json.dumps(probes), ""]
    out = root / "outputs/latest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "manual_download_requests.md").write_text("\n".join(lines), encoding="utf-8")


def load_cache(root):
    root = Path(root)
    result = {}
    for folder in ["fred", "yahoo"]:
        for p in (root / "data/raw" / folder).glob("*.csv"):
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if list(df.columns) != [p.stem]:
                raise ValueError(f"Expected date,{p.stem} in {p}")
            result[p.stem] = validate_series(df.iloc[:, 0])
    return result
