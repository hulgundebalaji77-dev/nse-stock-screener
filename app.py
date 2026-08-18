import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
import requests
import threading
import time
from datetime import datetime

# ================= 1. PAGE CONFIGURATION =================
st.set_page_config(page_title="All Sector Stocks Auto-Scanner & Alert", layout="wide")

# ================= 2. ALL SECTORS & THEIR STOCKS MAPPING =================
SECTOR_STOCKS = {
    "NIFTY BANK": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", 
        "AXISBANK.NS", "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "AUBANK.NS", "FEDERALBNK.NS"
    ],
    "NIFTY IT": [
        "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "LTIM.NS", 
        "TECHM.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS", "LTTS.NS"
    ],
    "NIFTY AUTO": [
        "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", 
        "EICHERMOT.NS", "TVSMOTOR.NS", "BHARATFORG.NS", "ASHOKLEY.NS", "BALKRISIND.NS"
    ],
    "NIFTY PHARMA": [
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS", 
        "AUROPHARMA.NS", "TORNTPHARM.NS", "ALKEM.NS", "ZYDUSLIFE.NS", "BIOCON.NS"
    ],
    "NIFTY FMCG": [
        "ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", 
        "DABUR.NS", "GODREJCP.NS", "MARICO.NS", "COLPAL.NS", "VBL.NS"
    ],
    "NIFTY METAL": [
        "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "JINDALSTEL.NS", "VEDL.NS", 
        "COALINDIA.NS", "NMDC.NS", "SAIL.NS", "NATIONALUM.NS", "APLAPOLLO.NS"
    ],
    "NIFTY ENERGY & OIL/GAS": [
        "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS", 
        "IOC.NS", "GAIL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ADANIGREEN.NS"
    ],
    "NIFTY REALTY & INFRA": [
        "DLF.NS", "GODREJPROP.NS", "LODHA.NS", "OBEROIRLTY.NS", "PHOENIXLTD.NS", 
        "LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "AMBUJACEM.NS", "SHREECEM.NS"
    ]
}

# Flatten list of all unique stocks
ALL_STOCKS_FLAT = sorted(list(set([stock for stocks in SECTOR_STOCKS.values() for stock in stocks])))

# ================= 3. SMS FUNCTION =================
def send_sms_alert(phone_number, message, api_key):
    if not api_key:
        return {"return": False, "message": "Missing API Key"}
    
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "authorization": api_key,
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": str(phone_number),
    }
    headers = {'cache-control': "no-cache"}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"return": False, "message": str(e)}

# ================= 4. TECHNICAL INDICATORS CALCULATION =================
def calculate_indicators(df):
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    
    df['Resistance'] = df['High'].rolling(window=20).max()
    df['Support'] = df['Low'].rolling(window=20).min()
    return df

# ================= 5. AUTO BACKGROUND SCANNER ENGINE =================
if "auto_scan_active" not in st.session_state:
    st.session_state.auto_scan_active = False
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()
if "scan_logs" not in st.session_state:
    st.session_state.scan_logs = []

