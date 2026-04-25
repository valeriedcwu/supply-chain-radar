"""
Supply chain corridor definitions.

Each corridor maps financial/market signals to a real-world supply chain.
Thresholds are in z-score units (standard deviations from rolling mean).
"""

CORRIDORS = {
    "grain_black_sea": {
        "name": "Grain – Black Sea Corridor",
        "description": "Wheat and grain exports through Black Sea region",
        "lat": 44.0,
        "lon": 34.0,
        "market_signals": {
            "ZW=F": {  # CBOT Wheat futures
                "name": "Wheat Futures",
                "weight": 0.35,
                "direction": "up",  # price spike = stress
            },
            "UAHUSD=X": {  # Ukrainian Hryvnia
                "name": "UAH/USD",
                "weight": 0.20,
                "direction": "down",  # depreciation = stress
            },
            "ZC=F": {  # Corn futures
                "name": "Corn Futures",
                "weight": 0.20,
                "direction": "up",
            },
        },
        "fred_signals": {
            "DCOILBRENTEU": {  # Brent crude (shipping cost proxy)
                "name": "Brent Crude",
                "weight": 0.25,
                "direction": "up",
            },
        },
        "news_keywords": ["black sea", "ukraine grain", "odessa port", "grain corridor"],
        "alert_threshold": 1.8,  # composite z-score to trigger alert
    },
    "energy_middle_east": {
        "name": "Energy – Middle East / Red Sea",
        "description": "Oil and LNG through Suez Canal and Red Sea",
        "lat": 15.5,
        "lon": 42.0,
        "market_signals": {
            "BZ=F": {  # Brent crude futures
                "name": "Brent Crude Futures",
                "weight": 0.30,
                "direction": "up",
            },
            "NG=F": {  # Natural gas
                "name": "Natural Gas Futures",
                "weight": 0.20,
                "direction": "up",
            },
        },
        "fred_signals": {
            "DCOILBRENTEU": {
                "name": "Brent Crude (FRED)",
                "weight": 0.20,
                "direction": "up",
            },
        },
        "news_keywords": ["red sea", "houthi", "suez canal", "strait of hormuz", "middle east oil", "iran war", "iran oil", "hormuz closure"],
        "alert_threshold": 1.8,
    },
    "industrial_asia_pacific": {
        "name": "Industrial – Asia-Pacific",
        "description": "Manufacturing inputs and container shipping from East Asia",
        "lat": 31.2,
        "lon": 121.5,
        "market_signals": {
            "HG=F": {  # Copper futures
                "name": "Copper Futures",
                "weight": 0.30,
                "direction": "up",
            },
            "CNY=X": {  # Chinese Yuan
                "name": "CNY/USD",
                "weight": 0.20,
                "direction": "down",
            },
            "000001.SS": {  # Shanghai Composite (proxy for CN industrial)
                "name": "Shanghai Composite",
                "weight": 0.15,
                "direction": "down",  # drop = economic stress
            },
        },
        "fred_signals": {},
        "news_keywords": ["china tariff", "container shipping", "port congestion asia"],
        "alert_threshold": 1.8,
    },
    "semiconductor_taiwan": {
        "name": "Semiconductor – Taiwan Strait",
        "description": "Global chip supply chain centered on Taiwan and rare earth inputs",
        "lat": 24.5,
        "lon": 121.0,
        "market_signals": {
            "TSM": {  # TSMC ADR
                "name": "TSMC (ADR)",
                "weight": 0.30,
                "direction": "down",  # TSMC drop = chip supply stress
            },
            "SOXX": {  # iShares Semiconductor ETF
                "name": "Semiconductor ETF (SOXX)",
                "weight": 0.20,
                "direction": "down",
            },
            "TWD=X": {  # Taiwan Dollar
                "name": "TWD/USD",
                "weight": 0.20,
                "direction": "down",  # TWD depreciation = stress
            },
            "REMX": {  # VanEck Rare Earth ETF
                "name": "Rare Earth ETF (REMX)",
                "weight": 0.15,
                "direction": "up",  # rare earth price spike = supply stress
            },
        },
        "fred_signals": {},
        "news_keywords": [
            # English keywords
            "taiwan strait", "TSMC", "chip shortage", "semiconductor export controls",
            "rare earth export", "chip sanctions",
            # Chinese keywords (GDELT indexes Chinese media)
            "台海危機", "台積電", "稀土出口", "晶片制裁", "半導體",
        ],
        "alert_threshold": 1.8,
    },
}
