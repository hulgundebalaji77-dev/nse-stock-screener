from datetime import datetime
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import ta
import yfinance as yf

# ================= 1. PAGE CONFIGURATION =================
st.set_page_config(
    page_title="Price vs EMA Screener & Telegram Alert", layout="wide"
)

# ================= 2. ALL SECTOR STOCKS =================
ALL_STOCKS = [
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "INDUSINDBK.NS",
    "BANKBARODA.NS",
    "PNB.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "TCS.NS",
    "INFY.NS",
    "HCLTECH.NS",
    "WIPRO.NS",
    "LTIM.NS",
    "TECHM.NS",
    "PERSISTENT.NS",
    "COFORGE.NS",
    "TATAMOTORS.NS",
    "M&M.NS",
    "MARUTI.NS",
    "BAJAJ-AUTO.NS",
    "HEROMOTOCO.NS",
    "EICHERMOT.NS",
    "TVSMOTOR.NS",
    "SUNPHARMA.NS",
    "DRREDDY.NS",
    "CIPLA.NS",
    "DIVISLAB.NS",
    "LUPIN.NS",
    "APOLLOHOSP.NS",
    "AUROPHARMA.NS",
    "ITC.NS",
    "HINDUNILVR.NS",
    "NESTLEIND.NS",
    "BRITANNIA.NS",
    "TATACONSUM.NS",
    "VBL.NS",
    "TITAN.NS",
    "DABUR.NS",
    "TATASTEEL.NS",
    "JSWSTEEL.NS",
    "HINDALCO.NS",
    "JINDALSTEL.NS",
    "VEDL.NS",
    "COALINDIA.NS",
    "RELIANCE.NS",
    "ONGC.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "BPCL.NS",
    "IOC.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "LT.NS",
    "ULTRACEMCO.NS",
    "GRASIM.NS",
    "DLF.NS",
    "GODREJPROP.NS",
    "AMBUJACEM.NS",
]


# ================= 3. TELEGRAM ALERT FUNCTION =================
def send_telegram_alert(bot_token, chat_id, message):
  if not bot_token or not chat_id:
    return {"ok": False, "description": "Token किंवा Chat ID भरलेला नाही"}
  url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
  payload = {
      "chat_id": str(chat_id).strip(),
      "text": message,
      "parse_mode": "HTML",
  }
  try:
    response = requests.post(url, json=payload, timeout=10)
    return response.json()
  except Exception as e:
    return {"ok": False, "description": str(e)}


# ================= 4. TECHNICAL INDICATORS =================
def calculate_all_indicators(df):
  df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
  df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
  df["EMA_50"] = ta.trend.ema_indicator(df["Close"], window=50)
  df["EMA_200"] = ta.trend.ema_indicator(df["Close"], window=200)
  df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
  return df


# ================= 5. EVALUATE PRICE VS EMA SIGNALS =================
def evaluate_stock_signals(df, active_filters):
  if df.empty or len(df) < 30:
    return None

  df = calculate_all_indicators(df)
  p_close = float(df["Close"].iloc[-2])
  c_close = float(df["Close"].iloc[-1])
  triggers = []

  # 1. Price vs 9 EMA
  if active_filters.get("price_ema_9") and pd.notna(df["EMA_9"].iloc[-1]):
    p_e9, c_e9 = float(df["EMA_9"].iloc[-2]), float(df["EMA_9"].iloc[-1])
    if p_close <= p_e9 and c_close > c_e9:
      triggers.append("🟢 Price Crossed ABOVE 9 EMA")
    elif p_close >= p_e9 and c_close < c_e9:
      triggers.append("🔴 Price Dropped BELOW 9 EMA")

  # 2. Price vs 21 EMA
  if active_filters.get("price_ema_21") and pd.notna(df["EMA_21"].iloc[-1]):
    p_e21, c_e21 = float(df["EMA_21"].iloc[-2]), float(df["EMA_21"].iloc[-1])
    if p_close <= p_e21 and c_close > c_e21:
      triggers.append("🟢 Price Crossed ABOVE 21 EMA")
    elif p_close >= p_e21 and c_close < c_e21:
      triggers.append("🔴 Price Dropped BELOW 21 EMA")

  # 3. Price vs 50 EMA
  if active_filters.get("price_ema_50") and pd.notna(df["EMA_50"].iloc[-1]):
    p_e50, c_e50 = float(df["EMA_50"].iloc[-2]), float(df["EMA_50"].iloc[-1])
    if p_close <= p_e50 and c_close > c_e50:
      triggers.append("🚀 Price Crossed ABOVE 50 EMA")
    elif p_close >= p_e50 and c_close < c_e50:
      triggers.append("🔻 Price Dropped BELOW 50 EMA")

  # 4. Price vs 200 EMA
  if active_filters.get("price_ema_200") and pd.notna(df["EMA_200"].iloc[-1]):
    p_e200, c_e200 = (
        float(df["EMA_200"].iloc[-2]),
        float(df["EMA_200"].iloc[-1]),
    )
    if p_close <= p_e200 and c_close > c_e200:
      triggers.append("🔥 Price Crossed ABOVE 200 EMA (Major Bullish)")
    elif p_close >= p_e200 and c_close < c_e200:
      triggers.append("⚠️ Price Dropped BELOW 200 EMA (Major Bearish)")

  if triggers:
    chg_pct = ((c_close - p_close) / p_close) * 100
    return {
        "Close": c_close,
        "Change_Pct": chg_pct,
        "RSI": (
            float(df["RSI"].iloc[-1]) if pd.notna(df["RSI"].iloc[-1]) else 0.0
        ),
        "Signals": " | ".join(triggers),
        "Raw_Signals": triggers,
    }
  return None


