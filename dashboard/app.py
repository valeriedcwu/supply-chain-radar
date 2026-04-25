"""
Supply Chain Radar — Streamlit Dashboard

Run: streamlit run dashboard/app.py
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.corridors import CORRIDORS
from signals.detector import run_all_signals
from mapping.risk_mapper import compute_corridor_risk, get_current_status

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supply Chain Radar",
    page_icon="🛰️",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data_store")

# ── Dark theme plotly defaults ───────────────────────────────────────────────
PLOT_TEMPLATE = "plotly_dark"
RISK_COLORS = ["#00c853", "#ffd600", "#ff3d00"]  # green → yellow → red


# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_and_process():
    market_path = os.path.join(DATA_DIR, "market_data.parquet")
    news_path = os.path.join(DATA_DIR, "news_data.parquet")

    if not os.path.exists(market_path):
        st.error("No market data found. Run `python -m data.ingest_market` first.")
        st.stop()

    market_df = pd.read_parquet(market_path)
    news_df = pd.read_parquet(news_path) if os.path.exists(news_path) else pd.DataFrame()

    signals = run_all_signals(market_df, news_df)
    risk = compute_corridor_risk(signals)

    return market_df, news_df, signals, risk


market_df, news_df, signals_df, risk_df = load_and_process()
status = get_current_status(risk_df)


# ── Helper: get recent peak for a corridor ───────────────────────────────────
def get_recent_peak(risk_df, corridor_id, lookback_days=30):
    """Get peak risk score in last N days for a corridor."""
    if risk_df.empty:
        return 0, None
    cdf = risk_df[risk_df["corridor_id"] == corridor_id].copy()
    if cdf.empty:
        return 0, None
    cdf["date"] = pd.to_datetime(cdf["date"])
    cutoff = cdf["date"].max() - timedelta(days=lookback_days)
    recent = cdf[cdf["date"] >= cutoff]
    if recent.empty:
        return 0, None
    peak_row = recent.loc[recent["risk_score"].idxmax()]
    return peak_row["risk_score"], peak_row["date"].strftime("%b %d")


# ── Header ───────────────────────────────────────────────────────────────────
st.title("🛰️ Supply Chain Radar")
st.caption(
    "Financial market signals as early warning for supply chain disruptions.  |  "
    "Commodity futures · FX rates · Shipping indices · News sentiment"
)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_live, tab_backtest = st.tabs(["📡 Live Monitor", "🔬 Backtest: Case Studies"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: LIVE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_live:

    # ── Current Status Row ───────────────────────────────────────────────────
    st.subheader("Current Risk Status")
    cols = st.columns(len(CORRIDORS))

    for i, (cid, corridor) in enumerate(CORRIDORS.items()):
        info = status.get(cid, {"risk_score": 0, "alert": False, "top_signal": "N/A"})
        score = info["risk_score"]
        peak_score, peak_date = get_recent_peak(risk_df, cid, lookback_days=30)

        # Color coding based on CURRENT or RECENT PEAK (whichever is higher)
        display_score = max(score, peak_score)
        if display_score >= 70:
            color, label = "🔴", "HIGH"
        elif display_score >= 40:
            color, label = "🟡", "ELEVATED"
        else:
            color, label = "🟢", "NORMAL"

        with cols[i]:
            if peak_score > score and peak_score >= 40:
                # Show peak as primary, today as context
                st.metric(
                    label=f"{color} {corridor['name']}",
                    value=f"{peak_score:.0f}/100",
                    delta=label,
                    delta_color="inverse" if display_score >= 40 else "normal",
                )
                st.caption(f"30-day peak ({peak_date}) · Today: {score:.0f}")
            else:
                st.metric(
                    label=f"{color} {corridor['name']}",
                    value=f"{score:.0f}/100",
                    delta=label,
                    delta_color="inverse" if display_score >= 40 else "normal",
                )
            if info.get("alert"):
                st.warning(f"⚠️ {info['top_signal'][:100]}")

    # ── World Map ────────────────────────────────────────────────────────────
    st.subheader("Global Corridor Map")

    map_data = []
    for cid, corridor in CORRIDORS.items():
        info = status.get(cid, {"risk_score": 0})
        peak_score, _ = get_recent_peak(risk_df, cid, lookback_days=30)
        display = max(info["risk_score"], peak_score)
        map_data.append({
            "lat": corridor["lat"],
            "lon": corridor["lon"],
            "name": corridor["name"],
            "risk_score": display,
            "size": max(15, display),
        })

    map_df = pd.DataFrame(map_data)
    fig_map = px.scatter_geo(
        map_df,
        lat="lat",
        lon="lon",
        size="size",
        color="risk_score",
        color_continuous_scale=RISK_COLORS,
        range_color=[0, 100],
        hover_name="name",
        hover_data={"risk_score": True, "size": False, "lat": False, "lon": False},
        projection="natural earth",
    )
    fig_map.update_layout(
        template=PLOT_TEMPLATE,
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#555",
            showland=True,
            landcolor="#1a1a2e",
            bgcolor="rgba(0,0,0,0)",
            oceancolor="#0e1117",
            showocean=True,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_map, width='stretch')

    # ── Risk Timeline ────────────────────────────────────────────────────────
    st.subheader("Risk Score Timeline")

    if not risk_df.empty:
        fig_timeline = px.line(
            risk_df,
            x="date",
            y="risk_score",
            color="corridor_name",
            labels={"risk_score": "Risk Score (0-100)", "date": ""},
        )
        fig_timeline.add_hline(
            y=70, line_dash="dash", line_color="#ff3d00",
            annotation_text="High Risk", annotation_font_color="#ff3d00",
        )
        fig_timeline.add_hline(
            y=40, line_dash="dash", line_color="#ffd600",
            annotation_text="Elevated", annotation_font_color="#ffd600",
        )
        fig_timeline.update_layout(
            template=PLOT_TEMPLATE,
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_timeline, width='stretch')
    else:
        st.info("No risk data to display.")

    # ── Signal Drilldown ─────────────────────────────────────────────────────
    st.subheader("Signal Drilldown")

    selected_corridor = st.selectbox(
        "Select corridor:",
        options=list(CORRIDORS.keys()),
        format_func=lambda x: CORRIDORS[x]["name"],
    )

    if not signals_df.empty:
        corridor_signals = signals_df[signals_df["corridor_id"] == selected_corridor].copy()

        if not corridor_signals.empty:
            col1, col2 = st.columns(2)

            with col1:
                type_counts = corridor_signals["signal_type"].value_counts()
                fig_types = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Signal Type Distribution",
                    color_discrete_sequence=["#4fc3f7", "#ffab40", "#aed581", "#ff8a65"],
                )
                fig_types.update_layout(
                    template=PLOT_TEMPLATE,
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_types, width='stretch')

            with col2:
                fig_scores = px.scatter(
                    corridor_signals,
                    x="date",
                    y="score",
                    color="signal_type",
                    size="weight",
                    hover_data=["detail"],
                    title="Signal Scores Over Time",
                    color_discrete_sequence=["#4fc3f7", "#ffab40", "#aed581", "#ff8a65"],
                )
                fig_scores.update_layout(
                    template=PLOT_TEMPLATE,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_scores, width='stretch')

            st.markdown("**Recent High-Scoring Signals**")
            recent = (
                corridor_signals.nlargest(10, "score")[
                    ["date", "signal_type", "ticker", "score", "detail"]
                ]
            )
            st.dataframe(recent, width='stretch', hide_index=True)
        else:
            st.info(f"No signals detected for {CORRIDORS[selected_corridor]['name']}.")

    # ── Raw Data Explorer ────────────────────────────────────────────────────
    with st.expander("📊 Raw Market Data Explorer"):
        tickers = sorted(market_df["ticker"].unique())
        selected_ticker = st.selectbox("Ticker:", tickers)
        ticker_data = market_df[market_df["ticker"] == selected_ticker].sort_values("date")
        fig_price = px.line(ticker_data, x="date", y="close", title=f"{selected_ticker} — Price History")
        fig_price.update_layout(
            template=PLOT_TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_price, width='stretch')


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: BACKTEST — CASE STUDIES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_backtest:

    st.subheader("🔬 Backtest: Did the Radar Catch Real Events?")
    st.markdown(
        "Below we highlight periods where known real-world supply chain disruptions occurred "
        "and check whether our financial signal engine detected elevated risk **before or during** "
        "the event."
    )

    if risk_df.empty:
        st.warning("No risk data available for backtesting.")
    else:
        risk_bt = risk_df.copy()
        risk_bt["date"] = pd.to_datetime(risk_bt["date"])

        # ── Define known events ──────────────────────────────────────────────
        EVENTS = [
            {
                "name": "Black Sea Grain Corridor Volatility",
                "corridor": "grain_black_sea",
                "start": "2025-06-01",
                "end": "2025-10-31",
                "description": (
                    "Ongoing uncertainty around Ukraine grain exports and Black Sea corridor "
                    "access drove wheat and corn futures volatility."
                ),
            },
            {
                "name": "Iran War & Strait of Hormuz Crisis",
                "corridor": "energy_middle_east",
                "start": "2026-02-28",
                "end": "2026-04-08",
                "description": (
                    "US-Israel strikes on Iran triggered closure of the Strait of Hormuz, "
                    "disrupting 20% of global oil supply. Brent surged from $71 to over $120/bbl. "
                    "IEA called it the 'greatest global energy security challenge in history.'"
                ),
            },
            {
                "name": "TSMC Export Controls & Chip Supply Chain Stress",
                "corridor": "semiconductor_taiwan",
                "start": "2025-08-15",
                "end": "2026-01-15",
                "description": (
                    "US revoked TSMC's Validated End-User status for its Nanjing fab (announced Sep 2025), "
                    "Taiwan proposed N-2 export rule restricting leading-edge chip manufacturing abroad (Dec 2025), "
                    "and TSMC secured a one-year annual license replacing the permanent waiver (Jan 2026). "
                    "Multiple shocks to the global semiconductor supply chain in rapid succession."
                ),
            },
            {
                "name": "US-China Tariff Escalation (2025–2026)",
                "corridor": "industrial_asia_pacific",
                "start": "2025-07-01",
                "end": "2025-12-31",
                "description": (
                    "Escalating US tariffs on Chinese goods through 2025 disrupted industrial "
                    "supply chains. Copper futures and CNY/USD reflected trade war stress."
                ),
            },
        ]

        data_min = risk_bt["date"].min()
        data_max = risk_bt["date"].max()

        for event in EVENTS:
            st.markdown("---")
            st.markdown(f"### 📌 {event['name']}")
            st.markdown(f"**Corridor:** {CORRIDORS.get(event['corridor'], {}).get('name', event['corridor'])}")
            st.markdown(f"**Period:** {event['start']} → {event['end']}")
            st.markdown(f"_{event['description']}_")

            e_start = pd.to_datetime(event["start"])
            e_end = pd.to_datetime(event["end"])

            # Show wider window
            window_start = e_start - timedelta(days=30)
            window_end = min(e_end + timedelta(days=30), data_max)

            corridor_risk = risk_bt[
                (risk_bt["corridor_id"] == event["corridor"])
                & (risk_bt["date"] >= window_start)
                & (risk_bt["date"] <= window_end)
            ]

            if corridor_risk.empty:
                st.info(
                    f"No data for this period. "
                    f"(Data range: {data_min.date()} → {data_max.date()})"
                )
                continue

            # Plot with event window highlighted
            fig = go.Figure()

            fig.add_vrect(
                x0=event["start"], x1=event["end"],
                fillcolor="#ff3d00", opacity=0.15,
                line_width=0,
                annotation_text="Event Window",
                annotation_position="top left",
                annotation_font_color="#ff3d00",
            )

            fig.add_trace(go.Scatter(
                x=corridor_risk["date"],
                y=corridor_risk["risk_score"],
                mode="lines+markers",
                name="Risk Score",
                line=dict(color="#4fc3f7", width=2),
                marker=dict(size=4),
            ))

            fig.add_hline(y=70, line_dash="dash", line_color="#ff3d00", opacity=0.5)
            fig.add_hline(y=40, line_dash="dash", line_color="#ffd600", opacity=0.5)

            fig.update_layout(
                template=PLOT_TEMPLATE,
                height=350,
                yaxis_title="Risk Score",
                xaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, width='stretch')

            # Stats
            event_risk = corridor_risk[
                (corridor_risk["date"] >= e_start) & (corridor_risk["date"] <= e_end)
            ]
            pre_event = corridor_risk[corridor_risk["date"] < e_start]

            if not event_risk.empty:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Peak During Event", f"{event_risk['risk_score'].max():.0f}/100")
                with col2:
                    st.metric("Avg During Event", f"{event_risk['risk_score'].mean():.0f}/100")
                with col3:
                    pre_avg = pre_event["risk_score"].mean() if not pre_event.empty else 0
                    st.metric("Avg Before Event", f"{pre_avg:.0f}/100")
                with col4:
                    event_avg = event_risk["risk_score"].mean()
                    if not pre_event.empty and pre_avg > 5:
                        increase = ((event_avg - pre_avg) / pre_avg) * 100
                        st.metric("Signal Increase", f"{increase:+.0f}%")
                    elif pre_avg <= 5 and event_avg > 10:
                        st.metric("Signal Increase", f"0 → {event_avg:.0f}",
                                  delta="New risk", delta_color="inverse")
                    else:
                        st.metric("Signal Increase", "N/A")

                peak = event_risk["risk_score"].max()
                if peak >= 70:
                    st.success(f"✅ **DETECTED** — Risk score hit {peak:.0f}, above High Risk threshold.")
                elif peak >= 40:
                    st.warning(f"⚠️ **PARTIAL DETECTION** — Risk reached {peak:.0f} (Elevated).")
                else:
                    st.error(f"❌ **MISSED** — Peak was only {peak:.0f}. Thresholds or signals need tuning.")

    # ── Methodology ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Methodology")
    st.markdown(
        """
        **Signal Sources:**
        - **Price Anomaly Detection:** Rolling 60-day z-score on daily returns.
          Catches sudden spikes — e.g. Brent jumping 8% in a day.
        - **Price Level Detection:** Compares recent 10-day average price to 6-month baseline.
          Catches sustained elevated prices that z-scores adapt to — e.g. Brent staying at $100+ for weeks.
        - **Correlation Breakdown:** When normally-correlated assets in a corridor diverge
          (short-window vs long-window correlation delta > 0.5), structural change is flagged.
        - **News Spike Detection:** Daily article volume per corridor from GDELT,
          flagged when volume exceeds 1σ above the rolling mean.

        **Bilingual News Intelligence (Semiconductor Corridor):**
        The Semiconductor – Taiwan Strait corridor monitors headlines in both
        English and Traditional Chinese (台海危機, 台積電, 稀土出口, 晶片制裁, 半導體).
        GDELT indexes Chinese-language media, enabling detection of cross-strait
        supply chain signals that English-only systems miss.

        **Composite Risk Score:** Weighted sum of active signals, scaled 0–100.

        **Monitored Corridors:**
        - 🌾 **Grain – Black Sea:** Wheat/corn futures, UAH/USD, Brent crude, Ukraine/Black Sea headlines
        - ⛽ **Energy – Middle East / Red Sea:** Brent/natural gas futures, Iran/Hormuz/Suez headlines
        - 🏭 **Industrial – Asia-Pacific:** Copper, CNY/USD, Shanghai Composite, tariff headlines
        - 🔬 **Semiconductor – Taiwan Strait:** TSMC, SOXX, TWD/USD, rare earth ETF, bilingual CN/EN headlines

        **Limitations:** This is a prototype. Production deployment would require higher-frequency data,
        more sophisticated NLP (entity extraction, sentiment classification via transformer models),
        integration with physical supply chain data (port throughput, AIS vessel tracking, inventory levels),
        and real-time Bloomberg terminal feeds.
        """
    )

# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Supply Chain Radar  |  "
    "Financial signals → Operational intelligence  |  "
    "EN + 中文 bilingual news monitoring"
)
