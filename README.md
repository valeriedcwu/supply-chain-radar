# 🛰️ Supply Chain Radar

**Financial market signals as early warning for supply chain disruptions.**

Supply Chain Radar monitors commodity futures, FX rates, shipping indices, and news headlines across critical global corridors — detecting supply chain stress before it hits the physical world.

## Why Financial Signals?

Markets move before the physical world. When geopolitical tensions rise, commodity futures spike days before port throughput drops. When export controls shift, TSMC's stock reacts before a single chip shipment is delayed. This system turns that financial signal into operational intelligence.

## Monitored Corridors

| Corridor | Key Signals | News Language |
|---|---|---|
| 🌾 **Grain – Black Sea** | Wheat/corn futures, UAH/USD, Brent crude | English |
| ⛽ **Energy – Middle East / Red Sea** | Brent/natural gas futures, shipping indices | English |
| 🏭 **Industrial – Asia-Pacific** | Copper, CNY/USD, Shanghai Composite | English |
| 🔬 **Semiconductor – Taiwan Strait** | TSMC, SOXX, TWD/USD, rare earth ETF (REMX) | English + 中文 |

The Semiconductor corridor uses **bilingual news intelligence** — monitoring headlines in both English and Traditional Chinese (台海危機, 台積電, 稀土出口, 晶片制裁). This captures cross-strait supply chain signals that English-only systems miss.

## Detection Algorithms

1. **Price Anomaly Detection** — Rolling 60-day z-score on daily returns. Catches sudden shocks.
2. **Price Level Detection** — Compares 10-day average to 6-month baseline. Catches sustained elevated prices that z-scores adapt to.
3. **Correlation Breakdown** — Flags when normally-correlated assets diverge, indicating structural change.
4. **News Spike Detection** — Monitors GDELT article volume per corridor in English and Chinese.

Signals are weighted per corridor and aggregated into a composite risk score (0–100).

## Backtest Results

| Event | Corridor | Peak Score | Signal Increase | Result |
|---|---|---|---|---|
| 🇮🇷 Iran War / Hormuz Crisis (Feb–Apr 2026) | Energy | 100/100 | +206% | ✅ DETECTED |
| 🇺🇦 Black Sea Grain Volatility (Jun–Oct 2025) | Grain | 63/100 | 0→18 | ⚠️ PARTIAL |
| 🇹🇼 TSMC Export Controls (Aug 2025–Jan 2026) | Semiconductor | TBD | TBD | TBD |
| 🇨🇳 US-China Tariff Escalation (Jul–Dec 2025) | Industrial | 56/100 | +10% | ⚠️ PARTIAL |

## Architecture

```
Yahoo Finance / FRED            GDELT (EN + 中文)
         │                          │
         ▼                          ▼
   ┌──────────┐              ┌───────────┐
   │  Market   │              │   News    │
   │  Ingest   │              │  Ingest   │
   └────┬──────┘              └─────┬─────┘
        │                           │
        ▼                           ▼
   ┌──────────┐              ┌───────────┐
   │ Anomaly  │              │ NLP Event │
   │ Detector │              │ Classifier│
   │ (4 types)│              │           │
   └────┬──────┘              └─────┬─────┘
        │                           │
        └───────────┬───────────────┘
                    ▼
             ┌─────────────┐
             │ Risk Mapper  │
             │ (corridors)  │
             └──────┬───────┘
                    ▼
             ┌─────────────┐
             │  Streamlit   │
             │  Dashboard   │
             └─────────────┘
```

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/supply-chain-radar.git
cd supply-chain-radar
pip install -r requirements.txt

# Pull data
python -m data.ingest_market      # commodity futures, FX, ETFs
python -m data.ingest_news        # GDELT headlines (EN + 中文)

# Launch dashboard
streamlit run dashboard/app.py
```

Optional environment variables:
- `FRED_API_KEY` — for FRED macro indicators (free at https://fred.stlouisfed.org/docs/api/api_key.html)
- `NEWSAPI_KEY` — fallback news source if GDELT is unreliable

## Project Structure

```
supply-chain-radar/
├── config/
│   └── corridors.py          # Corridor definitions, tickers, weights, thresholds
├── data/
│   ├── ingest_market.py      # Yahoo Finance + FRED ingestion
│   └── ingest_news.py        # GDELT + NewsAPI ingestion (bilingual)
├── signals/
│   └── detector.py           # 4 detection algorithms
├── mapping/
│   └── risk_mapper.py        # Signal → corridor risk aggregation
├── dashboard/
│   └── app.py                # Streamlit dashboard (Live Monitor + Backtest)
├── .streamlit/
│   └── config.toml           # Dark theme
├── requirements.txt
├── run_pipeline.py           # One-command pipeline runner
└── README.md
```

## Future Improvements

- **Bloomberg integration** — Direct terminal feed for higher-frequency, higher-quality data
- **NLP sentiment classification** — Transformer-based event classification beyond volume counting
- **Physical supply chain data** — AIS vessel tracking, port throughput, inventory levels
- **Real-time alerting** — Push notifications via Slack/email when risk scores breach thresholds
- **Expanded bilingual coverage** — Japanese (日本語) for automotive supply chains, Korean (한국어) for memory chip corridors

## Built With

Python, Streamlit, Plotly, yfinance, GDELT, pandas, scikit-learn

---

*Built as a portfolio project demonstrating financial signal processing for operational intelligence.*
