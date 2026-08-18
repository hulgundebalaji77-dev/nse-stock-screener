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
st.set_page_config(page_title="NSE Pro Auto-Scanner & Alert System", layout="wide")

# ================= 2. MASTER SECTORAL INDICES =================
ALL_SECTORS = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY FINANCIAL SERVICES": "NIFTY_FIN_SERVICE.NS",
    "NIFTY MIDCAP 100": "^NSEMDCP50",
    "NIFTY SMALLCAP 100": "^NSESMCAP",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "NIFTY PVT BANK": "NIFTY_PVT_BANK.NS",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY INFRA": "^CNXINFRA",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY OIL & GAS": "^CNXOILGAS",
    "NIFTY HEALTHCARE": "^CNXHEALTHCARE",
    "NIFTY CONSUMER DURABLES": "^CNXCONSUM",
    "NIFTY COMMODITIES": "^CNXCOMMODITIES"
}

# ================= 3. SMS FUNCTION (Fast2SMS API) =================
def send_sms_alert(phone_number, message, api_key):
    if not api_key or api_key == "YOUR_FAST2SMS_API_KEY_HERE":
        return {"return": False, "message": "Invalid or missing API Key"}
    
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
        response = requests.post(url, data=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"return": False, "message": str(e)}

# ================= 4. TECHNICAL HELPER FUNCTIONS =================
def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df['High'] + df['Low']) / 2
    atr = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=period)
    up_band = hl2 - (multiplier * atr)
    low_band = hl2 + (multiplier * atr)
    
    supertrend = pd.Series(True, index=df.index)
    st_val = pd.Series(0.0, index=df.index)
    
    for i in range(1, len(df.index)):
        curr, prev = i, i - 1
        if df['Close'].iloc[curr] > low_band.iloc[prev]:
            supertrend.iloc[curr] = True
        elif df['Close'].iloc[curr] < up_band.iloc[prev]:
            supertrend.iloc[curr] = False
        else:
            supertrend.iloc[curr] = supertrend.iloc[prev]
            if supertrend.iloc[curr] and up_band.iloc[curr] < up_band.iloc[prev]:
                up_band.iloc[curr] = up_band.iloc[prev]
            if not supertrend.iloc[curr] and low_band.iloc[curr] > low_band.iloc[prev]:
                low_band.iloc[curr] = low_band.iloc[prev]
        
        st_val.iloc[curr] = up_band.iloc[curr] if supertrend.iloc[curr] else low_band.iloc[curr]
        
    return supertrend, st_val

def calculate_vwap(df):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    tp_vol = typical_price * df['Volume']
    return tp_vol.cumsum() / df['Volume'].cumsum()

# ================= 5. BACKGROUND AUTO-SCANNER ENGINE =================
if "auto_scan_active" not in st.session_state:
    st.session_state.auto_scan_active = False
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()
if "last_scan_logs" not in st.session_state:
    st.session_state.last_scan_logs = []

def background_scanner(api_key, phone_no):
    while st.session_state.auto_scan_active:
        logs = []
        now_str = datetime.now().strftime("%H:%M:%S")
        for name, symbol in ALL_SECTORS.items():
            try:
                df = yf.download(symbol, period="5d", interval="15m", progress=False)
                if df.empty or len(df) < 30:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]

                # Calculations
                df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
                df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
                df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
                macd = ta.trend.MACD(df['Close'])
                df['MACD'] = macd.macd()
                df['MACD_Signal'] = macd.macd_signal()

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
                    triggers.append("MACD Bullish Cross")

                if curr_rsi <= 30:
                    triggers.append(f"RSI Oversold ({curr_rsi:.1f})")
                elif curr_rsi >= 75:
                    triggers.append(f"RSI Overbought ({curr_rsi:.1f})")

                if triggers:
                    today = datetime.now().strftime("%Y-%m-%d")
                    alert_key = f"{symbol}{today}{triggers[0]}"
                    if alert_key not in st.session_state.sent_alerts:
                        sms_msg = f"AUTO ALERT:\nSector: {name}\nCMP: {cmp_val:.2f}\nRSI: {curr_rsi:.1f}\nTrigger: {', '.join(triggers)}"
                        res = send_sms_alert(phone_no, sms_msg, api_key)
                        if res.get("return"):
                            st.session_state.sent_alerts.add(alert_key)
                            logs.append(f"[{now_str}] ✅ SMS Sent for {name} ({', '.join(triggers)})")
                        else:
                            logs.append(f"[{now_str}] ❌ SMS Failed for {name}: {res.get('message')}")
            except Exception:
                continue
        
        if logs:
            st.session_state.last_scan_logs = logs
        time.sleep(300)  # Scan every 5 minutes

