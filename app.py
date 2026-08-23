from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import ta
import yfinance as yf

st.set_page_config(
    page_title="Professional Stock & Commodity Screener",
    layout="wide",
    page_icon="📈",
)

# ---- इंडेक्स व कमॉडिटीनुसार शेअर्सची वर्गवारी ----
MARKET_SECTORS = {
    "NIFTY 50 (All Stocks)": [
        "ADANIENT.NS",
        "ADANIPORTS.NS",
        "APOLLOHOSP.NS",
        "ASIANPAINT.NS",
        "AXISBANK.NS",
        "BAJAJ-AUTO.NS",
        "BAJFINANCE.NS",
        "BAJAJFINSV.NS",
        "BPCL.NS",
        "BHARTIARTL.NS",
        "BRITANNIA.NS",
        "CIPLA.NS",
        "COALINDIA.NS",
        "DRREDDY.NS",
        "EICHERMOT.NS",
        "GRASIM.NS",
        "HCLTECH.NS",
        "HDFCBANK.NS",
        "HDFCLIFE.NS",
        "HEROMOTOCO.NS",
        "HINDALCO.NS",
        "HINDUNILVR.NS",
        "ICICIBANK.NS",
        "INDUSINDBK.NS",
        "INFY.NS",
        "ITC.NS",
        "JSWSTEEL.NS",
        "KOTAKBANK.NS",
        "LT.NS",
        "M&M.NS",
        "MARUTI.NS",
        "NESTLEIND.NS",
        "NTPC.NS",
        "ONGC.NS",
        "POWERGRID.NS",
        "RELIANCE.NS",
        "SBILIFE.NS",
        "SBIN.NS",
        "SUNPHARMA.NS",
        "TATACONSUM.NS",
        "TATAMOTORS.NS",
        "TATASTEEL.NS",
        "TCS.NS",
        "TECHM.NS",
        "TITAN.NS",
        "ULTRACEMCO.NS",
        "WIPRO.NS",
    ],
    "BANKNIFTY (All Stocks)": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "INDUSINDBK.NS",
        "BANKBARODA.NS",
        "PNB.NS",
        "AUBANK.NS",
        "FEDERALBNK.NS",
        "IDFCFIRSTB.NS",
        "BANDHANBNK.NS",
    ],
    "FINNIFTY (All Stocks)": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "SBIN.NS",
        "BAJFINANCE.NS",
        "BAJAJFINSV.NS",
        "HDFCLIFE.NS",
        "SBILIFE.NS",
        "CHOLAFIN.NS",
        "SHRIRAMFIN.NS",
        "MUTHOOTFIN.NS",
        "PFC.NS",
        "RECLTD.NS",
    ],
    "SENSEX 30": [
        "HDFCBANK.BO",
        "RELIANCE.BO",
        "ICICIBANK.BO",
        "INFY.BO",
        "TCS.BO",
        "ITC.BO",
        "LT.BO",
        "AXISBANK.BO",
        "SBIN.BO",
        "BHARTIARTL.BO",
        "KOTAKBANK.BO",
        "HINDUNILVR.BO",
        "M&M.BO",
        "MARUTI.BO",
        "SUNPHARMA.BO",
        "TATASTEEL.BO",
        "TITAN.BO",
        "BAJFINANCE.BO",
        "ASIANPAINT.BO",
        "NTPC.BO",
        "POWERGRID.BO",
        "ULTRACEMCO.BO",
        "NESTLEIND.BO",
        "TECHM.BO",
        "WIPRO.BO",
        "JSWSTEEL.BO",
        "TATAMOTORS.BO",
        "INDUSINDBK.BO",
        "BAJAJFINSV.BO",
        "HCLTECH.BO",
    ],
    "COMMODITY (Crude Oil & Gold)": [
        "CL=F",
        "GC=F",
        "MCX:CRUDEOIL",
        "MCX:GOLD",
        "GOLDBEES.NS",
    ],
}

# ---- SIDEBAR: सेटिंग्ज ----
st.sidebar.header("⚙️ स्कॅनर पॅरामीटर्स")

selected_market = st.sidebar.selectbox(
    "📊 इंडेक्स / कमॉडिटी निवडा:", list(MARKET_SECTORS.keys())
)
selected_stocks = MARKET_SECTORS[selected_market]

timeframe = st.sidebar.selectbox(
    "⏱️ Timeframe निवडा:",
    ["1m", "5m", "15m", "1h", "1d"],
    index=2,  # 15m default
)

selected_emas = st.sidebar.multiselect(
    "📈 EMA इंडिकेटर्स निवडा:",
    [9, 21, 50, 200],
    default=[9, 21, 50, 200],
)

check_sr = st.sidebar.checkbox(
    "🎯 Support & Resistance लेव्हल्स दाखवा", value=True
)

st.sidebar.markdown("---")
st.sidebar.subheader("✈️ Telegram अलर्ट सेटिंग")
tg_token = st.sidebar.text_input(
    "Bot Token",
    type="password",
    value="8799046332:AAEMln5lVcfrnzQ23ymg...",
)  # तुमचे बरोबर टोकन टाका
tg_chat_id = st.sidebar.text_input("Chat ID", value="5055029691")


