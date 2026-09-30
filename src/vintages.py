"""Strict archived macro vintages via official ALFRED downloads.

Every response must carry the requested vintage in its column name. Failed
requests are recorded; current-vintage macro data are never substituted.
"""
import io
import os
import json
import hashlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
import pandas as pd
from threadpoolctl import threadpool_limits
from .data import validate_series, load_cache, safe_error
from .registry import FRED, MARKET
from .transforms import prepare
from .engine import one_step, write_json, episode_report, plot_episodes
from .sectors import sector_statistics

MACRO_CODES = [s.code for s in FRED if not s.optional and s.pillar != 0]


def parse_vintage(text, code, date):
    expected = f"{code}_{pd.Timestamp(date):%Y%m%d}"
    df = pd.read_csv(io.StringIO(text), na_values=["."])
    if list(df.columns) != ["observation_date", expected]:
        raise ValueError(f"Rejected vintage response: expected {expected}; got {list(df.columns)}")
    s = pd.Series(pd.to_numeric(df[expected], errors="raise").values,
                  index=pd.to_datetime(df.observation_date), name=code).dropna()
    if len(s) and s.index.max() > pd.Timestamp(date):
        raise ValueError(f"{code}: observation date after requested vintage")
    return validate_series(s)


def fetch_vintage(root, code, date):
    date = str(pd.Timestamp(date).date())
    dest = Path(root) / "data/raw/vintages" / date
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / (code + ".csv")
    url = f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={code}&vintage_date={date}"
    if path.exists():
        return parse_vintage(path.read_text(encoding="utf-8"), code, date)
    key = os.environ.get("FRED_API_KEY")
    if key:
        r = requests.get("https://api.stlouisfed.org/fred/series/observations", params={
            "series_id": code, "api_key": key, "file_type": "json", "realtime_start": date, "realtime_end": date}, timeout=45)
        if r.status_code == 200:
            original = r.text
            df = pd.DataFrame(r.json()["observations"])
            s = pd.Series(pd.to_numeric(df.value.replace(".", None)).values, index=pd.to_datetime(df.date), name=f"{code}_{date.replace('-', '')}")
            s.index.name = "observation_date"
            text = s.to_csv()
            (dest / (code + ".json")).write_text(original, encoding="utf-8")
        else:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            text = r.text
    else:
        r = requests.get(url, timeout=45)
        r.raise_for_status()
        text = r.text
    s = parse_vintage(text, code, date)
    path.write_text(text, encoding="utf-8")
    write_json(dest / (code + ".metadata.json"), {"url": url, "requested_vintage": date,
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "first_observation": str(s.index.min().date()), "latest_observation": str(s.index.max().date())})
    return s


def archived_backtest(root, start="2019-01-01", end="2020-12-31", workers=4):
    root = Path(root)
    cache = load_cache(root)
    prices = {c: cache[c] for c in MARKET if c in cache}
    rows, failures = [], []
    out = root / "outputs/vintage_backtest" / f"{start}_{end}"
    out.mkdir(parents=True, exist_ok=True)
    _, current_monthly, _ = prepare(root, write=False)
    for date in pd.date_range(start, end, freq="ME"):
        def get(code):
            try:
                return code, fetch_vintage(root, code, date), None
            except Exception as exc:
                return code, None, safe_error(exc)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(get, MACRO_CODES))
        bad = {code: err for code, _, err in results if err}
        if bad:
            failures.append({"date": str(date.date()), "series_errors": bad})
            print(f"Vintage {date:%Y-%m}: unavailable {list(bad)}", flush=True)
            continue
        vintage = {code: series for code, series, _ in results}
        vintage.update(prices)
        # The next calendar day makes this decision month's observations eligible;
        # response vintages and per-feature availability lags still constrain data.
        pillars, _, missing = prepare(root, date + pd.Timedelta(days=1), cache_override=vintage, write=False)
        if missing:
            failures.append({"date": str(date.date()), "missing_pillars": missing})
            continue
        with threadpool_limits(limits=1):
            row = one_step({n: p["available"] for n, p in pillars.items()}, date)
        if row is None:
            missing_features = {}
            for n, p in pillars.items():
                panel = p["available"]
                missing_features[n] = panel.columns.tolist() if date not in panel.index else panel.columns[panel.loc[date].isna()].tolist()
            failures.append({"date": str(date.date()), "reason": "Incomplete released panel or fewer than 48 training months", "missing_features": missing_features})
        else:
            rows.append(row)
            print(f"Vintage {date:%Y-%m}: {row['state_bucket']}, p={row['confidence']:.1%}", flush=True)
    write_json(out / "method.json", {"mode": "archived_macro_vintages", "start": start, "end": end,
        "macro_point_in_time": True, "market_point_in_time_archive": False,
        "market_caveat": "Yahoo adjusted-price history retrieved now. Future multiplicative adjustment factors cancel in relative log returns, but vendor corrections and historical universes are not archived.",
        "availability": "Exact ALFRED requested-vintage headers plus conservative release lags. No current-macro substitution.",
        "failed_dates": failures, "successful_dates": len(rows)})
    if rows:
        history = pd.DataFrame(rows).set_index("date")
        history.to_csv(out / "assignments.csv")
        episode_report(history, current_monthly).to_csv(out / "episodes.csv", index=False)
        sector_statistics(current_monthly, history.state_bucket, forward=True).to_csv(out / "next_month_sector_history.csv", index=False)
        plot_episodes(history, out)
    return rows, failures