# ================= 6. SIDEBAR CONTROLS =================
st.sidebar.header("📊 निवड आणि सेटिंग्ज")

mode = st.sidebar.radio("सिम्बॉल प्रकार:", ["सर्व सेक्टरल इंडायसेस (Indices)", "कस्टम स्टॉक (Custom Stock)"])
if mode == "सर्व सेक्टरल इंडायसेस (Indices)":
    selected_name = st.sidebar.selectbox("सेक्टर इंडेक्स निवडा:", list(ALL_SECTORS.keys()))
    ticker = ALL_SECTORS[selected_name]
else:
    ticker = st.sidebar.text_input("स्टॉक सिम्बॉल टाका (उदा. RELIANCE.NS, SBIN.NS)", value="RELIANCE.NS")
    selected_name = ticker

timeframe = st.sidebar.selectbox("टाइमफ्रेम (Timeframe)", ["5m", "15m", "1h", "1d", "1wk"], index=3)
period = st.sidebar.selectbox("डेटा कालावधी (Period)", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ इंडिकेटर्स ऑन / ऑफ")
show_ema = st.sidebar.checkbox("EMAs (9, 21, 50, 200)", value=True)
show_sma = st.sidebar.checkbox("SMAs (20, 50)", value=False)
show_supertrend = st.sidebar.checkbox("Supertrend (10, 3)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands (20, 2)", value=True)
show_vwap = st.sidebar.checkbox("VWAP", value=True)
show_macd = st.sidebar.checkbox("MACD (12, 26, 9)", value=True)
show_rsi = st.sidebar.checkbox("RSI (14)", value=True)
show_stoch = st.sidebar.checkbox("Stochastic RSI", value=True)
show_sr = st.sidebar.checkbox("20D Support & Resistance", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📱 ऑटो SMS अलर्ट सेटिंग")
phone_no = st.sidebar.text_input("मोबाईल नंबर", value="8459958007")
api_key = st.sidebar.text_input("Fast2SMS API Key", type="password")

# Background Auto-Scanner Toggle Button
if st.sidebar.button("🚀 ऑटो स्कॅनर सुरू करा (Start Auto Scanner)"):
    if api_key:
        if not st.session_state.auto_scan_active:
            st.session_state.auto_scan_active = True
            threading.Thread(target=background_scanner, args=(api_key, phone_no), daemon=True).start()
            st.sidebar.success("ऑटो स्कॅनर बॅकग्राउंडमध्ये सुरू झाले!")
    else:
        st.sidebar.error("कृपया Fast2SMS API Key टाका.")

if st.sidebar.button("⏹️ ऑटो स्कॅनर थांबवा (Stop Auto Scanner)"):
    st.session_state.auto_scan_active = False
    st.sidebar.warning("ऑटो स्कॅनर थांबवले गेले.")

# ================= 7. APPLICATION TABS =================
tab1, tab2 = st.tabs(["📈 प्रो चार्ट आणि तांत्रिक विश्लेषण", "⚡ सर्व सेक्टर्स डॅशबोर्ड व ऑटो लॉग्ज"])

# ----------------- TAB 1: ADVANCED CHART -----------------
with tab1:
    st.subheader(f"📊 {selected_name} ({ticker}) - ऑल-इंडिकेटर विश्लेषण")
    data = yf.download(ticker, period=period, interval=timeframe)

    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]

        # Indicator Calculations
        data['EMA_9'] = ta.trend.ema_indicator(data['Close'], window=9)
        data['EMA_21'] = ta.trend.ema_indicator(data['Close'], window=21)
        data['EMA_50'] = ta.trend.ema_indicator(data['Close'], window=50)
        data['EMA_200'] = ta.trend.ema_indicator(data['Close'], window=200)
        data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
        data['SMA_50'] = ta.trend.sma_indicator(data['Close'], window=50)

        bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
        data['BB_High'] = bb.bollinger_hband()
        data['BB_Low'] = bb.bollinger_lband()

        try:
            data['ST_Signal'], data['ST_Val'] = calculate_supertrend(data)
        except Exception:
            data['ST_Signal'] = True
            data['ST_Val'] = data['Close']

        try:
            data['VWAP'] = calculate_vwap(data)
        except Exception:
            data['VWAP'] = data['Close']

        data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
        data['Stoch_RSI'] = ta.momentum.stochrsi(data['Close'], window=14) * 100
        
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()
        data['MACD_Hist'] = macd.macd_diff()

        data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=14)
        data['Resistance'] = data['High'].rolling(window=20).max()
        data['Support'] = data['Low'].rolling(window=20).min()

        # Metrics
        c_price = float(data['Close'].iloc[-1])
        p_price = float(data['Close'].iloc[-2])
        chg_pct = ((c_price - p_price) / p_price) * 100

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("CMP", f"₹{c_price:.2f}", f"{chg_pct:+.2f}%")
        c2.metric("RSI (14)", f"{data['RSI'].iloc[-1]:.1f}")
        c3.metric("MACD", f"{data['MACD'].iloc[-1]:.2f}")
        c4.metric("9 EMA", f"{data['EMA_9'].iloc[-1]:.2f}")
        c5.metric("21 EMA", f"{data['EMA_21'].iloc[-1]:.2f}")
        c6.metric("ATR (14)", f"{data['ATR'].iloc[-1]:.2f}")

        # Multi-panel Chart Setup
        extra_panels = sum([show_macd, show_rsi, show_stoch])
        total_rows = 2 + extra_panels
        row_heights = [0.55, 0.15] + [0.15] * extra_panels

        fig = make_subplots(rows=total_rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=row_heights)

        # Panel 1: Price & Overlays
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)

        if show_ema:
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_9'], line=dict(color='#2962FF', width=1.2), name="9 EMA"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_21'], line=dict(color='#FF6D00', width=1.2), name="21 EMA"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='#00897B', width=1.2), name="50 EMA"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_200'], line=dict(color='#D50000', width=1.5), name="200 EMA"), row=1, col=1)

        if show_sma:
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], line=dict(color='#AB47BC', width=1.2, dash='dot'), name="20 SMA"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], line=dict(color='#5C6BC0', width=1.2, dash='dot'), name="50 SMA"), row=1, col=1)

        if show_bb:
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_High'], line=dict(color='gray', dash='dash'), name="BB Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_Low'], line=dict(color='gray', dash='dash'), fill='tonexty', fillcolor='rgba(200,200,200,0.1)', name="BB Lower"), row=1, col=1)

        if show_supertrend:
            st_color = ['green' if val else 'red' for val in data['ST_Signal']]
            fig.add_trace(go.Scatter(x=data.index, y=data['ST_Val'], mode='markers', marker=dict(color=st_color, size=3), name="Supertrend"), row=1, col=1)

        if show_vwap:
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='#FFD600', width=1.3), name="VWAP"), row=1, col=1)

        if show_sr:
            fig.add_trace(go.Scatter(x=data.index, y=data['Resistance'], line=dict(color='green', dash='dot'), name="20D Res"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Support'], line=dict(color='orange', dash='dot'), name="20D Supp"), row=1, col=1)

        # Panel 2: Volume
        curr_row = 2
        vol_colors = ['green' if c >= o else 'red' for c, o in zip(data['Close'], data['Open'])]
        fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=vol_colors, name="Volume"), row=curr_row, col=1)

        # Panel 3: MACD
        if show_macd:
            curr_row += 1
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='blue', width=1.2), name="MACD"), row=curr_row, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'], line=dict(color='red', width=1.2), name="Signal"), row=curr_row, col=1)
            hist_colors = ['green' if val >= 0 else 'red' for val in data['MACD_Hist']]
            fig.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], marker_color=hist_colors, name="Hist"), row=curr_row, col=1)

        # Panel 4: RSI
        if show_rsi:
            curr_row += 1
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.3), name="RSI (14)"), row=curr_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr_row, col=1)

        # Panel 5: Stochastic RSI
        if show_stoch:
            curr_row += 1
            fig.add_trace(go.Scatter(x=data.index, y=data['Stoch_RSI'], line=dict(color='brown', width=1.2), name="Stoch RSI"), row=curr_row, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=curr_row, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=curr_row, col=1)

        fig.update_layout(height=850, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # Manual Trigger Button
        st.subheader("🚨 मॅन्युअल SMS अलर्ट")
        if st.button("📲 त्वरित 8459958007 वर टेस्ट SMS पाठवा"):
            if api_key:
                sms_body = f"MANUAL ALERT:\n{selected_name}\nCMP: {c_price:.2f}\nRSI: {data['RSI'].iloc[-1]:.1f}"
                res = send_sms_alert(phone_no, sms_body, api_key)
                if res.get("return"):
                    st.success("SMS यशस्वीरीत्या पाठवला गेला!")
                else:
                    st.error(f"SMS अयशस्वी: {res.get('message')}")
            else:
                st.error("कृपया API Key प्रविष्ट करा.")
    else:
        st.error("डेटा लोड करता आला नाही.")

# ----------------- TAB 2: DASHBOARD & AUTO LOGS -----------------
with tab2:
    st.subheader("⚡ सर्व NSE सेक्टर्स लाइव्ह डॅशबोर्ड")
    if st.button("सर्व सेक्टर्स आता स्कॅन करा (Manual Refresh)"):
        with st.spinner("सर्व सेक्टर्सचा डेटा लोड होत आहे..."):
            summary_list = []
            for sec_name, sec_sym in ALL_SECTORS.items():
                try:
                    df_sec = yf.download(sec_sym, period="3mo", interval="1d", progress=False)
                    if not df_sec.empty:
                        if isinstance(df_sec.columns, pd.MultiIndex):
                            df_sec.columns = [col[0] for col in df_sec.columns]

                        c_close = float(df_sec['Close'].iloc[-1])
                        p_close = float(df_sec['Close'].iloc[-2])
                        change_p = ((c_close - p_close) / p_close) * 100
                        rsi_val = float(ta.momentum.rsi(df_sec['Close'], window=14).iloc[-1])
                        ema_9 = float(ta.trend.ema_indicator(df_sec['Close'], window=9).iloc[-1])
                        ema_21 = float(ta.trend.ema_indicator(df_sec['Close'], window=21).iloc[-1])

                        trend_status = "🟢 Bullish" if ema_9 > ema_21 else "🔴 Bearish"

                        summary_list.append({
                            "इंडेक्स": sec_name,
                            "CMP": f"{c_close:.2f}",
                            "बदल (%)": f"{change_p:+.2f}%",
                            "RSI (14)": f"{rsi_val:.1f}",
                            "9/21 EMA ट्रेंड": trend_status
                        })
                except Exception:
                    continue

            if summary_list:
                st.dataframe(pd.DataFrame(summary_list), use_container_width=True)

    st.markdown("---")
    st.subheader("📜 ऑटो-स्कॅनर रिअल-टाइम लॉग्ज")
    if st.session_state.auto_scan_active:
        st.info("🟢 बॅकग्राउंड ऑटो-स्कॅनर सक्रिय आहे (दर ५ मिनिटांनी स्कॅन होत आहे).")
    else:
        st.warning("⚪ ऑटो-स्कॅनर सध्या बंद आहे. सुरू करण्यासाठी साइडबारमधील बटण दाबा.")

    if st.session_state.last_scan_logs:
        for log in st.session_state.last_scan_logs:
            st.text(log)
