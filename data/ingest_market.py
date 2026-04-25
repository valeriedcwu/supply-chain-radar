"""
Market data ingestion from yfinance and FRED API.

Usage:
    python -m data.ingest_market
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Optional: FRED API for macro indicators
try:
    from fredapi import Fred

    FRED_API_KEY = os.getenv("FRED_API_KEY", "")
    fred = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else None
except ImportError:
    fred = None

from config.corridors import CORRIDORS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data_store")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_market_data(lookback_days: int = 365) -> pd.DataFrame:
    """Pull all market tickers defined in corridor config via yfinance."""
    # Collect unique tickers across all corridors
    tickers = set()
    for corridor in CORRIDORS.values():
        tickers.update(corridor["market_signals"].keys())

    tickers = sorted(tickers)
    end = datetime.today()
    start = end - timedelta(days=lookback_days)

    print(f"Fetching {len(tickers)} tickers from {start.date()} to {end.date()}...")
    raw = yf.download(tickers, start=start, end=end, group_by="ticker", auto_adjust=True)

    # Normalize to a clean DataFrame: date | ticker | close
    rows = []
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                series = raw["Close"]
            else:
                series = raw[ticker]["Close"]
            for date, price in series.dropna().items():
                rows.append({"date": date, "ticker": ticker, "close": float(price)})
        except (KeyError, TypeError):
            print(f"  ⚠ Could not fetch {ticker}, skipping")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def fetch_fred_data(lookback_days: int = 365) -> pd.DataFrame:
    """Pull FRED series defined in corridor config."""
    if fred is None:
        print("FRED API not configured — skipping. Set FRED_API_KEY env var.")
        return pd.DataFrame(columns=["date", "ticker", "close"])

    series_ids = set()
    for corridor in CORRIDORS.values():
        series_ids.update(corridor.get("fred_signals", {}).keys())

    end = datetime.today()
    start = end - timedelta(days=lookback_days)

    rows = []
    for sid in sorted(series_ids):
        try:
            s = fred.get_series(sid, observation_start=start, observation_end=end)
            for date, val in s.dropna().items():
                rows.append({"date": date.date(), "ticker": sid, "close": float(val)})
            print(f"  ✓ {sid}: {len(s.dropna())} observations")
        except Exception as e:
            print(f"  ⚠ FRED {sid} failed: {e}")

    return pd.DataFrame(rows)


def ingest_all(lookback_days: int = 365) -> pd.DataFrame:
    """Fetch everything and save to parquet."""
    market = fetch_market_data(lookback_days)
    fred_data = fetch_fred_data(lookback_days)

    df = pd.concat([market, fred_data], ignore_index=True)
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    out_path = os.path.join(DATA_DIR, "market_data.parquet")
    df.to_parquet(out_path, index=False)
    print(f"\n✅ Saved {len(df)} rows to {out_path}")
    print(f"   Tickers: {sorted(df['ticker'].unique())}")
    print(f"   Date range: {df['date'].min()} → {df['date'].max()}")
    return df


if __name__ == "__main__":
    ingest_all()
