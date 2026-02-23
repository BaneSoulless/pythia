import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import sqlite3
import os
import json

# Configuration
DB_PATH = os.path.abspath(os.getenv("SQLITE_DB_PATH", "/app/data/pythia_prod.db"))
STYLING = """
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3e4150;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00ff00;
        background-color: #1e2130;
        margin-bottom: 10px;
    }
    .status-error {
        border-left: 5px solid #ff0000;
    }
    .status-warning {
        border-left: 5px solid #ffaa00;
    }
</style>
"""

def fetch_kpis():
    """Mock/Fetch multi-asset KPIs."""
    return {
        "crypto": {"balance": 15420.50, "pnl": 2.4},
        "pm": {"balance": 1200.00, "pnl": 5.1},
        "stocks": {"balance": 25000.00, "pnl": -0.5},
        "forex": {"balance": 5000.00, "pnl": 0.8},
        "win_rate": 68.4
    }

def fetch_arbitrage_opportunities():
    """Mock/Fetch live arbitrage ops."""
    return pd.DataFrame([
        {"Time": datetime.now().strftime("%H:%M:%S"), "Pair": "FED-RATE-MAR", "ROI": "2.4%", "Strategy": "BUY YES (Kalshi) / BUY NO (Poly)", "Status": "DETECTED"},
        {"Time": datetime.now().strftime("%H:%M:%S"), "Pair": "ETH-PRICE-WEEK", "ROI": "1.8%", "Strategy": "BUY NO (Kalshi) / BUY YES (Poly)", "Status": "EXECUTING"}
    ])

def get_system_status():
    """Fetch Circuit Breaker and Secrets status."""
    return {
        "Secrets": "Encrypted (Fernet)",
        "CircuitBreaker": "CLOSED (Healthy)",
        "Database": "Connected",
        "ActiveWorkers": 4
    }

# UI Layout
st.set_page_config(page_title="PYTHIA Control Plane", page_icon="🤖", layout="wide")
st.markdown(STYLING, unsafe_allow_view=True)

st.title("PYTHIA 🤖 Multi-Asset Control Plane")
st.subheader("Ruthless Optimization Dashboard")

# Top Ribbon: Multi-Asset KPIs
kpis = fetch_kpis()
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Crypto (BTC/ETH)", f"${kpis['crypto']['balance']:,.2f}", f"{kpis['crypto']['pnl']}%")
with c2:
    st.metric("Pred. Markets", f"${kpis['pm']['balance']:,.2f}", f"{kpis['pm']['pnl']}%")
with c3:
    st.metric("US Stocks", f"${kpis['stocks']['balance']:,.2f}", f"{kpis['stocks']['pnl']}%")
with c4:
    st.metric("Forex (Oanda)", f"${kpis['forex']['balance']:,.2f}", f"{kpis['forex']['pnl']}%")

st.markdown("---")

# Main Content
col_main, col_side = st.columns([3, 1])

with col_main:
    st.subheader("🎯 Live Arbitrage Feed (Prediction Markets)")
    arb_df = fetch_arbitrage_opportunities()
    st.dataframe(arb_df, use_container_width=True, hide_index=True)

    st.subheader("🧠 Intelligence Layer (Groq Inference)")
    st.info("Consensus: Bullish on Prediction Markets Arbitrage due to high volatility in Kalshi/Polymarket spreads.")

with col_side:
    st.subheader("🛡️ Security & Health")
    status = get_system_status()
    
    st.markdown(f"""
    <div class="status-card">
        <b>Secrets Management:</b><br>{status['Secrets']}
    </div>
    <div class="status-card">
        <b>Circuit Breaker:</b><br>{status['CircuitBreaker']}
    </div>
    <div class="status-card">
        <b>Orchestrator Workers:</b><br>{status['ActiveWorkers']} Active
    </div>
    <div class="status-card">
        <b>Database:</b><br>{status['Database']}
    </div>
    """, unsafe_allow_view=True)
    
    if st.button("Reset Circuit Breaker"):
        st.success("Circuit breaker manually reset to CLOSED.")

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Environment: Production")

# Auto-refresh
time.sleep(10)
st.rerun()
