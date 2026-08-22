from datetime import datetime
import time
import pandas as pd
import requests
import ta
import yfinance as yf

# Telegram डिटेल्स
TG_TOKEN = "तुमचा_TELEGRAM_BOT_TOKEN"
TG_CHAT_ID = "5055029691"

ALL_STOCKS = [
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "TCS.NS",
    "INFY.NS",
    "TATAMOTORS.NS",
    "M&M.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "CIPLA.NS",
    "ITC.NS",
    "HINDUNILVR.NS",
    "TATASTEEL.NS",
    "RELIANCE.NS",
    "LT.NS",
]

sent_alerts = set()


def send_telegram(msg):
  url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
  try:
    requests.post(
        url,
        json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=10,
    )
  except Exception:
    pass


def run_scanner_loop():
  start_time = time.time()
  # ५० मिनिटे अखंड लूप चालेल (दर ६० सेकंदांनी स्कॅन)
  while (time.time() - start_time) < 3000:
    now_str = datetime.now().strftime("%H:%M:%S")

    for sym in ALL_STOCKS:
      try:
        df = yf.download(sym, period="5d", interval="1m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
          df.columns = [col[0] for col in df.columns]
        if len(df) < 30:
          continue

        df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
        df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
        df["EMA_50"] = ta.trend.ema_indicator(df["Close"], window=50)
        df["EMA_200"] = ta.trend.ema_indicator(df["Close"], window=200)

        p_c, c_c = float(df["Close"].iloc[-2]), float(df["Close"].iloc[-1])
        p_e9, c_e9 = float(df["EMA_9"].iloc[-2]), float(df["EMA_9"].iloc[-1])
        p_e21, c_e21 = (
            float(df["EMA_21"].iloc[-2]),
            float(df["EMA_21"].iloc[-1]),
        )
        p_e50, c_e50 = (
            float(df["EMA_50"].iloc[-2]),
            float(df["EMA_50"].iloc[-1]),
        )

        triggers = []
        if p_c <= p_e9 and c_c > c_e9:
          triggers.append("🟢 Crossed ABOVE 9 EMA")
        if p_c <= p_e21 and c_c > c_e21:
          triggers.append("🟢 Crossed ABOVE 21 EMA")
        if p_c <= p_e50 and c_c > c_e50:
          triggers.append("🚀 Crossed ABOVE 50 EMA")

        if triggers:
          alert_key = f"{sym}{datetime.now().strftime('%Y%m%d%H%M')}"
          if alert_key not in sent_alerts:
            msg = (
                f"🚨 <b>1-MIN EMA ALERT</b> 🚨\n\n"
                f"📈 <b>Stock:</b> {sym}\n"
                f"💰 <b>CMP:</b> ₹{c_c:.2f}\n"
                f"🎯 <b>Trigger:</b> {' | '.join(triggers)}\n"
                f"⏰ <b>Time:</b> {now_str}"
            )
            send_telegram(msg)
            sent_alerts.add(alert_key)
      except Exception:
        continue

    time.sleep(60)  # १ मिनिटाचा ब्रेक


run_scanner_loop()
