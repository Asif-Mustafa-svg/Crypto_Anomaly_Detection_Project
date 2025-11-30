Crypto Anomaly Detection System
A real-time crypto market monitoring pipeline that identifies abnormal price movements and volatility shifts in the BTC/USDT pair using live Binance WebSocket data. The system streams trade events (price, qty, ts, isBuyerMaker), processes them through a rolling analytical window, and applies statistical and machine-learning techniques to detect anomalies as they occur.
The architecture consists of three components:
streamer.py – captures live trades and stores them in a rolling buffer (last_trades)
analyzer.py – computes rolling statistics (mu, sigma, zscore), performs CUSUM drift detection (s_pos, s_neg, k, h), variance ratio testing (v1, v2, pval), and IsolationForest modeling (isolation_flag)
dashboard.py – visualizes live prices, rolling metrics, and anomaly alerts through Streamlit
All computation is coordinated via a continuously updated state/state.json file.
Tech Stack: Python, WebSocket-Client, NumPy, Pandas, SciPy, Scikit-Learn, Streamlit.
Summary:
This system demonstrates real-time data engineering, streaming analytics, statistical drift detection, and unsupervised ML for market surveillance and quantitative research.
