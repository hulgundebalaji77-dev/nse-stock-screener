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
st.set_page_config(page_title="Only Signal Triggered Stocks Screener", layout="wide")

# ================= 2. ALL SECTOR STOCKS LIST =================
ALL_STOCKS_FLAT = [
    # Banking & Finance
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", 
    "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
    # IT
    "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "LTIM.NS", "TECHM.NS", "PERSISTENT.NS", "COFORGE.NS",
    # Auto
    "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS",
    # Pharma & Healthcare
    "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS", "APOLLOHOSP.NS",
    # FMCG & Consumer
    "ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", "VBL.NS", "TITAN.NS",
    # Metal & Mining
    "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "JINDALSTEL.NS", "VEDL.NS", "COALINDIA.NS",
    # Energy, Oil & Gas
    "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS", "IOC.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    # Infra & Realty
    "LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "DLF.NS", "GODREJPROP.NS"
]

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

# ================= 4. SIGNAL CHECKER FUNCTION =================
def scan_stock_for_signals(df):
    """
    फक्त सिग्नल तयार झाला असेल तरच माहिती रिटर्न करतो.
    नाहीतर None रिटर्न करतो.
    """
    if df.empty or len(df) < 30:
        return None

    # Indicators
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()

    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()

    # Values for Last 2 Candles
    p_close = float(df['Close'].iloc[-2])
    c_close = float(df['Close'].iloc[-1])
    
    p_e9, p_e21 = float(df['EMA_9'].iloc[-2]), float(df['EMA_21'].iloc[-2])
    c_e9, c_e21 = float(df['EMA_9'].iloc[-1]), float(df['EMA_21'].iloc[-1])
    
    p_macd, p_msig = float(df['MACD'].iloc[-2]), float(df['MACD_Signal'].iloc[-2])
    c_macd, c_msig = float(df['MACD'].iloc[-1]), float(df['MACD_Signal'].iloc[-1])
    
    curr_rsi = float(df['RSI'].iloc[-1])
    bb_high = float(df['BB_High'].iloc[-1])
    bb_low = float(df['BB_Low'].iloc[-1])

    signals = []

    # 1. EMA Crossover
    if (p_e9 <= p_e21) and (c_e9 > c_e21):
        signals.append("🟢 9/21 EMA Golden Cross (Buy)")
    elif (p_e9 >= p_e21) and (c_e9 < c_e21):
        signals.append("🔴 9/21 EMA Death Cross (Sell)")

    # 2. MACD Crossover
    if (p_macd <= p_msig) and (c_macd > c_msig):
        signals.append("🟢 MACD Bullish Cross")
    elif (p_macd >= p_msig) and (c_macd < c_msig):
        signals.append("🔴 MACD Bearish Cross")

    # 3. RSI Extrems
    if curr_rsi <= 30:
        signals.append(f"📉 RSI Oversold ({curr_rsi:.1f})")
    elif curr_rsi >= 70:
        signals.append(f"📈 RSI Overbought ({curr_rsi:.1f})")

    # 4. Bollinger Breakout
    if c_close > bb_high:
        signals.append("🚀 Upper BB Breakout")
    elif c_close < bb_low:
        signals.append("🔻 Lower BB Breakdown")

    # जर किमान १ सिग्नल असेल तरच डेटा पाठवा
    if signals:
        chg_pct = ((c_close - p_close) / p_close) * 100
        return {
            "Close": c_close,
            "Change_Pct": chg_pct,
            "RSI": curr_rsi,
            "Signals": " | ".join(signals),
            "Raw_Signals": signals
        }
    return None

# ================= 5. BACKGROUND AUTO SCANNER ENGINE =================
if "auto_scan_active" not in st.session_state:
    st.session_state.auto_scan_active = False
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()
if "detected_signals_table" not in st.session_state:
    st.session_state.detected_signals_table = []

def run_auto_scanner(api_key, phone_no):
    while st.session_state.auto_scan_active:
        now_time = datetime.now().strftime("%H:%M:%S")
        for sym in ALL_STOCKS_FLAT:
            if not st.session_state.auto_scan_active:
                break
            try:
                df = yf.download(sym, period="5d", interval="15m", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]

                res = scan_stock_for_signals(df)
                
                # जर सिग्नल मिळाला तरच:
                if res:
                    today = datetime.now().strftime("%Y-%m-%d")
                    alert_key = f"{sym}{today}{res['Raw_Signals'][0]}"

                    if alert_key not in st.session_state.sent_alerts:
                        # Auto SMS
                        sms_text = f"SIGNAL ALERT:\nStock: {sym}\nPrice: ₹{res['Close']:.2f}\nRSI: {res['RSI']:.1f}\nTrigger: {res['Signals']}"
                        sms_status = send_sms_alert(phone_no, sms_text, api_key)
                        
                        if sms_status.get("return"):
                            st.session_state.sent_alerts.add(alert_key)

                        # UI साठी टेबलमध्ये ॲड करा
                        st.session_state.detected_signals_table.insert(0, {
                            "वेळ (Time)": now_time,
                            "स्टॉक (Stock)": sym,
                            "किंमत (CMP)": f"₹{res['Close']:.2f}",
                            "बदल (%)": f"{res['Change_Pct']:+.2f}%",
                            "RSI": f"{res['RSI']:.1f}",
                            "सिग्नल (Triggers)": res['Signals']
                        })
            except Exception:
                continue

        time.sleep(300) # 5 मिनिटांचा गॅप