def run_background_scanner(api_key, phone_no):
    while st.session_state.auto_scan_active:
        now_str = datetime.now().strftime("%H:%M:%S")
        for sym in ALL_STOCKS_FLAT:
            if not st.session_state.auto_scan_active:
                break
            try:
                df = yf.download(sym, period="5d", interval="15m", progress=False)
                if df.empty or len(df) < 30:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]

                df = calculate_indicators(df)

                p_e9, p_e21 = float(df['EMA_9'].iloc[-2]), float(df['EMA_21'].iloc[-2])
                c_e9, c_e21 = float(df['EMA_9'].iloc[-1]), float(df['EMA_21'].iloc[-1])
                p_macd, p_msig = float(df['MACD'].iloc[-2]), float(df['MACD_Signal'].iloc[-2])
                c_macd, c_msig = float(df['MACD'].iloc[-1]), float(df['MACD_Signal'].iloc[-1])
                curr_rsi = float(df['RSI'].iloc[-1])
                cmp_val = float(df['Close'].iloc[-1])

                triggers = []
                if (p_e9 <= p_e21) and (c_e9 > c_e21):
                    triggers.append("Bullish 9/21 EMA Cross")
                elif (p_e9 >= p_e21) and (c_e9 < c_e21):
                    triggers.append("Bearish 9/21 EMA Cross")

                if (p_macd <= p_msig) and (c_macd > c_msig):
                    triggers.append("MACD Buy Cross")

                if curr_rsi <= 30:
                    triggers.append(f"RSI Oversold ({curr_rsi:.1f})")
                elif curr_rsi >= 75:
                    triggers.append(f"RSI Overbought ({curr_rsi:.1f})")

                if triggers:
                    today = datetime.now().strftime("%Y-%m-%d")
                    alert_key = f"{sym}{today}{triggers[0]}"
                    if alert_key not in st.session_state.sent_alerts:
                        sms_msg = f"STOCK ALERT:\n{sym}\nPrice: ₹{cmp_val:.2f}\nRSI: {curr_rsi:.1f}\nTrigger: {', '.join(triggers)}"
                        res = send_sms_alert(phone_no, sms_msg, api_key)
                        if res.get("return"):
                            st.session_state.sent_alerts.add(alert_key)
                            st.session_state.scan_logs.insert(0, f"[{now_str}] ✅ SMS Sent: {sym} -> {', '.join(triggers)}")
            except Exception:
                continue

        # Wait 5 minutes between full scans
        time.sleep(300)

# ================= 6. SIDEBAR CONTROLS =================
st.sidebar.header("📊 स्टॉक निवड व ऑटो स्कॅनर")

selected_sector = st.sidebar.selectbox("सेक्टर निवडा (Select Sector):", list(SECTOR_STOCKS.keys()))
available_stocks = SECTOR_STOCKS[selected_sector]
selected_stock = st.sidebar.selectbox("स्टॉक निवडा (Select Stock):", available_stocks)

custom_ticker = st.sidebar.text_input("किंवा कस्टम स्टॉक टाका (उदा. TATAPOWER.NS):", value="")
active_ticker = custom_ticker.strip().upper() if custom_ticker else selected_stock

