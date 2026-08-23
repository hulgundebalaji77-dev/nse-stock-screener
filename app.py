from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import ta
import yfinance as yf

st.set_page_config(
    page_title="NEON PRO Market Screener",
    layout="wide",
    page_icon="🔥",
    initial_sidebar_state="expanded",
)

# ---- ULTRA COLOURFUL NEON CSS STYLING ----
st.markdown(
    """
<style>
    /* Dark Neon Background Glow */
    .stApp {
        background-color: #0d1117;
    }
    
    /* Neon Gradient Title */
    .neon-title {
        background: linear-gradient(135deg, #FF007A 0%, #7928CA 40%, #00F0FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.6rem;
        font-weight: 900;
        text-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
        margin-bottom: 0px;
    }
    .neon-subtitle {
        color: #58a6ff;
        font-size: 1rem;
        font-weight: 500;
        margin-bottom: 25px;
    }

    /* Colourful Vibrant Cards */
    .card-pink {
        background: linear-gradient(135deg, #1f1024 0%, #3b1238 100%);
        border: 1.5px solid #ff2a85;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 0 15px rgba(255, 42, 133, 0.25);
    }
    .card-cyan {
        background: linear-gradient(135deg, #091f2c 0%, #0c3345 100%);
        border: 1.5px solid #00f0ff;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.25);
    }
    .card-purple {
        background: linear-gradient(135deg, #17102b 0%, #291a4d 100%);
        border: 1.5px solid #a855f7;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 0 15px rgba(168, 85, 247, 0.25);
    }
    .card-green {
        background: linear-gradient(135deg, #0d2417 0%, #103d22 100%);
        border: 1.5px solid #00ff88;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.25);
    }
    
    .card-val-pink { font-size: 1.8rem; font-weight: 800; color: #ff66b2; }
    .card-val-cyan { font-size: 1.8rem; font-weight: 800; color: #38ef7d; }
    .card-val-purple { font-size: 1.8rem; font-weight: 800; color: #c084fc; }
    .card-val-green { font-size: 1.8rem; font-weight: 800; color: #00ff88; }
    .card-lbl { color: #c9d1d9; font-size: 0.85rem; text-transform: uppercase; font-weight: 600; margin-top: 4px; }

    /* Glowing Multi-colour Scan Button */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #ff007a 0%, #7928ca 50%, #00f0ff 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 1.1rem;
        border-radius: 12px;
        border: none;
        padding: 0.75rem 2.5rem;
        box-shadow: 0 0 20px rgba(255, 0, 122, 0.5);
        transition: all 0.3s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.8);
        color: #ffffff;
    }
</style>
""",
    unsafe_allow_html=True,
)

