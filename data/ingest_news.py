"""
News/headline ingestion for supply chain event detection.

Uses GDELT GKG (free, no key needed) as primary source.
Fallback to NewsAPI if NEWSAPI_KEY is set.

Usage:
    python -m data.ingest_news
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

from config.corridors import CORRIDORS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data_store")
os.makedirs(DATA_DIR, exist_ok=True)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


def fetch_gdelt_news(lookback_days: int = 30) -> pd.DataFrame:
    """
    Query GDELT DOC API for headlines matching corridor keywords.
    Free, no API key needed, but limited to ~3 months of data.
    """
    all_keywords = set()
    keyword_to_corridor = {}
    for cid, corridor in CORRIDORS.items():
        for kw in corridor["news_keywords"]:
            all_keywords.add(kw)
            keyword_to_corridor[kw] = cid

    rows = []
    start_date = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y%m%d%H%M%S")
    end_date = datetime.today().strftime("%Y%m%d%H%M%S")

    for i, keyword in enumerate(sorted(all_keywords)):
        # Rate-limit: wait between requests to avoid GDELT throttling
        if i > 0:
            time.sleep(3)

        for attempt in range(3):  # retry up to 3 times
            try:
                url = "https://api.gdeltproject.org/api/v2/doc/doc"
                params = {
                    "query": keyword,
                    "mode": "artlist",
                    "maxrecords": 50,
                    "format": "json",
                    "startdatetime": start_date,
                    "enddatetime": end_date,
                    "sort": "datedesc",
                }
                resp = requests.get(url, params=params, timeout=30)

                # Check for non-JSON response (empty results or error page)
                content_type = resp.headers.get("Content-Type", "")
                if "json" not in content_type or not resp.text.strip().startswith("{"):
                    print(f"  ⚠ '{keyword}': no results (non-JSON response), skipping")
                    break

                data = resp.json()
                for article in data.get("articles", []):
                    rows.append({
                        "date": pd.to_datetime(article.get("seendate", "")).date(),
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("domain", ""),
                        "keyword": keyword,
                        "corridor_id": keyword_to_corridor.get(keyword, ""),
                        "tone": article.get("tone", 0),
                    })
                print(f"  ✓ '{keyword}': {len(data.get('articles', []))} articles")
                break  # success, no retry needed

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < 2:
                    wait = 5 * (attempt + 1)
                    print(f"  ⏳ '{keyword}' timeout, retrying in {wait}s... (attempt {attempt+2}/3)")
                    time.sleep(wait)
                else:
                    print(f"  ⚠ '{keyword}': failed after 3 attempts, skipping")
            except Exception as e:
                print(f"  ⚠ GDELT query '{keyword}' failed: {e}")
                break

    return pd.DataFrame(rows)


def fetch_newsapi_news(lookback_days: int = 30) -> pd.DataFrame:
    """Fallback: use NewsAPI.org (requires free API key)."""
    if not NEWSAPI_KEY:
        return pd.DataFrame()

    all_keywords = set()
    keyword_to_corridor = {}
    for cid, corridor in CORRIDORS.items():
        for kw in corridor["news_keywords"]:
            all_keywords.add(kw)
            keyword_to_corridor[kw] = cid

    rows = []
    from_date = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    for keyword in sorted(all_keywords):
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": keyword,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "pageSize": 30,
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=15,
            )
            data = resp.json()
            for article in data.get("articles", []):
                rows.append({
                    "date": pd.to_datetime(article.get("publishedAt", "")).date(),
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "keyword": keyword,
                    "corridor_id": keyword_to_corridor.get(keyword, ""),
                    "tone": 0,
                })
        except Exception as e:
            print(f"  ⚠ NewsAPI '{keyword}' failed: {e}")

    return pd.DataFrame(rows)


def ingest_all(lookback_days: int = 30) -> pd.DataFrame:
    """Fetch news from available sources and save."""
    print("Fetching from GDELT...")
    df = fetch_gdelt_news(lookback_days)

    if df.empty and NEWSAPI_KEY:
        print("GDELT empty, trying NewsAPI...")
        df = fetch_newsapi_news(lookback_days)

    if df.empty:
        print("⚠ No news data fetched. Check your network / API keys.")
        return df

    df = df.drop_duplicates(subset=["title", "date"]).sort_values("date", ascending=False)

    out_path = os.path.join(DATA_DIR, "news_data.parquet")

    # Merge with existing data instead of overwriting
    if os.path.exists(out_path):
        existing = pd.read_parquet(out_path)
        df = pd.concat([existing, df], ignore_index=True)
        df = df.drop_duplicates(subset=["title", "date"]).sort_values("date", ascending=False)
        print(f"  Merged with {len(existing)} existing articles")

    df.to_parquet(out_path, index=False)
    print(f"\n✅ Saved {len(df)} articles to {out_path}")
    return df


if __name__ == "__main__":
    ingest_all()
