# app/dashboard.py
import streamlit as st
import json
import time
import pandas as pd
import os
from datetime import datetime

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "state.json")

st.set_page_config(page_title="Crypto Anomaly — BTC/USDT Live", layout="wide")
st.title("Crypto Anomaly — BTC/USDT Live")

placeholder = st.empty()

def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        return {}

while True:
    state = load_state()
    trades = state.get("last_trades", [])[-500:]
    alerts = state.get("alerts", [])[-50:]
    stats = state.get("stats", {})
    last_update = state.get("last_update", None)

    # prepare price series
    df = pd.DataFrame(trades)
    if not df.empty:
        df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')
        df = df.set_index('ts_dt')
        price_series = df['price']

    with placeholder.container():
        col1, col2 = st.columns([3,1])
        with col1:
            st.subheader("Price (latest 500 trades)")
            if not df.empty:
                st.line_chart(price_series)
            else:
                st.write("Waiting for trades...")

        with col2:
            st.subheader("Latest Stats")
            st.metric("Last Price", f"{trades[-1]['price']:.2f}" if trades else "—")
            st.write("μ (rolling):", stats.get("mu", "—"))
            st.write("σ (rolling):", stats.get("sigma", "—"))
            st.write("z-score:", round(stats.get("zscore", 0), 3))
            st.write("Last update:", datetime.utcfromtimestamp(last_update/1000).strftime("%Y-%m-%d %H:%M:%S") if last_update else "—")
            st.markdown("---")
            st.subheader("Recent Alerts")
            if alerts:
                alert_df = pd.DataFrame(alerts)[['ts','price','anomaly']]
                alert_df['ts'] = pd.to_datetime(alert_df['ts'], unit='ms')
                st.table(alert_df.sort_values('ts', ascending=False).head(10))
            else:
                st.write("No alerts yet.")

    time.sleep(2)