MARKET_SECTORS = {
    "🔥 NIFTY 50": [
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
    "🏦 BANKNIFTY": [
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
    "💳 FINNIFTY": [
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
    "🏛️ SENSEX 30": [
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
    "🛢️ COMMODITY (Crude & Gold)": [
        "CL=F",
        "GC=F",
        "MCX:CRUDEOIL",
        "MCX:GOLD",
        "GOLDBEES.NS",
    ],
}

# Sidebar
with st.sidebar:
  st.markdown("## 🌈 *कंट्रोल सेंटर*")
  selected_market = st.selectbox(
      "🎯 इंडेक्स / कमॉडिटी निवडा:", list(MARKET_SECTORS.keys())
  )
  selected_stocks = MARKET_SECTORS[selected_market]

  timeframe = st.select_slider(
      "⏱️ Timeframe:",
      options=["1m", "5m", "15m", "1h", "1d"],
      value="15m",
  )

  selected_emas = st.multiselect(
      "📈 EMA इंडिकेटर्स:", [9, 21, 50, 200], default=[9, 21, 50, 200]
  )

  check_sr = st.checkbox("🎯 Support & Resistance लेव्हल्स", value=True)

  st.markdown("---")
  st.markdown("### ✈️ Telegram बॉट सेटिंग")
  tg_token = st.text_input("Bot Token", type="password")
  tg_chat_id = st.text_input("Chat ID", value="5055029691")

# Main Header
st.markdown(
    '<div class="neon-title">⚡ ULTRA MARKET SCREENER</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="neon-subtitle">🚀 लाईव्ह मल्टि-ॲसेट स्कॅनिंग • <b>{selected_market}</b> • Timeframe: <b>{timeframe}</b></div>',
    unsafe_allow_html=True,
)

# 4 Neon Metric Cards
c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    f'<div class="card-pink"><div class="card-val-pink">{len(selected_stocks)}</div><div class="card-lbl">एकूण शेअर्स</div></div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="card-cyan"><div class="card-val-cyan">{timeframe}</div><div class="card-lbl">टाईमफ्रेम</div></div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="card-purple"><div class="card-val-purple">{len(selected_emas)} EMAs</div><div class="card-lbl">इंडिकेटर्स</div></div>',
    unsafe_allow_html=True,
)
c4.markdown(
    '<div class="card-green"><div class="card-val-green">24/7 LIVE</div><div class="card-lbl">क्लाउड स्टेटस</div></div>',
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(
    ["⚡ थेट ब्रेकआऊट सिग्नल्स (Live Signals)", "🕯️ मल्टिकलर निऑन चार्ट"]
)

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

    for ema in [9, 21, 50, 200]:
      df[f"EMA_{ema}"] = ta.trend.ema_indicator(df["Close"], window=ema)

    df["Resistance"] = df["High"].rolling(20).max()
    df["Support"] = df["Low"].rolling(20).min()
    return df
  except Exception:
    return None


with tab1:
  if st.button("🔥 आता त्वरित स्कॅन करा (Instant Scan)"):
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
      for ema in selected_emas:
        if f"EMA_{ema}" in df.columns:
          p_ema = float(df[f"EMA_{ema}"].iloc[-2])
          c_ema = float(df[f"EMA_{ema}"].iloc[-1])
          if p_close <= p_ema and c_close > c_ema:
            signals.append(f"🟢 BUY (Above {ema} EMA)")
          elif p_close >= p_ema and c_close < c_ema:
            signals.append(f"🔴 SELL (Below {ema} EMA)")

      if check_sr:
        if c_close > res_lvl and p_close <= res_lvl:
          signals.append("🚀 RESISTANCE BREAKOUT")
        elif c_close < sup_lvl and p_close >= sup_lvl:
          signals.append("⚠️ SUPPORT BREAKDOWN")

      if signals:
        clean_name = (
            sym.replace(".NS", "")
            .replace(".BO", "")
            .replace("CL=F", "CRUDE OIL")
            .replace("GC=F", "GOLD")
        )
        results.append({
            "Stock / Asset": clean_name,
            "CMP (₹)": f"₹{c_close:.2f}",
            "Technical Signals": "  |  ".join(signals),
            "Support (₹)": f"₹{sup_lvl:.2f}",
            "Resistance (₹)": f"₹{res_lvl:.2f}",
        })

    bar.empty()
    if results:
      res_df = pd.DataFrame(results)
      st.success(f"🎉 एकूण {len(results)} शेअर्समध्ये धमाकेदार सिग्नल्स मिळाले!")
      st.dataframe(res_df, use_container_width=True, hide_index=True)
    else:
      st.info("या टाइमफ्रेमवर सध्या कोणताही नवीन सिग्नल उपलब्ध नाही.")

with tab2:
  chart_sym = st.selectbox("📊 विश्लेषणासाठी शेअर निवडा:", selected_stocks)
  df_chart = fetch_and_calculate(chart_sym, timeframe)

  if df_chart is not None:
    fig = go.Figure()
    # Neon Style Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],
            high=df_chart["High"],
            low=df_chart["Low"],
            close=df_chart["Close"],
            name="कँडल्स",
            increasing_line_color="#00FF88",
            decreasing_line_color="#FF0055",
        )
    )

    # Vibrant Indicator Lines
    ema_colors = {
        9: "#FFE600",  # Bright Yellow
        21: "#00F0FF",  # Bright Cyan
        50: "#FF00AA",  # Bright Pink/Magenta
        200: "#B026FF",  # Bright Purple
    }

    for ema in selected_emas:
      if f"EMA_{ema}" in df_chart.columns:
        fig.add_trace(
            go.Scatter(
                x=df_chart.index,
                y=df_chart[f"EMA_{ema}"],
                name=f"EMA {ema}",
                line=dict(color=ema_colors.get(ema, "#FFFFFF"), width=2),
            )
        )

    if check_sr:
      latest_res = df_chart["Resistance"].iloc[-1]
      latest_sup = df_chart["Support"].iloc[-1]
      fig.add_hline(
          y=latest_res,
          line_dash="dash",
          line_color="#00E5FF",
          annotation_text=f"Res: ₹{latest_res:.2f}",
          annotation_font_color="#00E5FF",
      )
      fig.add_hline(
          y=latest_sup,
          line_dash="dash",
          line_color="#FF3366",
          annotation_text=f"Sup: ₹{latest_sup:.2f}",
          annotation_font_color="#FF3366",
      )

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        xaxis_rangeslider_visible=False,
        height=580,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
