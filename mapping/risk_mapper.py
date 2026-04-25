"""
Risk Mapper: aggregates raw signals into corridor-level risk scores.

Output: daily risk score per corridor (0-100 scale).
"""

import pandas as pd
import numpy as np
from config.corridors import CORRIDORS


def compute_corridor_risk(signals_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each corridor on each date, compute a weighted composite risk score.

    Score = sum(signal_score * signal_weight), capped and scaled to 0-100.
    """
    if signals_df.empty:
        return pd.DataFrame(columns=["date", "corridor_id", "risk_score", "alert", "top_signal"])

    rows = []
    for cid in CORRIDORS:
        corridor_sigs = signals_df[signals_df["corridor_id"] == cid]
        if corridor_sigs.empty:
            continue

        threshold = CORRIDORS[cid]["alert_threshold"]

        for date, day_sigs in corridor_sigs.groupby("date"):
            # Weighted composite score
            composite = (day_sigs["score"] * day_sigs["weight"]).sum()
            # Scale to 0-100 (z-score of ~3 maps to ~100)
            risk_score = min(100, max(0, composite / 3.0 * 100))
            alert = composite >= threshold
            top = day_sigs.loc[day_sigs["score"].idxmax(), "detail"] if len(day_sigs) > 0 else ""

            rows.append({
                "date": date,
                "corridor_id": cid,
                "corridor_name": CORRIDORS[cid]["name"],
                "risk_score": round(risk_score, 1),
                "composite_z": round(composite, 2),
                "alert": alert,
                "num_signals": len(day_sigs),
                "top_signal": top,
            })

    df = pd.DataFrame(rows).sort_values(["date", "corridor_id"]).reset_index(drop=True)
    return df


def get_current_status(risk_df: pd.DataFrame) -> dict:
    """Get the latest risk status for each corridor."""
    if risk_df.empty:
        return {}

    latest_date = risk_df["date"].max()
    latest = risk_df[risk_df["date"] == latest_date]

    status = {}
    for _, row in latest.iterrows():
        status[row["corridor_id"]] = {
            "name": row["corridor_name"],
            "risk_score": row["risk_score"],
            "alert": row["alert"],
            "top_signal": row["top_signal"],
            "date": row["date"],
        }

    # Fill in corridors with no signals as "low risk"
    for cid in CORRIDORS:
        if cid not in status:
            status[cid] = {
                "name": CORRIDORS[cid]["name"],
                "risk_score": 0,
                "alert": False,
                "top_signal": "No signals detected",
                "date": latest_date,
            }

    return status
