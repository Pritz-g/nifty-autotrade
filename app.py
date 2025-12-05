"""
Nifty AutoTrade Bot - Flask Webhook for TradingView → Angel One SmartAPI
Author: ChatGPT
 
IMPORTANT:
- Do NOT put API keys in this file
- Add them as Environment Variables in Render
"""
import os
import json
from flask import Flask, request, jsonify
from SmartApi import SmartConnect
import pyotp
 
app = Flask(__name__)
 
# Read environment variables
CLIENT_ID = os.environ.get("SMART_CLIENT_ID")
API_KEY = os.environ.get("SMART_API_KEY")
PASSWORD = os.environ.get("SMART_PASSWORD")
TOTP_SECRET = os.environ.get("SMART_TOTP_SECRET")
SYMBOL_TOKEN = os.environ.get("SYMBOL_TOKEN", "999999")
EXCHANGE = "NFO"
QTY = int(os.environ.get("ORDER_QTY", 2))
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() == "false"
 
def smart_login():
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        return obj
    except Exception as e:
        print("Login Error:", e)
        return None
 
 
@app.route("/health")
def health():
    return "OK", 200
 
 
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Webhook received:", data)
 
    if not data or "signal" not in data:
        return jsonify({"error": "Invalid payload"}), 400
 
    signal = data["signal"].upper()
    order_type = "BUY" if signal == "BUY" else "SELL"
    
    if DRY_RUN:
        print(f"[DRY RUN] {order_type} {QTY}")
        return jsonify({"status": "DRY RUN", "order": order_type}), 200
 
    broker = smart_login()
    if not broker:
        return jsonify({"error": "Login failed"}), 500
    
    try:
        order_id = broker.placeOrder({
            "variety": "NORMAL",
            "tradingsymbol": SYMBOL_TOKEN,
            "symboltoken": SYMBOL_TOKEN,
            "transactiontype": order_type,
            "exchange": EXCHANGE,
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": QTY
        })
        print("Order ID:", order_id)
        return jsonify({"status": "success", "order_id": order_id}), 200
 
    except Exception as e:
        print("Order error:", e)
        return jsonify({"error": str(e)}), 500
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
