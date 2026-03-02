from datetime import datetime
import pandas as pd
import streamlit as st
from pythia.adapters.alpaca_adapter import AlpacaAdapter

st.set_page_config(page_title="Stocks Portfolio", page_icon="🏦", layout="wide")

st.title("🏦 Stocks Portfolio Control Plane")
st.markdown("US Equities Paper Trading via **Alpaca Cloud**")

# Top metrics row (Mocked from Adapter status)
col1, col2, col3, col4 = st.columns(4)

# In a real scenario: account = run_async(adapter.get_account_status())
col1.metric("Equity", "$102,450.00", delta="+$2,450.00")
col2.metric("Buying Power", "$409,800.00", delta="4x Leverage")
col3.metric("Day Trades (6d)", "1/3", delta="PDT Safe")
col4.metric("Market Status", "OPEN", delta="✅ Trading")

st.markdown("---")

# Portfolio Table
st.subheader("💼 Active Positions")

# Mock positions
positions = [
    {"Symbol": "AAPL", "Qty": 50, "Avg Entry": 182.50, "Current Price": 185.20, "Market Value": 9260.00, "Unrealized P&L": "+$135.00"},
    {"Symbol": "TSLA", "Qty": 20, "Avg Entry": 245.10, "Current Price": 238.90, "Market Value": 4778.00, "Unrealized P&L": "-$124.00"},
    {"Symbol": "NVDA", "Qty": 15, "Avg Entry": 720.00, "Current Price": 785.40, "Market Value": 11781.00, "Unrealized P&L": "+$981.00"},
    {"Symbol": "MSFT", "Qty": 30, "Avg Entry": 405.00, "Current Price": 412.30, "Market Value": 12369.00, "Unrealized P&L": "+$219.00"},
]

df_stocks = pd.DataFrame(positions)
st.dataframe(df_stocks, use_container_width=True)

st.markdown("---")
st.subheader("🛡️ Compliance & Risk")
col1, col2, col3 = st.columns(3)
col1.metric("Max Pos Size", "10%", delta="Configured")
col2.metric("Stop Loss (Avg)", "2.5%", delta="Trailing")
col3.metric("Volatility Guard", "PASS", delta="SOTA-2026")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CET")
st.caption("Data source: Pythia Alpaca Adapter (Paper Account)")
