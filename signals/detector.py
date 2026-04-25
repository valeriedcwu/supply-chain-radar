"""
Signal detection engine.

Three signal types:
1. Price anomaly: rolling z-score on individual series
2. Correlation breakdown: when normally correlated assets diverge
3. News spike: surge in negative headlines for a corridor

All signals output a standardized format:
    {date, corridor_id, signal_type, score, detail}
"""

import pandas as pd
import numpy as np
from typing import Optional

from config.corridors import CORRIDORS


# ---------------------------------------------------------------------------
# 1. Price anomaly detection (rolling z-score)
# ---------------------------------------------------------------------------

def detect_price_anomalies(
    market_df: pd.DataFrame,
    window: int = 60,
    min_periods: int = 30,
) -> pd.DataFrame:
    """
    For each ticker in each corridor, compute rolling z-score of daily returns.
    Flag when |z| exceeds corridor threshold.
    """
    signals = []

    for cid, corridor in CORRIDORS.items():
        threshold = corridor["alert_threshold"]
        all_sigs = {**corridor["market_signals"], **corridor.get("fred_signals", {})}

        for ticker, meta in all_sigs.items():
            series = market_df[market_df["ticker"] == ticker].copy()
            if len(series) < min_periods:
                continue

            series = series.sort_values("date").set_index("date")
            series["return"] = series["close"].pct_change()

            roll_mean = series["return"].rolling(window, min_periods=min_periods).mean()
            roll_std = series["return"].rolling(window, min_periods=min_periods).std()
            series["z_score"] = (series["return"] - roll_mean) / roll_std.replace(0, np.nan)

            # Directional: "up" means positive z = stress, "down" means negative z = stress
            direction_mult = 1.0 if meta["direction"] == "up" else -1.0

            for date, row in series.iterrows():
                z = row["z_score"]
                if pd.isna(z):
                    continue
                directed_z = z * direction_mult
                if directed_z > threshold * 0.5:  # store sub-threshold too for composite
                    signals.append({
                        "date": date,
                        "corridor_id": cid,
                        "signal_type": "price_anomaly",
                        "ticker": ticker,
                        "score": float(directed_z),
                        "weight": meta["weight"],
                        "detail": f"{meta['name']}: z={z:.2f} (return={row['return']:.4f})",
                    })

    return pd.DataFrame(signals)


# ---------------------------------------------------------------------------
# 2. Correlation breakdown detection
# ---------------------------------------------------------------------------

def detect_correlation_breaks(
    market_df: pd.DataFrame,
    window: int = 60,
    short_window: int = 10,
) -> pd.DataFrame:
    """
    For each corridor, check if the short-term correlation between its
    tickers diverges significantly from the long-term correlation.
    A breakdown in normal relationships signals disruption.
    """
    signals = []

    for cid, corridor in CORRIDORS.items():
        tickers = list(corridor["market_signals"].keys())
        if len(tickers) < 2:
            continue

        # Build return matrix
        pivoted = market_df[market_df["ticker"].isin(tickers)].pivot_table(
            index="date", columns="ticker", values="close"
        ).pct_change().dropna()

        if len(pivoted) < window:
            continue

        # Rolling correlation of first two tickers as a proxy
        t1, t2 = tickers[0], tickers[1]
        if t1 not in pivoted.columns or t2 not in pivoted.columns:
            continue

        long_corr = pivoted[t1].rolling(window).corr(pivoted[t2])
        short_corr = pivoted[t1].rolling(short_window).corr(pivoted[t2])
        corr_diff = (long_corr - short_corr).abs()

        for date, diff in corr_diff.dropna().items():
            if diff > 0.5:  # significant divergence
                signals.append({
                    "date": date,
                    "corridor_id": cid,
                    "signal_type": "correlation_break",
                    "ticker": f"{t1}/{t2}",
                    "score": float(diff),
                    "weight": 0.3,
                    "detail": f"Corr breakdown {t1} vs {t2}: Δ={diff:.2f}",
                })

    return pd.DataFrame(signals)


# ---------------------------------------------------------------------------
# 3. News spike detection
# ---------------------------------------------------------------------------

