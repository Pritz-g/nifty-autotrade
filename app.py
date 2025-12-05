"""
Nifty AutoTrade Bot - Flask Webhook for TradingView → Angel One SmartAPI
Author: ChatGPT
 
IMPORTANT:
- Do NOT put API keys in this file
- Add them as Environment Variables in Render
"""
 
import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
 
# SmartAPI library
from smartapi import SmartConnect
 
 
# --------------- CONFIG ---------------
SMARTAPI_KEY_ENV = "SMARTAPI_KEY"
CLIENT_ID_ENV = "ANGEL_CLIENT_ID"
PASSWORD_ENV = "ANGEL_PASSWORD"
DRY_RUN_ENV = "DRY_RUN"  # true/false
DEFAULT_QTY = int(os.getenv("DEFAULT_QTY", "25"))
 
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
 
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nifty_autotrade")
 
app = Flask(__name__)
 
 
# --------------- SMARTAPI WRAPPER ---------------
class AngelClient:
    def __init__(self, api_key, client_id, password):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.client = SmartConnect(api_key=self.api_key)
        self.login()
 
    def login(self):
        logger.info("Logging in SmartAPI ...")
        try:
            session_data = self.client.generateSession(self.client_id, self.password)
            self.jwt_token = session_data["data"]["jwtToken"]
            logger.info("Login success")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
 
    def get_instruments(self):
        try:
            return self.client.get_instrument_for_fno()
        except Exception as e:
            logger.error("Failed to get instrument list: %s", e)
            return []
 
    def find_nifty_future(self):
        instruments = self.get_instruments()
        for inst in instruments:
            ts = inst.get("tradingsymbol", "")
            if "NIFTY" in ts and "FUT" in ts:
                logger.info(f"Instrument Selected: {inst}")
                return inst
        logger.error("NIFTY FUT instrument not found")
        return None
 
    def place_order(self, tradingsymbol, symboltoken, transactiontype, qty):
        payload = {
            "variety": "NORMAL",
            "tradingsymbol": tradingsymbol,
            "symboltoken": str(symboltoken),
            "transactiontype": transactiontype,
            "exchange": "NFO",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": 0,
            "quantity": qty
        }
 
        logger.info(f"ORDER REQUEST: {payload}")
 
        if os.getenv(DRY_RUN_ENV, "true").lower() == "true":
            logger.info("DRY-RUN MODE: No real trade executed")
            return {"status": "dry_run", "payload": payload}
 
        try:
            resp = self.client.placeOrder(**payload)
            logger.info(f"ORDER RESPONSE: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Order failed: {str(e)}")
            return {"status": "error", "error": str(e)}
 
 
# --------------- ROUTES ---------------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
 
 
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    logger.info(f"Webhook Received: {data}")
 
    signal = str(data.get("signal", "")).upper()
 
    if signal not in ["BUY", "SELL"]:
        logger.warning("Invalid or missing signal")
        return jsonify({"status": "ignored"}), 200
 
    api_key = os.getenv(SMARTAPI_KEY_ENV)
    client_id = os.getenv(CLIENT_ID_ENV)
    password = os.getenv(PASSWORD_ENV)
 
    if not api_key or not client_id or not password:
        return jsonify({"status": "error", "reason": "Missing API credentials"}), 500
 
    angel = AngelClient(api_key, client_id, password)
    inst = angel.find_nifty_future()
    if not inst:
        return jsonify({"status": "error", "reason": "Instrument not found"}), 500
 
    tradingsymbol = inst["tradingsymbol"]
    symboltoken = inst["token"]
    qty = int(data.get("qty", DEFAULT_QTY))
 
    resp = angel.place_order(tradingsymbol, symboltoken, signal, qty)
 
    return jsonify({"status": "ok", "signal": signal, "response": resp})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