# ================= 6. SESSION STATE INITIALIZATION =================
if "auto_scan_active" not in st.session_state:
  st.session_state.auto_scan_active = False
if "sent_alerts" not in st.session_state:
  st.session_state.sent_alerts = set()
if "live_auto_table" not in st.session_state:
  st.session_state.live_auto_table = []
if "last_scan_time" not in st.session_state:
  st.session_state.last_scan_time = "कधीच नाही"

# ================= 7. LEFT SIDEBAR =================
st.sidebar.title("🎛️ Price vs EMA फिल्टर्स")
st.sidebar.caption("ज्या EMA वर किंमत गेल्यास अलर्ट हवा आहे ते सिलेक्ट करा:")

active_filters = {
    "price_ema_9": st.sidebar.checkbox(
        "⚡ Price Crossed 9 EMA (Above / Below)", value=True
    ),
    "price_ema_21": st.sidebar.checkbox(
        "📈 Price Crossed 21 EMA (Above / Below)", value=True
    ),
    "price_ema_50": st.sidebar.checkbox(
        "🚀 Price Crossed 50 EMA (Above / Below)", value=True
    ),
    "price_ema_200": st.sidebar.checkbox(
        "🔥 Price Crossed 200 EMA (Above / Below)", value=True
    ),
}

