from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Prediction Markets", page_icon="🔮", layout="wide")

st.title("🔮 Prediction Markets Control Plane")
st.markdown("Cross-platform arbitrage detection: **Kalshi** × **Polymarket**")


# Metrics from Prometheus
def fetch_prometheus_metric(query):
    try:
        response = requests.get(
            "http://prometheus:9090/api/v1/query", params={"query": query}, timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("result"):
                return data["data"]["result"]
        return []
    except Exception as e:
        st.error(f"Prometheus error: {e}")
        return []


# Top metrics row
col1, col2, col3, col4 = st.columns(4)

# Arbitrage opportunities (24h)
arb_data = fetch_prometheus_metric(
    "increase(pythia_arbitrage_opportunities_total[24h])"
)
arb_count = sum(float(r["value"][1]) for r in arb_data if "value" in r) if arb_data else 0
col1.metric("Arbitrage Opportunities (24h)", f"{int(arb_count)}", delta="Live scanning")

# Average ROI
roi_data = fetch_prometheus_metric(
    "histogram_quantile(0.5, pythia_arbitrage_roi_percent_bucket)"
)
avg_roi = 0.0
if roi_data and isinstance(roi_data, list) and len(roi_data) > 0:
    val = roi_data[0].get("value")
    if isinstance(val, list) and len(val) > 1:
        try:
            val_float = float(val[1])
            if not pd.isna(val_float):
                avg_roi = val_float
        except ValueError:
            pass
col2.metric(
    "Average ROI (P50)", f"{avg_roi:.2f}%", delta="+Good" if avg_roi > 1.5 else "Low"
)

# Platform balances
kalshi_balance = fetch_prometheus_metric(
    "pythia_prediction_market_balance_usdc{platform='kalshi'}"
)
poly_balance = fetch_prometheus_metric(
    "pythia_prediction_market_balance_usdc{platform='polymarket'}"
)
total_balance = 0.0
if kalshi_balance and len(kalshi_balance) > 0 and "value" in kalshi_balance[0]:
    total_balance += float(kalshi_balance[0]["value"][1])
if poly_balance and len(poly_balance) > 0 and "value" in poly_balance[0]:
    total_balance += float(poly_balance[0]["value"][1])

col3.metric("Total Balance", f"${total_balance:,.2f}", delta="USDC")

# Circuit breaker state
cb_data = fetch_prometheus_metric("pythia_circuit_breaker_state")
cb_open = any(r["metric"].get("state") == "OPEN" for r in cb_data) if cb_data else False
col4.metric(
    "Circuit Breaker",
    "OPEN" if cb_open else "CLOSED",
    delta="⚠️ Fault" if cb_open else "✅ Healthy",
)

st.markdown("---")

# Charts row
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Platform Balances Over Time")

    # Query last 6 hours of balance data
    kalshi_series = fetch_prometheus_metric(
        "pythia_prediction_market_balance_usdc{platform='kalshi'}[6h]"
    )
    poly_series = fetch_prometheus_metric(
        "pythia_prediction_market_balance_usdc{platform='polymarket'}[6h]"
    )

    if kalshi_series or poly_series:
        # Create DataFrame for plotting
        data = []

        if kalshi_series and len(kalshi_series) > 0 and "values" in kalshi_series[0]:
            for timestamp, value in kalshi_series[0]["values"]:
                data.append(
                    {
                        "Time": datetime.fromtimestamp(float(timestamp)),
                        "Platform": "Kalshi",
                        "Balance": float(value),
                    }
                )

        if poly_series and len(poly_series) > 0 and "values" in poly_series[0]:
            for timestamp, value in poly_series[0]["values"]:
                data.append(
                    {
                        "Time": datetime.fromtimestamp(float(timestamp)),
                        "Platform": "Polymarket",
                        "Balance": float(value),
                    }
                )

        if data:
            df = pd.DataFrame(data)
            fig = px.line(
                df,
                x="Time",
                y="Balance",
                color="Platform",
                title="USDC Balance by Platform",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No balance data available yet")
    else:
        st.info("Waiting for balance data...")

with col2:
    st.subheader("📈 ROI Distribution")

    # Query ROI histogram
    roi_buckets = fetch_prometheus_metric("pythia_arbitrage_roi_percent_bucket")

    if roi_buckets:
        # Parse histogram buckets
        buckets_data = []
        for bucket in roi_buckets:
            le = bucket["metric"].get("le", "inf")
            if le != "+Inf":
                count = float(bucket["value"][1]) if "value" in bucket else 0
                buckets_data.append({"ROI %": f"{le}%", "Opportunities": count})

        if buckets_data:
            df = pd.DataFrame(buckets_data)
            fig = px.bar(
                df, x="ROI %", y="Opportunities", title="Arbitrage ROI Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ROI distribution data yet")
    else:
        st.info("Waiting for arbitrage opportunities...")

st.markdown("---")

# Recent arbitrage opportunities table
st.subheader("🎯 Recent Arbitrage Opportunities")

# Mock data (in production, fetch from backend API)
opportunities = [
    {
        "Timestamp": "2026-02-23 08:30:15",
        "Event": "Fed Rate Hike March 2026",
        "Kalshi YES": "$0.42",
        "Polymarket NO": "$0.56",
        "Total Cost": "$0.98",
        "Profit": "$0.02",
        "ROI": "2.04%",
        "Status": "🟢 Active",
    },
    {
        "Timestamp": "2026-02-23 08:25:42",
        "Event": "Bitcoin >$100K by June 2026",
        "Kalshi YES": "$0.38",
        "Polymarket NO": "$0.59",
        "Total Cost": "$0.97",
        "Profit": "$0.03",
        "ROI": "3.09%",
        "Status": "🟢 Active",
    },
    {
        "Timestamp": "2026-02-23 08:20:11",
        "Event": "US Recession in 2026",
        "Kalshi YES": "$0.31",
        "Polymarket NO": "$0.67",
        "Total Cost": "$0.98",
        "Profit": "$0.02",
        "ROI": "2.04%",
        "Status": "⏸️ Expired",
    },
]

df_opp = pd.DataFrame(opportunities)
st.dataframe(df_opp, use_container_width=True)

# Live market scanner status
st.markdown("---")
st.subheader("🔄 Live Market Scanner")

col1, col2, col3 = st.columns(3)

markets_scanned = fetch_prometheus_metric("pythia_markets_scanned_total")
kalshi_scanned = (
    sum(
        float(r["value"][1])
        for r in markets_scanned
        if r["metric"].get("platform") == "kalshi" and "value" in r
    )
    if markets_scanned
    else 0
)

poly_scanned = (
    sum(
        float(r["value"][1])
        for r in markets_scanned
        if r["metric"].get("platform") == "polymarket" and "value" in r
    )
    if markets_scanned
    else 0
)

col1.metric("Kalshi Markets Scanned", f"{int(kalshi_scanned)}")
col2.metric("Polymarket Markets Scanned", f"{int(poly_scanned)}")
col3.metric("Scan Interval", "5 minutes")

# Circuit breaker details
st.markdown("---")
st.subheader("🛡️ Circuit Breaker Status")

cb_failures = fetch_prometheus_metric("pythia_circuit_breaker_failures_total")
if cb_failures:
    cb_df = pd.DataFrame(
        [
            {
                "Platform": r["metric"].get("platform", "unknown"),
                "Total Failures": int(float(r["value"][1])) if "value" in r else 0,
            }
            for r in cb_failures
        ]
    )
    st.dataframe(cb_df, use_container_width=True)
else:
    st.success("✅ No circuit breaker failures detected")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CET")
st.caption("Data source: Prometheus @ http://prometheus:9090")
