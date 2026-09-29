"""Streamlit dashboard for the Gold Price Prediction System.

Run with: streamlit run src/dashboard/app.py
Expects the API to be running at http://localhost:8000 (see src/api/main.py).
"""
import os
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Gold Price Prediction", layout="wide")
st.title("🪙 Gold Price Prediction Dashboard")

# ---- Sidebar controls ----
st.sidebar.header("Settings")
days_ahead = st.sidebar.slider("Forecast horizon (days)", 1, 30, 1)
history_limit = st.sidebar.slider("History window (days)", 30, 1000, 180)

# ---- Fetch data ----
try:
    history_resp = requests.get(f"{API_BASE}/api/prices/history", params={"limit": history_limit}, timeout=10)
    history_resp.raise_for_status()
    history = pd.DataFrame(history_resp.json())
    history["date"] = pd.to_datetime(history["date"])
except Exception as e:
    st.error(f"Could not load price history from the API: {e}")
    st.stop()

try:
    pred_resp = requests.get(f"{API_BASE}/api/predict", params={"days_ahead": days_ahead}, timeout=10)
    pred_resp.raise_for_status()
    prediction = pred_resp.json()
except Exception as e:
    prediction = None
    st.warning(f"Prediction unavailable: {e}")

# ---- Metrics row ----
col1, col2, col3 = st.columns(3)
col1.metric("Latest Close", f"${history['close'].iloc[-1]:,.2f}")
if prediction:
    col2.metric(
        f"Predicted (+{days_ahead}d)",
        f"${prediction['predicted_price']:,.2f}",
        delta=f"{prediction['predicted_price'] - history['close'].iloc[-1]:.2f}",
    )
    col3.metric(
        "Confidence Range",
        f"${prediction['confidence_lower']:,.2f} – ${prediction['confidence_upper']:,.2f}",
    )

# ---- Chart ----
fig = go.Figure()
fig.add_trace(go.Scatter(x=history["date"], y=history["close"], name="Historical Close", mode="lines"))

if prediction:
    target_date = history["date"].max() + pd.Timedelta(days=days_ahead)
    fig.add_trace(go.Scatter(
        x=[target_date], y=[prediction["predicted_price"]],
        name="Prediction", mode="markers", marker=dict(size=12, color="red"),
    ))
    fig.add_trace(go.Scatter(
        x=[target_date, target_date],
        y=[prediction["confidence_lower"], prediction["confidence_upper"]],
        name="Confidence Interval", mode="lines", line=dict(color="red", dash="dot"),
    ))

fig.update_layout(title="Gold Price — History & Forecast", xaxis_title="Date", yaxis_title="Price (USD)")
st.plotly_chart(fig, use_container_width=True)

# ---- Model status ----
st.subheader("Model Status")
try:
    status_resp = requests.get(f"{API_BASE}/api/model/status", timeout=10)
    status_resp.raise_for_status()
    st.json(status_resp.json())
except Exception:
    st.info("No trained model status available yet — run `python -m src.models.train`.")
