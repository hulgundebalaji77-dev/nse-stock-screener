from datetime import datetime
import time
import pandas as pd
import requests
import ta
import yfinance as yf

# तुमचे अचूक Telegram डिटेल्स
TG_TOKEN = "8799046332:AAHzWmvR1ZWJ-7ARzWgybFu-6Ykl7Trdt2k"
TG_CHAT_ID = "5055029691"
# सर्व इंडेक्स, शेअर्स आणि कमॉडिटी एकत्र
WATCHLIST = [
    # NIFTY 50 & BANKNIFTY & FINNIFTY Major Stocks
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "INDUSINDBK.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
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
    "BHARTIARTL.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "TITAN.NS",
    "JSWSTEEL.NS",
    "COALINDIA.NS",
    # Commodities
    "CL=F",  # Crude Oil
    "GC=F",  # Gold
    "GOLDBEES.NS",
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
  # ५० मिनिटे अविरत लूप
  while (time.time() - start_time) < 3000:
    now_str = datetime.now().strftime("%H:%M:%S")

    for sym in WATCHLIST:
      try:
        # १ मिनिटाच्या कँडलवर स्कॅनिंग
        df = yf.download(sym, period="5d", interval="1m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
          df.columns = [col[0] for col in df.columns]
        if len(df) < 50:
          continue

        for e in [9, 21, 50, 200]:
          df[f"EMA_{e}"] = ta.trend.ema_indicator(df["Close"], window=e)

        df["Res"] = df["High"].rolling(20).max()
        df["Sup"] = df["Low"].rolling(20).min()

        p_c, c_c = float(df["Close"].iloc[-2]), float(df["Close"].iloc[-1])
        res_lvl, sup_lvl = (
            float(df["Res"].iloc[-2]),
            float(df["Sup"].iloc[-2]),
        )

        triggers = []
        # EMA Breakouts
        for e in [9, 21, 50, 200]:
          if f"EMA_{e}" in df.columns:
            p_e, c_e = (
                float(df[f"EMA_{e}"].iloc[-2]),
                float(df[f"EMA_{e}"].iloc[-1]),
            )
            if p_c <= p_e and c_c > c_e:
              triggers.append(f"🟢 Crossed Above {e} EMA")
            elif p_c >= p_e and c_c < c_e:
              triggers.append(f"🔴 Crossed Below {e} EMA")

        # S&R Breakouts
        if c_c > res_lvl and p_c <= res_lvl:
          triggers.append("🚀 Resistance Breakout")
        elif c_c < sup_lvl and p_c >= sup_lvl:
          triggers.append("⚠️ Support Breakdown")

        if triggers:
          clean_name = (
              sym.replace(".NS", "")
              .replace("CL=F", "CRUDE OIL")
              .replace("GC=F", "GOLD")
          )
          alert_key = (
              f"{clean_name}{datetime.now().strftime('%Y%m%d%H%M')}_{triggers[0]}"
          )

          if alert_key not in sent_alerts:
            msg = (
                f"🚨 <b>MARKET AUTO ALERT</b> 🚨\n\n"
                f"📊 <b>Asset:</b> {clean_name}\n"
                f"💰 <b>Price:</b> ₹{c_c:.2f}\n"
                f"🎯 <b>Signal:</b> {' | '.join(triggers)}\n"
                f"🛡️ <b>S/R:</b> Sup ₹{sup_lvl:.2f} | Res ₹{res_lvl:.2f}\n"
                f"⏰ <b>Time:</b> {now_str}"
            )
            send_telegram(msg)
            sent_alerts.add(alert_key)
      except Exception:
        continue

    time.sleep(60)  # दर १ मिनिटाला स्कॅन


run_scanner_loop()