def send_telegram(msg):
  if tg_token and tg_chat_id:
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
      requests.post(
          url,
          json={"chat_id": tg_chat_id, "text": msg, "parse_mode": "HTML"},
          timeout=5,
      )
    except Exception:
      pass


# ---- MAIN UI ----
st.title("📊 Multi-Asset Market Screener")
st.caption(
    f"सध्या निवडलेले: *{selected_market}* | टाईमफ्रेम: *{timeframe}*"
)

tab1, tab2 = st.tabs(
    ["⚡ त्वरित स्कॅन निकाल (Signals)", "🕯️ कॅन्डलस्टिक व S&R चार्ट"]
)

# डेटा फेच आणि कॅल्क्युलेशन फंक्शन
period_map = {"1m": "5d", "5m": "10d", "15m": "30d", "1h": "60d", "1d": "1y"}


@st.cache_data(ttl=60)
def fetch_and_calculate(symbol, tf):
  try:
    df = yf.download(
        symbol, period=period_map.get(tf, "30d"), interval=tf, progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = [col[0] for col in df.columns]
    if len(df) < 50:
      return None

    # EMA कॅल्क्युलेशन
    for ema in [9, 21, 50, 200]:
      df[f"EMA_{ema}"] = ta.trend.ema_indicator(df["Close"], window=ema)

    # Support & Resistance (मागील २० कँडल्सचा High/Low)
    df["Resistance"] = df["High"].rolling(20).max()
    df["Support"] = df["Low"].rolling(20).min()
    return df
  except Exception:
    return None


with tab1:
  if st.button("🔍 आता त्वरित स्कॅन करा (Instant Scan)"):
    results = []
    bar = st.progress(0)

    for idx, sym in enumerate(selected_stocks):
      bar.progress((idx + 1) / len(selected_stocks))
      df = fetch_and_calculate(sym, timeframe)
      if df is None or len(df) < 2:
        continue

      c_close = float(df["Close"].iloc[-1])
      p_close = float(df["Close"].iloc[-2])
      res_lvl = float(df["Resistance"].iloc[-2])
      sup_lvl = float(df["Support"].iloc[-2])

      signals = []

      # EMA ट्रिगर्स
      for ema in selected_emas:
        if f"EMA_{ema}" in df.columns:
          p_ema = float(df[f"EMA_{ema}"].iloc[-2])
          c_ema = float(df[f"EMA_{ema}"].iloc[-1])
          if p_close <= p_ema and c_close > c_ema:
            signals.append(f"🟢 Crossed Above {ema} EMA")
          elif p_close >= p_ema and c_close < c_ema:
            signals.append(f"🔴 Crossed Below {ema} EMA")

      # Support & Resistance ब्रेकआऊट
      if check_sr:
        if c_close > res_lvl and p_close <= res_lvl:
          signals.append("🚀 Resistance Breakout")
        elif c_close < sup_lvl and p_close >= sup_lvl:
          signals.append("⚠️ Support Breakdown")

      if signals:
        clean_name = (
            sym.replace(".NS", "")
            .replace(".BO", "")
            .replace("CL=F", "CRUDE OIL")
            .replace("GC=F", "GOLD")
        )
        results.append({
            "Asset / Stock": clean_name,
            "CMP (₹)": f"{c_close:.2f}",
            "Signals": " | ".join(signals),
            "Support (₹)": f"{sup_lvl:.2f}",
            "Resistance (₹)": f"{res_lvl:.2f}",
        })

    if results:
      res_df = pd.DataFrame(results)
      st.success(f"🎯 एकूण {len(results)} सिग्नल्स सापडले!")
      st.dataframe(res_df, use_container_width=True)
    else:
      st.info("या टाईमफ्रेमवर सध्या कोणताही नवीन सिग्नल मिळालेला नाही.")

with tab2:
  chart_sym = st.selectbox("शेअर/कमॉडिटी निवडा:", selected_stocks)
  df_chart = fetch_and_calculate(chart_sym, timeframe)

  if df_chart is not None:
    fig = go.Figure()
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],
            high=df_chart["High"],
            low=df_chart["Low"],
            close=df_chart["Close"],
            name="Price",
        )
    )

    # Selected EMAs
    colors = {9: "orange", 21: "blue", 50: "purple", 200: "red"}
    for ema in selected_emas:
      if f"EMA_{ema}" in df_chart.columns:
        fig.add_trace(
            go.Scatter(
                x=df_chart.index,
                y=df_chart[f"EMA_{ema}"],
                name=f"EMA {ema}",
                line=dict(color=colors.get(ema, "black"), width=1.5),
            )
        )

    # Support & Resistance Lines
    if check_sr:
      latest_res = df_chart["Resistance"].iloc[-1]
      latest_sup = df_chart["Support"].iloc[-1]
      fig.add_hline(
          y=latest_res,
          line_dash="dash",
          line_color="green",
          annotation_text=f"Resistance: {latest_res:.2f}",
      )
      fig.add_hline(
          y=latest_sup,
          line_dash="dash",
          line_color="red",
          annotation_text=f"Support: {latest_sup:.2f}",
      )

    fig.update_layout(
        title=f"{chart_sym} Technical Chart",
        xaxis_rangeslider_visible=False,
        height=550,
    )
    st.plotly_chart(fig, use_container_width=True)
