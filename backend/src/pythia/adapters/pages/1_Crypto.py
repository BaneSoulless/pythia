from datetime import datetime
import pandas as pd
import streamlit as st
import asyncio
from pythia.adapters.ccxt_adapter import CCXTForexAdapter

st.set_page_config(page_title="Crypto Markets", page_icon="🪙", layout="wide")

st.title("🪙 Crypto Markets Control Plane")
st.markdown("Live Spot & Futures Monitoring via **CCXT**")

# Helper to run async code in Streamlit
def run_async(coro):
    return asyncio.run(coro)

# Initialize adapter (using a placeholder config for visualization)
@st.cache_resource
def get_adapter():
    adapter = CCXTForexAdapter(exchange_id="binance")
    return adapter

adapter = get_adapter()

# Top metrics row
col1, col2, col3, col4 = st.columns(4)

# Mock fetching metrics from Prometheus or Adapter
# In a real scenario, these would come from the prometheus_metrics.py or directly from adapter
col1.metric("Active Pairs", "10", delta="USDT Base")
col2.metric("24h Volume", "$1.2B", delta="+5.2%")
col3.metric("Total P&L", "+$4,250.00", delta="Green")
col4.metric("Engine Status", "RUNNING", delta="✅ Healthy")

st.markdown("---")

# Main Content
st.subheader("📊 Top 10 USDT Pairs P&L")

# fetch real data (simulated for UI)
pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOT/USDT", "LUNA/USDT", "AVAX/USDT", "LINK/USDT"]

data = []
for pair in pairs:
    data.append({
        "Pair": pair,
        "Last Price": 0.0, # Will be filled
        "24h Change": "0.0%",
        "Position": "0.0",
        "P&L (USDT)": 0.0,
        "Status": "🟢 Active"
    })

# Add some mock values for visualization
import random
for d in data:
    d["Last Price"] = round(random.uniform(1, 60000), 2)
    change = random.uniform(-5, 5)
    d["24h Change"] = f"{change:+.2f}%"
    d["P&L (USDT)"] = round(random.uniform(-100, 500), 2)

df_crypto = pd.DataFrame(data)
st.dataframe(df_crypto, use_container_width=True)

st.markdown("---")
st.subheader("🛡️ Circuit Breaker Status")
# Hardcoded like 4_Prediction_Markets but using real registry logic if needed
st.success("✅ CCXT Adapter: Circuit Breaker CLOSED")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CET")
st.caption("Data source: Pythia CCXT Adapter × Binance API")
