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
    page_title="Custom Indicator Signal Screener & Telegram Alert",
    layout="wide",
)

# ================= 2. ALL SECTOR STOCKS =================
ALL_STOCKS = [
    # Banking & Financial Services
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
    # IT
    "TCS.NS",
    "INFY.NS",
    "HCLTECH.NS",
    "WIPRO.NS",
    "LTIM.NS",
    "TECHM.NS",
    "PERSISTENT.NS",
    "COFORGE.NS",
    # Auto
    "TATAMOTORS.NS",
    "M&M.NS",
    "MARUTI.NS",
    "BAJAJ-AUTO.NS",
    "HEROMOTOCO.NS",
    "EICHERMOT.NS",
    "TVSMOTOR.NS",
    # Pharma & Healthcare
    "SUNPHARMA.NS",
    "DRREDDY.NS",
    "CIPLA.NS",
    "DIVISLAB.NS",
    "LUPIN.NS",
    "APOLLOHOSP.NS",
    "AUROPHARMA.NS",
    # FMCG & Consumption
    "ITC.NS",
    "HINDUNILVR.NS",
    "NESTLEIND.NS",
    "BRITANNIA.NS",
    "TATACONSUM.NS",
    "VBL.NS",
    "TITAN.NS",
    "DABUR.NS",
    # Metal & Energy
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
    # Infra & Realty
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
def calculate_supertrend(df, period=10, multiplier=3):
  hl2 = (df["High"] + df["Low"]) / 2
  atr = ta.volatility.average_true_range(
      df["High"], df["Low"], df["Close"], window=period
  )
  up_band = hl2 - (multiplier * atr)
  low_band = hl2 + (multiplier * atr)

  supertrend = pd.Series(True, index=df.index)
  st_val = pd.Series(0.0, index=df.index)

  for i in range(1, len(df.index)):
    curr, prev = i, i - 1
    if df["Close"].iloc[curr] > low_band.iloc[prev]:
      supertrend.iloc[curr] = True
    elif df["Close"].iloc[curr] < up_band.iloc[prev]:
      supertrend.iloc[curr] = False
    else:
      supertrend.iloc[curr] = supertrend.iloc[prev]
      if supertrend.iloc[curr] and up_band.iloc[curr] < up_band.iloc[prev]:
        up_band.iloc[curr] = up_band.iloc[prev]
      if not supertrend.iloc[curr] and low_band.iloc[curr] > low_band.iloc[prev]:
        low_band.iloc[curr] = low_band.iloc[prev]
    st_val.iloc[curr] = (
        up_band.iloc[curr] if supertrend.iloc[curr] else low_band.iloc[curr]
    )
  return supertrend, st_val


def calculate_all_indicators(df):
  df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
  df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
  df["EMA_50"] = ta.trend.ema_indicator(df["Close"], window=50)
  df["EMA_200"] = ta.trend.ema_indicator(df["Close"], window=200)
  df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
  df["Stoch_RSI"] = ta.momentum.stochrsi(df["Close"], window=14) * 100

  macd = ta.trend.MACD(df["Close"])
  df["MACD"] = macd.macd()
  df["MACD_Signal"] = macd.macd_signal()

  bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
  df["BB_High"] = bb.bollinger_hband()
  df["BB_Low"] = bb.bollinger_lband()

  tp = (df["High"] + df["Low"] + df["Close"]) / 3
  df["VWAP"] = (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()
  df["Resistance_20"] = df["High"].rolling(window=20).max()
  df["Support_20"] = df["Low"].rolling(window=20).min()

  try:
    df["ST_Signal"], df["ST_Val"] = calculate_supertrend(df)
  except Exception:
    df["ST_Signal"] = True
    df["ST_Val"] = df["Close"]

  return df


# ================= 5. EVALUATE SIGNALS =================
def evaluate_stock_signals(df, active_filters):
  if df.empty or len(df) < 30:
    return None

  df = calculate_all_indicators(df)
  p_close = float(df["Close"].iloc[-2])
  c_close = float(df["Close"].iloc[-1])
  triggers = []

  # 1. 9/21 EMA Cross
  if active_filters.get("ema_9_21"):
    p_e9, p_e21 = float(df["EMA_9"].iloc[-2]), float(df["EMA_21"].iloc[-2])
    c_e9, c_e21 = float(df["EMA_9"].iloc[-1]), float(df["EMA_21"].iloc[-1])
    if p_e9 <= p_e21 and c_e9 > c_e21:
      triggers.append("🟢 9/21 EMA Golden Cross (Buy)")
    elif p_e9 >= p_e21 and c_e9 < c_e21:
      triggers.append("🔴 9/21 EMA Death Cross (Sell)")

  # 2. 50/200 EMA Cross
  if active_filters.get("ema_50_200"):
    p_e50, p_e200 = float(df["EMA_50"].iloc[-2]), float(df["EMA_200"].iloc[-2])
    c_e50, c_e200 = float(df["EMA_50"].iloc[-1]), float(df["EMA_200"].iloc[-1])
    if p_e50 <= p_e200 and c_e50 > c_e200:
      triggers.append("🚀 50/200 EMA Golden Cross (Bullish)")
    elif p_e50 >= p_e200 and c_e50 < c_e200:
      triggers.append("🔻 50/200 EMA Death Cross (Bearish)")

  # 3. Supertrend
  if active_filters.get("supertrend"):
    if df["ST_Signal"].iloc[-1] and not df["ST_Signal"].iloc[-2]:
      triggers.append("🟢 Supertrend Buy Signal")
    elif not df["ST_Signal"].iloc[-1] and df["ST_Signal"].iloc[-2]:
      triggers.append("🔴 Supertrend Sell Signal")

  # 4. MACD Crossover
  if active_filters.get("macd"):
    p_m, p_msig = float(df["MACD"].iloc[-2]), float(df["MACD_Signal"].iloc[-2])
    c_m, c_msig = float(df["MACD"].iloc[-1]), float(df["MACD_Signal"].iloc[-1])
    if p_m <= p_msig and c_m > c_msig:
      triggers.append("🟢 MACD Bullish Crossover")
    elif p_m >= p_msig and c_m < c_msig:
      triggers.append("🔴 MACD Bearish Crossover")

  # 5. RSI Extremes
  if active_filters.get("rsi"):
    curr_rsi = float(df["RSI"].iloc[-1])
    if curr_rsi <= 30:
      triggers.append(f"📉 RSI Oversold ({curr_rsi:.1f})")
    elif curr_rsi >= 70:
      triggers.append(f"📈 RSI Overbought ({curr_rsi:.1f})")

  # 6. Bollinger Bands Breakout
  if active_filters.get("bollinger"):
    bb_high = float(df["BB_High"].iloc[-1])
    bb_low = float(df["BB_Low"].iloc[-1])
    if c_close > bb_high:
      triggers.append("🚀 Upper Bollinger Breakout")
    elif c_close < bb_low:
      triggers.append("🔻 Lower Bollinger Breakdown")

  # 7. VWAP Breakout
  if active_filters.get("vwap"):
    vwap_val = float(df["VWAP"].iloc[-1])
    p_vwap = float(df["VWAP"].iloc[-2])
    if p_close <= p_vwap and c_close > vwap_val:
      triggers.append("🟡 Crossed Above VWAP")
    elif p_close >= p_vwap and c_close < vwap_val:
      triggers.append("⚠️ Dropped Below VWAP")

  if triggers:
    chg_pct = ((c_close - p_close) / p_close) * 100
    return {
        "Close": c_close,
        "Change_Pct": chg_pct,
        "RSI": float(df["RSI"].iloc[-1]),
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
st.sidebar.title("🎛️ इंडिकेटर्स फिल्टर्स")
active_filters = {
    "ema_9_21": st.sidebar.checkbox("9/21 EMA Crossover", value=True),
    "supertrend": st.sidebar.checkbox("Supertrend (10, 3)", value=True),
    "macd": st.sidebar.checkbox("MACD Crossover", value=True),
    "rsi": st.sidebar.checkbox(
        "RSI (Oversold < 30 / Overbought > 70)", value=True
    ),
    "bollinger": st.sidebar.checkbox("Bollinger Bands Breakout", value=True),
    "vwap": st.sidebar.checkbox("VWAP Cross (Above / Below)", value=False),
    "ema_50_200": st.sidebar.checkbox(
        "50/200 EMA (Golden / Death Cross)", value=False
    ),
}

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
    test_msg = "<b>✅ Screener Alert Test:</b>\nTelegram Bot अलर्ट व्यवस्थित सुरू आहे!"
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
    st.sidebar.error("कृपया Bot Token आणि Chat ID टाका.")

if st.sidebar.button("⏹️ ऑटो स्कॅनर थांबवा"):
  st.session_state.auto_scan_active = False
  st.rerun()

# ================= 8. MAIN DASHBOARD =================
st.title("🎯 केवळ सिग्नल देणारे शेअर्स (Signal-Only Scanner)")
tab1, tab2 = st.tabs(
    ["⚡ त्वरित स्कॅन निकाल (Filtered Signals)", "📈 सिलेक्टेड शेअरचा लाईव्ह चार्ट"]
)

with tab1:
  if st.button("🔍 आता त्वरित स्कॅन करा (Instant Scan)"):
    with st.spinner("स्कॅनिंग सुरू आहे..."):
      matched_stocks = []
      for sym in ALL_STOCKS:
        try:
          df = yf.download(sym, period="5d", interval=timeframe, progress=False)
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
            f"🎯 एकूण {len(matched_stocks)} शेअर्समध्ये सिग्नल्स सापडले आहेत!"
        )
        st.dataframe(pd.DataFrame(matched_stocks), use_container_width=True)
      else:
        st.info("सध्या कोणत्याही शेअरमध्ये सिग्नल तयार झालेला नाही.")

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
  df_chart = yf.download(chart_ticker, period="3mo", interval=timeframe)
  if not df_chart.empty:
    if isinstance(df_chart.columns, pd.MultiIndex):
      df_chart.columns = [col[0] for col in df_chart.columns]
    df_chart = calculate_all_indicators(df_chart)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
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

  with st.spinner("ऑटो-स्कॅनिंग सुरू आहे... (पुढील फेरी ३ मिनिटांत होईल)"):
    for sym in ALL_STOCKS:
      try:
        df = yf.download(sym, period="5d", interval=timeframe, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
          df.columns = [col[0] for col in df.columns]

        res = evaluate_stock_signals(df, active_filters)
        if res:
          today = datetime.now().strftime("%Y-%m-%d")
          alert_key = f"{sym}{today}{res['Raw_Signals'][0]}"

          if alert_key not in st.session_state.sent_alerts:
            tg_msg = (
                f"🚨 <b>SIGNAL ALERT</b> 🚨\n\n"
                f"📈 <b>Stock:</b> {sym}\n"
                f"💰 <b>Price:</b> ₹{res['Close']:.2f} ({res['Change_Pct']:+.2f}%)\n"
                f"📊 <b>RSI:</b> {res['RSI']:.1f}\n"
                f"🎯 <b>Trigger:</b> {res['Signals']}\n"
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