def detect_news_spikes(
    news_df: pd.DataFrame,
    spike_threshold: int = 5,
) -> pd.DataFrame:
    """
    Count daily articles per corridor. Flag days with abnormal volume.
    """
    if news_df.empty:
        return pd.DataFrame(columns=["date", "corridor_id", "signal_type", "score", "detail"])

    signals = []
    for cid in CORRIDORS:
        corridor_news = news_df[news_df["corridor_id"] == cid]
        if corridor_news.empty:
            continue

        daily_count = corridor_news.groupby("date").size()
        mean_count = daily_count.mean()
        std_count = daily_count.std()
        if std_count == 0:
            continue

        for date, count in daily_count.items():
            z = (count - mean_count) / std_count
            if z > 1.0:
                # Get sample headlines for detail
                day_headlines = corridor_news[corridor_news["date"] == date]["title"].head(3).tolist()
                signals.append({
                    "date": date,
                    "corridor_id": cid,
                    "signal_type": "news_spike",
                    "ticker": "",
                    "score": float(z),
                    "weight": 0.2,
                    "detail": f"News spike ({count} articles, z={z:.1f}): {day_headlines[0][:80]}...",
                })

    return pd.DataFrame(signals)


# ---------------------------------------------------------------------------
# 4. Price level detector (catches sustained elevated/depressed prices)
# ---------------------------------------------------------------------------

def detect_price_levels(
    market_df: pd.DataFrame,
    baseline_window: int = 180,
    recent_window: int = 10,
    min_periods: int = 60,
) -> pd.DataFrame:
    """
    Compare recent price LEVEL to long-term baseline.
    Catches sustained moves that z-score adapts to.
    E.g., Brent at $100+ for weeks — z-score normalizes, but level detector
    sees it's 40% above the 6-month average.
    """
    signals = []

    for cid, corridor in CORRIDORS.items():
        threshold = corridor["alert_threshold"]
        all_sigs = {**corridor["market_signals"], **corridor.get("fred_signals", {})}

        for ticker, meta in all_sigs.items():
            series = market_df[market_df["ticker"] == ticker].copy()
            if len(series) < min_periods:
                continue

            series = series.sort_values("date").set_index("date")
            baseline_avg = series["close"].rolling(baseline_window, min_periods=min_periods).mean()
            recent_avg = series["close"].rolling(recent_window, min_periods=5).mean()

            # Percent deviation from baseline
            pct_deviation = (recent_avg - baseline_avg) / baseline_avg * 100

            direction_mult = 1.0 if meta["direction"] == "up" else -1.0

            for date, row in series.iterrows():
                dev = pct_deviation.get(date)
                if pd.isna(dev):
                    continue
                directed_dev = dev * direction_mult
                # Convert to z-score-like scale: 20% deviation ≈ z-score of 2
                score = directed_dev / 10.0
                if score > threshold * 0.5:
                    signals.append({
                        "date": date,
                        "corridor_id": cid,
                        "signal_type": "price_level",
                        "ticker": ticker,
                        "score": float(score),
                        "weight": meta["weight"] * 0.8,
                        "detail": f"{meta['name']}: {directed_dev:+.1f}% vs 6-month baseline",
                    })

    return pd.DataFrame(signals)


# ---------------------------------------------------------------------------
# Main: run all detectors
# ---------------------------------------------------------------------------

def run_all_signals(
    market_df: pd.DataFrame,
    news_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Run all signal detectors and return combined DataFrame."""
    print("Running price anomaly detection...")
    price_sigs = detect_price_anomalies(market_df)
    print(f"  → {len(price_sigs)} price signals")

    print("Running price level detection...")
    level_sigs = detect_price_levels(market_df)
    print(f"  → {len(level_sigs)} price level signals")

    print("Running correlation breakdown detection...")
    corr_sigs = detect_correlation_breaks(market_df)
    print(f"  → {len(corr_sigs)} correlation signals")

    news_sigs = pd.DataFrame()
    if news_df is not None and not news_df.empty:
        print("Running news spike detection...")
        news_sigs = detect_news_spikes(news_df)
        print(f"  → {len(news_sigs)} news signals")

    all_signals = pd.concat([price_sigs, level_sigs, corr_sigs, news_sigs], ignore_index=True)
    all_signals = all_signals.sort_values("date").reset_index(drop=True)
    print(f"\n✅ Total signals: {len(all_signals)}")
    return all_signals