st.sidebar.markdown("---")
timeframe = st.sidebar.selectbox(
    "टाइमफ्रेम (Timeframe):", ["15m", "5m", "1h", "1d"], index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("✈️ Telegram अलर्ट सेटिंग")
tg_token = st.sidebar.text_input("Telegram Bot Token", type="password")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID")

# Telegram Test Button
if st.sidebar.button("📲 Test Telegram Alert"):
  if tg_token and tg_chat_id:
    test_msg = "<b>✅ Screener Test:</b>\nPrice vs EMA अलर्ट सक्रिय आहे!"
    res = send_telegram_alert(tg_token, tg_chat_id, test_msg)
    if res.get("ok"):
      st.sidebar.success("Telegram वर मेसेज आला आहे!")
    else:
      st.sidebar.error(f"त्रुटी: {res.get('description')}")
  else:
    st.sidebar.error("कृपया Bot Token आणि Chat ID प्रविष्ट करा.")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 ऑटो स्कॅनर सुरू करा"):
  if tg_token and tg_chat_id:
    st.session_state.auto_scan_active = True
    st.rerun()
  else:
    st.sidebar.error("कृपया आधी Bot Token आणि Chat ID टाका.")

if st.sidebar.button("⏹️ ऑटो स्कॅनर थांबवा"):
  st.session_state.auto_scan_active = False
  st.rerun()

# ================= 8. MAIN DASHBOARD =================
st.title("🎯 Price vs 9, 21, 50, 200 EMA Screener")
st.caption(
    "किंमत (Price) कोणत्याही निवडलेल्या EMA च्या वर गेल्यास (Breakout) किंवा"
    " खाली आल्यास थेट अलर्ट मिळतील."
)

tab1, tab2 = st.tabs(
    ["⚡ त्वरित स्कॅन निकाल (Filtered Signals)", "📈 सिलेक्टेड शेअरचा लाईव्ह चार्ट"]
)

with tab1:
  if st.button("🔍 आता त्वरित स्कॅन करा (Instant Scan)"):
    with st.spinner("सर्व शेअर्समधील EMA क्रॉसओव्हर स्कॅन होत आहेत..."):
      matched_stocks = []
      # 200 EMA साठी किमान 60 दिवसांचा डेटा आवश्यक असतो
      period_val = "60d" if timeframe in ["5m", "15m", "1h"] else "1y"
      for sym in ALL_STOCKS:
        try:
          df = yf.download(
              sym, period=period_val, interval=timeframe, progress=False
          )
          if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
          res = evaluate_stock_signals(df, active_filters)
          if res:
            matched_stocks.append({
                "स्टॉक (Stock)": sym,
                "किंमत (CMP)": f"₹{res['Close']:.2f}",
                "बदल (%)": f"{res['Change_Pct']:+.2f}%",
                "RSI (14)": f"{res['RSI']:.1f}",
                "मिळालेला सिग्नल": res["Signals"],
            })
        except Exception:
          continue

      if matched_stocks:
        st.success(
            f"🎯 एकूण {len(matched_stocks)} शेअर्समध्ये EMA क्रॉसओव्हर सिग्नल"
            " सापडले!"
        )
        st.dataframe(pd.DataFrame(matched_stocks), use_container_width=True)
      else:
        st.info(
            "सध्या कोणत्याही शेअरमध्ये निवडलेल्या EMA च्या वर/खाली जाण्याचा"
            " सिग्नल मिळालेला नाही."
        )

  st.markdown("---")
  st.subheader("📡 ऑटो-स्कॅनरद्वारे सापडलेले शेअर्स (Live Telegram Alerts)")

  if st.session_state.auto_scan_active:
    st.success(
        f"🟢 ऑटो-स्कॅनर सुरू आहे (शेवटचे स्कॅन: {st.session_state.last_scan_time}) |"
        f" Chat ID: {tg_chat_id}"
    )
  else:
    st.warning("⚪ ऑटो-स्कॅनर बंद आहे.")

  if st.session_state.live_auto_table:
    st.dataframe(
        pd.DataFrame(st.session_state.live_auto_table), use_container_width=True
    )
  else:
    st.caption("अद्याप कोणतेही नवीन लाईव्ह ऑटो-सिग्नल्स ट्रिगर झालेले नाहीत.")

with tab2:
  chart_ticker = st.selectbox("स्टॉक निवडा:", ALL_STOCKS)
  df_chart = yf.download(
      chart_ticker,
      period="1y" if timeframe == "1d" else "60d",
      interval=timeframe,
  )
  if not df_chart.empty:
    if isinstance(df_chart.columns, pd.MultiIndex):
      df_chart.columns = [col[0] for col in df_chart.columns]
    df_chart = calculate_all_indicators(df_chart)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )
    fig.add_trace(
        go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],
            high=df_chart["High"],
            low=df_chart["Low"],
            close=df_chart["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart.index,
            y=df_chart["EMA_9"],
            line=dict(color="blue", width=1.2),
            name="9 EMA",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart.index,
            y=df_chart["EMA_21"],
            line=dict(color="orange", width=1.2),
            name="21 EMA",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart.index,
            y=df_chart["EMA_50"],
            line=dict(color="green", width=1.3),
            name="50 EMA",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart.index,
            y=df_chart["EMA_200"],
            line=dict(color="red", width=1.5),
            name="200 EMA",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_chart.index,
            y=df_chart["RSI"],
            line=dict(color="purple", width=1.3),
            name="RSI",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.update_layout(
        height=650, template="plotly_white", xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ================= 9. AUTO-RUN LOOP =================
if st.session_state.auto_scan_active:
  now_time = datetime.now().strftime("%H:%M:%S")
  st.session_state.last_scan_time = now_time
  period_val = "60d" if timeframe in ["5m", "15m", "1h"] else "1y"

  with st.spinner(
      "किंमत EMA च्या वर/खाली जात आहे का हे तपासत आहे... (पुढील फेरी ३"
      " मिनिटांत होईल)"
  ):
    for sym in ALL_STOCKS:
      try:
        df = yf.download(
            sym, period=period_val, interval=timeframe, progress=False
        )
        if isinstance(df.columns, pd.MultiIndex):
          df.columns = [col[0] for col in df.columns]

        res = evaluate_stock_signals(df, active_filters)
        if res:
          today = datetime.now().strftime("%Y-%m-%d")
          alert_key = f"{sym}{today}{res['Raw_Signals'][0]}"

          if alert_key not in st.session_state.sent_alerts:
            tg_msg = (
                f"🚨 <b>PRICE vs EMA ALERT</b> 🚨\n\n"
                f"📈 <b>Stock:</b> {sym}\n"
                f"💰 <b>Price:</b> ₹{res['Close']:.2f} ({res['Change_Pct']:+.2f}%)\n"
                f"🎯 <b>Trigger:</b> {res['Signals']}\n"
                f"📊 <b>RSI:</b> {res['RSI']:.1f}\n"
                f"⏰ <b>Time:</b> {now_time}"
            )
            tg_res = send_telegram_alert(tg_token, tg_chat_id, tg_msg)
            st.session_state.sent_alerts.add(alert_key)
            st.session_state.live_auto_table.insert(
                0,
                {
                    "वेळ (Time)": now_time,
                    "स्टॉक (Stock)": sym,
                    "किंमत (CMP)": f"₹{res['Close']:.2f}",
                    "बदल (%)": f"{res['Change_Pct']:+.2f}%",
                    "RSI": f"{res['RSI']:.1f}",
                    "सिग्नल": res["Signals"],
                },
            )
      except Exception:
        continue

  time.sleep(180)
  st.rerun()