# ================= 6. SIDEBAR CONTROLS =================
st.sidebar.header("🎯 सिग्नल-ओन्ली स्कॅनर (Controls)")

timeframe = st.sidebar.selectbox("टाइमफ्रेम निवडा:", ["15m", "5m", "1h", "1d"], index=0)
st.sidebar.markdown("---")
st.sidebar.subheader("📱 ऑटो SMS सेटिंग्ज")
phone_no = st.sidebar.text_input("मोबाईल नंबर", value="8459958007")
api_key = st.sidebar.text_input("Fast2SMS API Key", type="password")

if st.sidebar.button("🚀 ऑटो स्कॅनर सुरू करा (Start Auto Engine)"):
    if api_key:
        if not st.session_state.auto_scan_active:
            st.session_state.auto_scan_active = True
            threading.Thread(target=run_auto_scanner, args=(api_key, phone_no), daemon=True).start()
            st.sidebar.success("ऑटो स्कॅनर बॅकग्राउंडमध्ये सुरू झाले!")
    else:
        st.sidebar.error("कृपया Fast2SMS API Key टाका.")

if st.sidebar.button("⏹️ ऑटो स्कॅनर थांबवा"):
    st.session_state.auto_scan_active = False
    st.sidebar.warning("ऑटो स्कॅनर थांबवले आहे.")

# ================= 7. MAIN UI DASHBOARD =================
st.title("⚡ केवळ सिग्नल मिळालेले शेअर्स (Signal-Only Screener)")
st.caption("येथे फक्त तेच शेअर्स दिसतील ज्यामध्ये *9/21 EMA Cross, MACD Buy/Sell, किंवा Bollinger Breakout* तयार झाला आहे.")

col_btn1, col_btn2 = st.columns([2, 8])
with col_btn1:
    scan_now = st.button("🔍 आता त्वरित स्कॅन करा (Instant Scan)")

if scan_now:
    with st.spinner("सर्व शेअर्स स्कॅन करून फक्त सिग्नल असलेले शेअर्स शोधत आहे..."):
        manual_results = []
        for sym in ALL_STOCKS_FLAT:
            try:
                df = yf.download(sym, period="5d", interval=timeframe, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]

                res = scan_stock_for_signals(df)
                if res:
                    manual_results.append({
                        "स्टॉक (Stock)": sym,
                        "किंमत (CMP)": f"₹{res['Close']:.2f}",
                        "बदल (%)": f"{res['Change_Pct']:+.2f}%",
                        "RSI (14)": f"{res['RSI']:.1f}",
                        "मिळालेला सिग्नल (Triggered Signals)": res['Signals']
                    })
            except Exception:
                continue

        if manual_results:
            st.success(f"🎯 एकूण {len(manual_results)} शेअर्समध्ये तांत्रिक सिग्नल मिळाले आहेत!")
            st.dataframe(pd.DataFrame(manual_results), use_container_width=True)
        else:
            st.info("सध्या कोणत्याही शेअरमध्ये नवीन सिग्नल मिळालेला नाही (मार्केट रेंजबाऊंड आहे).")

# ऑटो स्कॅनरद्वारे सापडलेले रिअल-टाइम शेअर्स
st.markdown("---")
st.subheader("📡 ऑटो-स्कॅनरद्वारे सापडलेले शेअर्स (Live Auto-Triggered)")

if st.session_state.auto_scan_active:
    st.success("🟢 ऑटो-स्कॅनर सक्रिय आहे (नवीन सिग्नल मिळताच SMS पाठवला जाईल आणि खाली यादीत ॲड होईल).")
else:
    st.warning("⚪ ऑटो-स्कॅनर बंद आहे. डाव्या साइडबारमधून '🚀 ऑटो स्कॅनर सुरू करा' दाबा.")

if st.session_state.detected_signals_table:
    st.dataframe(pd.DataFrame(st.session_state.detected_signals_table), use_container_width=True)
else:
    st.caption("अद्याप ऑटो-स्कॅनमध्ये कोणताही नवीन ट्रिगर सापडलेला नाही.")
