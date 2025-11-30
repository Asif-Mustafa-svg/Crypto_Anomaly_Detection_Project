# app/streamer.py
import json
import time
import threading
from collections import deque
from websocket import WebSocketApp

import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "state.json")
os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)

# keep last N trades in memory
WINDOW_SIZE = 1000
trades = deque(maxlen=WINDOW_SIZE)

def write_state():
    # minimal state written for other components
    state = {
        "last_trades": list(trades),
        "timestamp": int(time.time()*1000)
    }
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)

def on_message(ws, message):
    msg = json.loads(message)
    # trade stream message for Binance: contains p (price), q (qty), T (trade time), m (isBuyerMaker)
    trade = {
        "price": float(msg.get("p") or msg.get("price") or 0.0),
        "qty": float(msg.get("q") or msg.get("qty") or 0.0),
        "ts": int(msg.get("T") or msg.get("trade_time") or time.time()*1000),
        "isBuyerMaker": bool(msg.get("m", False))
    }
    trades.append(trade)
    # write a compact state file every N messages to avoid I/O thrash
    if len(trades) % 10 == 0:
        write_state()

def on_error(ws, error):
    print("WS error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WS closed:", close_status_code, close_msg)

def on_open(ws):
    print("Connected to Binance stream.")

def run_stream(symbol="btcusdt"):
    # Binance trade stream: wss://stream.binance.com:9443/ws/btcusdt@trade
    url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@trade"
    ws = WebSocketApp(url,
                     on_open=on_open,
                     on_message=on_message,
                     on_error=on_error,
                     on_close=on_close)
    # run ws forever (blocking)
    ws.run_forever()

if __name__ == "__main__":
    try:
        run_stream("btcusdt")
    except KeyboardInterrupt:
        print("Streamer stopped.")
