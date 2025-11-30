# app/analyzer.py
import json
import time
import numpy as np
import os
from sklearn.ensemble import IsolationForest
from scipy import stats

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "state.json")

# parameters
ROLL_WINDOW = 120      # number of most recent trades to use for rolling stats
CUSUM_THRESHOLD = 4.0  # tweakable
IF_ESTIMATE_WINDOW = 500  # how many points to use to fit IsolationForest
IF_CONTAMINATION = 0.01   # fraction flagged as anomalies

def load_state():
    if not os.path.exists(STATE_PATH):
        return {"last_trades": [], "alerts": []}
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def write_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)

# Simple CUSUM (one-sided) for positive mean shifts
def cusum_detector(prices, k=0.5, h=5.0):
    # prices: list/array
    s_pos = 0.0
    s_neg = 0.0
    mu = np.mean(prices)
    sigma = np.std(prices) if np.std(prices) > 0 else 1.0
    alerts = []
    for i, x in enumerate(prices):
        # standardized increment
        z = (x - mu) / sigma
        s_pos = max(0.0, s_pos + z - k)
        s_neg = min(0.0, s_neg + z + k)
        if s_pos > h:
            alerts.append((i, "positive"))
            s_pos = 0.0
        if abs(s_neg) > h:
            alerts.append((i, "negative"))
            s_neg = 0.0
    return alerts

# Variance ratio test to detect volatility change (simple)
def variance_ratio_test(window1, window2):
    # test if var(window2) significantly different than var(window1) via F-test
    v1 = np.var(window1, ddof=1)
    v2 = np.var(window2, ddof=1)
    if v1 == 0 or v2 == 0:
        return 1.0  # p-value 1 => no change
    f = v2 / v1 if v2 > v1 else v1 / v2
    d1 = len(window2) - 1
    d2 = len(window1) - 1
    p = 1.0
    try:
        p = stats.f.cdf(f, d1, d2)
        # two-sided
        p_val = 2 * min(p, 1 - p)
    except Exception:
        p_val = 1.0
    return p_val

def run_loop(poll_interval=1.0):
    iso_model = None
    while True:
        state = load_state()
        trades = state.get("last_trades", [])
        prices = [t["price"] for t in trades]
        alerts = state.get("alerts", [])
        now_ts = int(time.time()*1000)

        if len(prices) >= 10:
            window = prices[-ROLL_WINDOW:]
            mu = float(np.mean(window))
            sigma = float(np.std(window))
            zscore = float((prices[-1] - mu) / (sigma if sigma>0 else 1.0))

            # CUSUM
            cusum_alerts = cusum_detector(window, k=0.5, h=CUSUM_THRESHOLD)

            # variance test: compare last half vs previous half
            half = len(window)//2
            if half > 5:
                pvar = variance_ratio_test(window[:half], window[half:])
            else:
                pvar = 1.0

            # Isolation Forest
            if len(prices) >= IF_ESTIMATE_WINDOW:
                # fit on the latest IF_ESTIMATE_WINDOW prices shaped as features
                X = np.array(prices[-IF_ESTIMATE_WINDOW:]).reshape(-1,1)
                iso_model = IsolationForest(contamination=IF_CONTAMINATION, random_state=42)
                iso_model.fit(X)

            isoflag = False
            if iso_model is not None:
                last_x = np.array([[prices[-1]]])
                pred = iso_model.predict(last_x)  # -1 anomaly, 1 normal
                isoflag = (pred[0] == -1)

            # Compose alert decision
            decision = {
                "ts": now_ts,
                "price": prices[-1],
                "mu": mu,
                "sigma": sigma,
                "zscore": zscore,
                "cusum_count": len(cusum_alerts),
                "variance_pval": pvar,
                "isolation_flag": bool(isoflag),
                "anomaly": bool(len(cusum_alerts) > 0 or pvar < 0.01 or isoflag)
            }

            # append to alerts log (keep last 200)
            alerts = alerts[-199:] if len(alerts) >= 199 else alerts
            if decision["anomaly"]:
                decision["note"] = "ANOMALY_DETECTED"
                alerts.append(decision)
                print("ALERT:", decision)
            else:
                # append last measurement for charting (optional)
                alerts.append({"ts": now_ts, "price": prices[-1], "anomaly": False})
                alerts = alerts[-200:]

            # write state
            state.update({
                "stats": {"mu": mu, "sigma": sigma, "zscore": zscore},
                "alerts": alerts,
                "last_update": now_ts
            })
            write_state(state)

        time.sleep(poll_interval)

if __name__ == "__main__":
    try:
        run_loop()
    except KeyboardInterrupt:
        print("Analyzer stopped.")
