from datetime import datetime
import os
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import ta
import yfinance as yf

# ---- पेज कॉन्फिगरेशन ----
st.set_page_config(
    page_title="Market Analyser",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

# ---- अल्ट्रा व्हायब्रंट निऑन CSS (प्युअर ब्लॅक थीम) ----
st.markdown(
    """
<style>
    .stApp {
        background-color: #05070a;
        color: #e6edf3;
    }
    
    .branding-box {
        text-align: center;
        margin-top: 10px;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        background: #000000;
        padding: 15px;
        border-radius: 16px;
        border: 1px solid #1f242c;
    }

    .neon-hulgunde-extended {
        display: flex;
        justify-content: space-between;
        width: 100%;
        max-width: 580px;
        margin-top: 5px;
        margin-bottom: 2px;
        font-size: 2.4rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 6px;
    }

    .h-pink   { color: #FF007A; text-shadow: 0 0 15px #FF007A; }
    .h-orange { color: #FF7700; text-shadow: 0 0 15px #FF7700; }
    .h-yellow { color: #FFE600; text-shadow: 0 0 15px #FFE600; }
    .h-green  { color: #00FF88; text-shadow: 0 0 15px #00FF88; }
    .h-cyan   { color: #00F0FF; text-shadow: 0 0 15px #00F0FF; }
    .h-blue   { color: #388BFD; text-shadow: 0 0 15px #388BFD; }
    .h-purple { color: #9D00FF; text-shadow: 0 0 15px #9D00FF; }
    .h-magenta{ color: #FF00D4; text-shadow: 0 0 15px #FF00D4; }

    .neon-market-analyser {
        background: linear-gradient(135deg, #00F0FF 0%, #9D00FF 50%, #FF007A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.6rem;
        font-weight: 900;
        text-align: center;
        text-shadow: 0 0 25px rgba(0, 240, 255, 0.45);
        letter-spacing: 3px;
        margin-top: 2px;
        margin-bottom: 5px;
        line-height: 1.2;
    }

    .neon-subtitle-center {
        color: #58a6ff;
        font-size: 1rem;
        font-weight: 500;
        text-align: center;
        margin-bottom: 25px;
    }

    .yellow-glow-label {
        color: #FFE600 !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        text-shadow: 0 0 10px rgba(255, 230, 0, 0.6) !important;
        margin-bottom: 6px;
        display: block;
    }

    .card-pink {
        background: linear-gradient(135deg, #160718 0%, #240822 100%);
        border: 2px solid #FF007A;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 0 15px rgba(255, 0, 122, 0.3);
    }
    .card-yellow {
        background: linear-gradient(135deg, #1c1604 0%, #2b2207 100%);
        border: 2px solid #FFE600;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 0 18px rgba(255, 230, 0, 0.4);
    }
    .card-green {
        background: linear-gradient(135deg, #05140c 0%, #0a2416 100%);
        border: 2px solid #00FF88;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
    }
    
    .val-pink { font-size: 1.8rem; font-weight: 800; color: #FF66B2; }
    .val-yellow { font-size: 1.8rem; font-weight: 800; color: #FFE600; text-shadow: 0 0 12px rgba(255, 230, 0, 0.6); }
    .val-green { font-size: 1.8rem; font-weight: 800; color: #00FF88; }
    .card-lbl { color: #8b949e; font-size: 0.8rem; text-transform: uppercase; font-weight: 600; margin-top: 4px; }

    div.stButton > button:first-child {
        background: linear-gradient(90deg, #FF007A 0%, #9D00FF 50%, #00F0FF 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 1.05rem;
        border-radius: 10px;
        border: none;
        padding: 0.7rem 2.2rem;
        box-shadow: 0 0 20px rgba(255, 0, 122, 0.45);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.7);
        color: #ffffff;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---- मार्केट डेटा सूची ----
MARKET_SECTORS = {
    "🎯 NIFTY 50 INDEX / OPTIONS (SPOT)": [
        "^NSEI", "NIFTYBEES.NS", "^NSEBANK"
    ],
    "🔥 NIFTY 50 EQUITIES": [
        "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
        "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS",
        "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS", "EICHERMOT.NS",
        "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS",
        "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INDUSINDBK.NS", "INFY.NS",
        "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", "M&M.NS",
        "MARUTI.NS", "NESTLEIND.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
        "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS", "TATACONSUM.NS",
        "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS",
        "ULTRACEMCO.NS", "WIPRO.NS"
    ],
    "🏦 BANKNIFTY": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "AUBANK.NS", "FEDERALBNK.NS",
        "IDFCFIRSTB.NS", "BANDHANBNK.NS"
    ],
    "💳 FINNIFTY": [
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS",
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "CHOLAFIN.NS",
        "SHRIRAMFIN.NS", "MUTHOOTFIN.NS", "PFC.NS", "RECLTD.NS"
    ],
    "🏛️ SENSEX 30": [
        "HDFCBANK.BO", "RELIANCE.BO", "ICICIBANK.BO", "INFY.BO", "TCS.BO",
        "ITC.BO", "LT.BO", "AXISBANK.BO", "SBIN.BO", "BHARTIARTL.BO",
        "KOTAKBANK.BO", "HINDUNILVR.BO", "M&M.BO", "MARUTI.BO", "SUNPHARMA.BO",
        "TATASTEEL.BO", "TITAN.BO", "BAJFINANCE.BO", "ASIANPAINT.BO", "NTPC.BO",
        "POWERGRID.BO", "ULTRACEMCO.BO", "NESTLEIND.BO", "TECHM.BO", "WIPRO.BO",
        "JSWSTEEL.BO", "TATAMOTORS.BO", "INDUSINDBK.BO", "BAJAJFINSV.BO", "HCLTECH.BO"
    ],
    "🛢️ TOP COMMODITIES (Crude Oil & Gold)": [
        "CL=F", "GC=F", "GOLDBEES.NS"
    ]
}

# साइडबार कंट्रोल्स
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
        
    st.markdown("## 🌈 कंट्रोल सेंटर")
    selected_market = st.selectbox("🎯 इंडेक्स / कमॉडिटी निवडा:", list(MARKET_SECTORS.keys()))
    selected_stocks = MARKET_SECTORS[selected_market]

    st.markdown('<span class="yellow-glow-label">⏱️ Timeframe</span>', unsafe_allow_html=True)
    timeframe = st.select_slider("Timeframe निवडा", options=["1m", "5m", "15m", "1h", "1d"], value="15m", label_visibility="collapsed")

    st.markdown('<span class="yellow-glow-label">📈 EMA Indicators</span>', unsafe_allow_html=True)
    selected_emas = st.multiselect("EMA निवडा", [9, 21, 50, 200], default=[9, 21, 50, 200], label_visibility="collapsed")

    st.markdown('<span class="yellow-glow-label">🎯 Support & Resistance</span>', unsafe_allow_html=True)
    check_sr = st.checkbox("Support & Resistance लेव्हल्स दाखवा", value=True)

    st.markdown("---")
    st.markdown("### ✈️ Telegram बॉट सेटिंग")
    tg_token = st.text_input(
        "Bot Token",
        value="8799046332:AAHzWmvR1ZWJ-7ARzWgybFu-6Ykl7Trdt2k",
        type="password"
    )
    tg_chat_id = st.text_input(
        "Chat ID",
        value="5055029691"
    )
    send_tg_alerts = st.checkbox("सिग्नल्स Telegram वर पाठवा", value=True)

# Telegram अलर्ट पाठवणारे फंक्शन
def send_telegram_message(token, chat_id, text):
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# ---- हेडर ब्रँडिंग ----
h_col1, h_col2, h_col3 = st.columns([1, 2.2, 1])
with h_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("""
<div class="branding-box">
    <div class="neon-hulgunde-extended">
        <span class="h-pink">H</span>
        <span class="h-orange">U</span>
        <span class="h-yellow">L</span>
        <span class="h-green">G</span>
        <span class="h-cyan">U</span>
        <span class="h-blue">N</span>
        <span class="h-purple">D</span>
        <span class="h-magenta">E</span>
    </div>
    <div class="neon-market-analyser">MARKET ANALYSER</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="neon-subtitle-center">🚀 लाईव्ह मल्टि-ॲसेट ॲनालिसिस • <b>{selected_market}</b> • Timeframe: <b>{timeframe}</b></div>', unsafe_allow_html=True)

# ४ मेट्रिक कार्ड्स
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="card-pink"><div class="val-pink">{len(selected_stocks)}</div><div class="card-lbl">एकूण शेअर्स / कमॉडिटी</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="card-yellow"><div class="val-yellow">{timeframe}</div><div class="card-lbl">Timeframe</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="card-yellow"><div class="val-yellow">{len(selected_emas)} EMAs</div><div class="card-lbl">Indicators</div></div>', unsafe_allow_html=True)
c4.markdown('<div class="card-green"><div class="val-green">24/7 LIVE</div><div class="card-lbl">ऑटोमेशन स्टेटस</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["⚡ थेट ब्रेकआऊट सिग्नल्स (Live Signals)", "🕯️ मल्टिकलर निऑन चार्ट", "🎯 Nifty 50 Option Chain"])

period_map = {"1m": "5d", "5m": "10d", "15m": "30d", "1h": "60d", "1d": "1y"}

@st.cache_data(ttl=60)
def fetch_and_calculate(symbol, tf):
    try:
        df = yf.download(symbol, period=period_map.get(tf, "30d"), interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        if len(df) < 50:
            return None
        
        for ema in [9, 21, 50, 200]:
            df[f'EMA_{ema}'] = ta.trend.ema_indicator(df['Close'], window=ema)
        
        df['Resistance'] = df['High'].rolling(20).max()
        df['Support'] = df['Low'].rolling(20).min()
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
            
            c_close = float(df['Close'].iloc[-1])
            p_close = float(df['Close'].iloc[-2])
            res_lvl = float(df['Resistance'].iloc[-2])
            sup_lvl = float(df['Support'].iloc[-2])
            
            signals = []
            for ema in selected_emas:
                if f'EMA_{ema}' in df.columns:
                    p_ema = float(df[f'EMA_{ema}'].iloc[-2])
                    c_ema = float(df[f'EMA_{ema}'].iloc[-1])
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
                clean_name = sym.replace(".NS", "").replace(".BO", "").replace("CL=F", "CRUDE OIL").replace("GC=F", "GOLD").replace("^NSEI", "NIFTY 50 INDEX").replace("^NSEBANK", "BANK NIFTY INDEX")
                results.append({
                    "Stock / Index": clean_name,
                    "CMP (₹)": f"₹{c_close:.2f}",
                    "Technical Signals": "  |  ".join(signals),
                    "Support (₹)": f"₹{sup_lvl:.2f}",
                    "Resistance (₹)": f"₹{res_lvl:.2f}"
                })
        
        bar.empty()
        if results:
            res_df = pd.DataFrame(results)
            st.success(f"🎉 एकूण {len(results)} सिग्नल्स मिळाले!")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

            if send_tg_alerts and tg_token and tg_chat_id:
                msg = f"⚡ मार्केट सिग्नल्स ({selected_market} - {timeframe})\n\n"
                for item in results:
                    msg += f"• {item['Stock / Index']}: {item['CMP (₹)']}\n  Signal: {item['Technical Signals']}\n\n"
                send_telegram_message(tg_token, tg_chat_id, msg)
                st.info("📨 Telegram वर सिग्नल्स पाठवले गेले आहेत!")
        else:
            st.info("या टाइमफ्रेमवर सध्या कोणताही नवीन सिग्नल उपलब्ध नाही.")

with tab2:
    chart_sym = st.selectbox("📊 विश्लेषणासाठी निवडा:", selected_stocks)
    df_chart = fetch_and_calculate(chart_sym, timeframe)
    
    if df_chart is not None:
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart['Open'],
            high=df_chart['High'],
            low=df_chart['Low'],
            close=df_chart['Close'],
            name="कँडल्स",
            increasing_line_color='#00FF88',
            decreasing_line_color='#FF0055'
        ))
        
        ema_colors = {
            9: '#FFE600',
            21: '#00F0FF',
            50: '#FF00AA',
            200: '#9D00FF'
        }
        
        for ema in selected_emas:
            if f'EMA_{ema}' in df_chart.columns:
                fig.add_trace(go.Scatter(
                    x=df_chart.index,
                    y=df_chart[f'EMA_{ema}'],
                    name=f"EMA {ema}",
                    line=dict(color=ema_colors.get(ema, '#FFFFFF'), width=2)
                ))
        
        if check_sr:
            latest_res = df_chart['Resistance'].iloc[-1]
            latest_sup = df_chart['Support'].iloc[-1]
            fig.add_hline(y=latest_res, line_dash="dash", line_color="#00F0FF", annotation_text=f"Res: ₹{latest_res:.2f}", annotation_font_color="#00F0FF")
            fig.add_hline(y=latest_sup, line_dash="dash", line_color="#FF007A", annotation_text=f"Sup: ₹{latest_sup:.2f}", annotation_font_color="#FF007A")
        
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor='#05070a',
            paper_bgcolor='#05070a',
            xaxis_rangeslider_visible=False,
            height=580,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### ⚡ निफ्टी ५० लाईव्ह ऑप्शन डेटा (Option Chain)")
    try:
        nifty_ticker = yf.Ticker("^NSEI")
        expiries = nifty_ticker.options
        if expiries:
            selected_exp = st.selectbox("📅 Expiry Date निवडा:", expiries)
            chain = nifty_ticker.option_chain(selected_exp)
            
            col_call, col_put = st.columns(2)
            
            with col_call:
                st.markdown("<h4 style='color: #00FF88;'>🟢 Call Options (CE)</h4>", unsafe_allow_html=True)
                calls_df = chain.calls[['strike', 'lastPrice', 'change', 'volume', 'openInterest']].rename(
                    columns={'strike': 'Strike', 'lastPrice': 'LTP', 'change': 'Change', 'volume': 'Vol', 'openInterest': 'OI'}
                )
                st.dataframe(calls_df, use_container_width=True, hide_index=True)
                
            with col_put:
                st.markdown("<h4 style='color: #FF007A;'>🔴 Put Options (PE)</h4>", unsafe_allow_html=True)
                puts_df = chain.puts[['strike', 'lastPrice', 'change', 'volume', 'openInterest']].rename(
                    columns={'strike': 'Strike', 'lastPrice': 'LTP', 'change': 'Change', 'volume': 'Vol', 'openInterest': 'OI'}
                )
                st.dataframe(puts_df, use_container_width=True, hide_index=True)
        else:
            st.warning("सध्या ऑप्शन एक्सपायरी डेटा उपलब्ध नाही.")
    except Exception as e:
        st.error(f"ऑप्शन डेटा लोड करताना अडचण आली: {e}")
