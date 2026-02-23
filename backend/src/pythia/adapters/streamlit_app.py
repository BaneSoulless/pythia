import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

import sqlite3
import os

DB_PATH = os.path.abspath(os.getenv("SQLITE_DB_PATH", "/app/data/pythia_prod.db"))

def fetch_mock_kpis():
    return {
        "balance": 50.0 + random.uniform(-5.0, 10.0),
        "pnl_pct": random.uniform(-1.5, 3.5),
        "win_rate": random.uniform(40.0, 75.0),
        "open_trades": random.randint(0, 3)
    }

def fetch_real_trades():
    """Query SQLite EventStore for recent trades from event_log."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    # Query the event_log table which uses JSON for data
    query = """
    SELECT created_at as Time, stream_id as Pair, event_type as Action, data 
    FROM event_log 
    WHERE event_type = 'trade.executed'
    ORDER BY id DESC LIMIT 20
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return df
        
    # Flatten JSON data for UI
    import json
    df['Confidence'] = df['data'].apply(lambda x: json.loads(x).get('confidence', 0.0) if isinstance(x, str) else x.get('confidence', 0.0))
    df['Price'] = df['data'].apply(lambda x: json.loads(x).get('price', 0.0) if isinstance(x, str) else x.get('price', 0.0))
    df['Action'] = df['data'].apply(lambda x: json.loads(x).get('action', 'HOLD') if isinstance(x, str) else x.get('action', 'HOLD'))
    df['Reason'] = df.apply(lambda row: f"Executed at {row['Price']}", axis=1)
    
    return df[['Time', 'Pair', 'Action', 'Confidence', 'Reason']]

def fetch_mock_signals():
    # Use real trades if available, otherwise mock for UI dev
    real_df = fetch_real_trades()
    if not real_df.empty:
        # Map columns to UI format
        real_df = real_df.rename(columns={
            "timestamp": "Time", "pair": "Pair", "action": "Action", 
            "confidence": "Confidence", "pnl": "Reason"
        })
        real_df['Reason'] = real_df['Reason'].apply(lambda x: f"PnL: {x}" if pd.notna(x) else "AI model derived technical consensus")
        return real_df
        
    actions = ["BUY", "SELL", "HOLD"]
    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    data = []
    for _ in range(5):
        c = random.random()
        act = random.choice(actions)
        if c < 0.5: act = "HOLD" # Confidence gate mock
            
        data.append({
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Pair": random.choice(pairs),
            "Action": act,
            "Confidence": round(c, 3),
            "Reason": "AI model derived technical consensus"
        })
    return pd.DataFrame(data)

st.set_page_config(page_title="PYTHIA Test Mode MVP", page_icon="🤖", layout="wide")
st.title("PYTHIA 🤖 Thread MVP Dashboard")

# Real-time Metrics
kpis = fetch_mock_kpis()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Virtual Balance", value=f"€{kpis['balance']:.2f}", delta=f"{kpis['pnl_pct']:.2f}%")
with col2:
    st.metric(label="Win Rate", value=f"{kpis['win_rate']:.1f}%")
with col3:
    st.metric(label="Open Trades", value=kpis['open_trades'])
with col4:
    st.metric(label="Active Strategy", value="Freqtrade + Groq MVP")

st.markdown("---")
st.subheader("Real-time Model Inference Signals")

def color_confidence(val):
    color = 'red'
    if val > 0.7:
        color = 'green'
    elif val >= 0.5:
        color = 'orange'
    return f'background-color: {color}; color: white; font-weight: bold'

def color_action(val):
    if val == "BUY": return 'color: green; font-weight: bold'
    if val == "SELL": return 'color: red; font-weight: bold'
    return 'color: gray'

df = fetch_mock_signals()
# Estetizzazione base per MVP Standalone
st.dataframe(
    df.style.map(color_confidence, subset=['Confidence'])
            .map(color_action, subset=['Action']),
    use_container_width=True,
    hide_index=True
)

st.caption("Auto-refreshing every 5 seconds. Connects directly to SQLite Test EventStore / Memory Idempotency cache.")

time.sleep(5)
st.rerun()