timeframe = st.sidebar.selectbox("टाइमफ्रेम (Timeframe)", ["5m", "15m", "1h", "1d", "1wk"], index=3)
period = st.sidebar.selectbox("कालावधी (Period)", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("📱 ऑटो SMS अलर्ट सेटिंग")
phone_no = st.sidebar.text_input("मोबाईल नंबर", value="8459958007")
api_key = st.sidebar.text_input("Fast2SMS API Key", type="password")

if st.sidebar.button("🚀 सर्व शेअर्स ऑटो स्कॅन सुरू करा"):
    if api_key:
        if not st.session_state.auto_scan_active:
            st.session_state.auto_scan_active = True
            threading.Thread(target=run_background_scanner, args=(api_key, phone_no), daemon=True).start()
            st.sidebar.success("सर्व सेक्टर शेअर्सचा ऑटो-स्कॅनर सुरू झाला!")
    else:
        st.sidebar.error("कृपया Fast2SMS API Key टाका.")

if st.sidebar.button("⏹️ ऑटो स्कॅनर बंद करा"):
    st.session_state.auto_scan_active = False
    st.sidebar.warning("ऑटो स्कॅनर थांबवले आहे.")

# ================= 7. APPLICATION TABS =================
tab1, tab2, tab3 = st.tabs(["📈 तांत्रिक चार्ट & सिग्नल्स", "⚡ सेक्टर शेअर्स लाइव्ह स्कॅनर", "📜 ऑटो SMS लॉग्ज"])

# ----------------- TAB 1: CHART -----------------
with tab1:
    st.subheader(f"📊 {active_ticker} - सविस्तर तांत्रिक चार्ट")
    data = yf.download(active_ticker, period=period, interval=timeframe)

    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]

        data = calculate_indicators(data)

        c_price = float(data['Close'].iloc[-1])
        p_price = float(data['Close'].iloc[-2])
        chg_pct = ((c_price - p_price) / p_price) * 100

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("किंमत (CMP)", f"₹{c_price:.2f}", f"{chg_pct:+.2f}%")
        c2.metric("RSI (14)", f"{data['RSI'].iloc[-1]:.1f}")
        c3.metric("MACD", f"{data['MACD'].iloc[-1]:.2f}")
        c4.metric("9 EMA", f"{data['EMA_9'].iloc[-1]:.2f}")
        c5.metric("21 EMA", f"{data['EMA_21'].iloc[-1]:.2f}")

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])

        # Panel 1: Price & Overlays
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_9'], line=dict(color='#2962FF', width=1.2), name="9 EMA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_21'], line=dict(color='#FF6D00', width=1.2), name="21 EMA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_200'], line=dict(color='#D50000', width=1.5), name="200 EMA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['BB_High'], line=dict(color='gray', dash='dash'), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['BB_Low'], line=dict(color='gray', dash='dash'), fill='tonexty', fillcolor='rgba(200,200,200,0.1)', name="BB Lower"), row=1, col=1)

        # Panel 2: Volume
        vol_colors = ['green' if c >= o else 'red' for c, o in zip(data['Close'], data['Open'])]
        fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=vol_colors, name="Volume"), row=2, col=1)

        # Panel 3: RSI & MACD
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.3), name="RSI (14)"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        fig.update_layout(height=750, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        if st.button("📲 थेट 8459958007 वर SMS पाठवा"):
            if api_key:
                res = send_sms_alert(phone_no, f"Test: {active_ticker} CMP: ₹{c_price:.2f} RSI: {data['RSI'].iloc[-1]:.1f}", api_key)
                if res.get("return"):
                    st.success("SMS यशस्वीरीत्या पाठवला गेला!")
                else:
                    st.error(f"SMS अयशस्वी: {res.get('message')}")
            else:
                st.error("कृपया API Key टाका.")
    else:
        st.error("डेटा लोड करता आला नाही.")

# ----------------- TAB 2: SECTOR STOCKS SCANNER -----------------
with tab2:
    st.subheader(f"⚡ {selected_sector} मधील सर्व शेअर्सची लाईव्ह स्थिती")
    if st.button(f"{selected_sector} चे सर्व शेअर्स स्कॅन करा"):
        with st.spinner("डेटा लोड होत आहे..."):
            stock_summary = []
            for stk in available_stocks:
                try:
                    df_stk = yf.download(stk, period="1mo", interval="1d", progress=False)
                    if not df_stk.empty:
                        if isinstance(df_stk.columns, pd.MultiIndex):
                            df_stk.columns = [col[0] for col in df_stk.columns]

                        df_stk = calculate_indicators(df_stk)
                        cp = float(df_stk['Close'].iloc[-1])
                        pp = float(df_stk['Close'].iloc[-2])
                        pct = ((cp - pp) / pp) * 100
                        rsi_v = float(df_stk['RSI'].iloc[-1])
                        e9 = float(df_stk['EMA_9'].iloc[-1])
                        e21 = float(df_stk['EMA_21'].iloc[-1])

                        stock_summary.append({
                            "स्टॉक (Symbol)": stk,
                            "CMP (किंमत)": f"₹{cp:.2f}",
                            "बदल (%)": f"{pct:+.2f}%",
                            "RSI (14)": f"{rsi_v:.1f}",
                            "9/21 EMA": "🟢 Bullish" if e9 > e21 else "🔴 Bearish"
                        })
                except Exception:
                    continue

            if stock_summary:
                st.dataframe(pd.DataFrame(stock_summary), use_container_width=True)

# ----------------- TAB 3: AUTO SMS LOGS -----------------
with tab3:
    st.subheader("📜 ऑटो-स्कॅनर रिअल-टाइम SMS लॉग्ज")
    if st.session_state.auto_scan_active:
        st.info("🟢 सर्व ८०+ सेक्टर शेअर्सचे ऑटो-स्कॅनिंग बॅकग्राउंडमध्ये चालू आहे...")
    else:
        st.warning("⚪ ऑटो-स्कॅनर बंद आहे. डाव्या साइडबारमधून '🚀 सर्व शेअर्स ऑटो स्कॅन सुरू करा' वर क्लिक करा.")

    if st.session_state.scan_logs:
        for l in st.session_state.scan_logs:
            st.text(l)
    else:
        st.caption("अद्याप कोणताही नवीन सिग्नल आलेला नाही.")
