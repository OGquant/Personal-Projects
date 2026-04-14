"""
AURUM — Institutional Metals Intelligence Terminal
Main entry point. Run: streamlit run src/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="AURUM • Metals Terminal",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Bloomberg-style dark theme ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=DM+Sans:wght@400;500;700&display=swap');

    .stApp { font-family: 'DM Sans', sans-serif; }
    code, .stCode, pre { font-family: 'JetBrains Mono', monospace !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1A1E2E;
        border: 1px solid #2a2e3e;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; }
    [data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0a0d14; }
    [data-testid="stSidebar"] .stMarkdown h1 { font-size: 1.3rem; color: #F5A623; }

    /* Tables */
    .stDataFrame { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }

    /* Headers */
    h1 { color: #F5A623 !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    h2 { color: #E0E0E8 !important; font-weight: 600 !important; }
    h3 { color: #a0a0b0 !important; font-weight: 500 !important; }

    /* Remove top padding */
    .block-container { padding-top: 1rem; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
    }

    /* Plotly charts dark bg */
    .js-plotly-plot .plotly .modebar { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("# 🥇 AURUM")
    st.caption("Metals Intelligence Terminal")
    st.divider()
    st.markdown("**Navigation**")
    st.page_link("app.py", label="🏠 Market Overview", icon="🏠")
    st.page_link("pages/2_futures_oi.py", label="📈 Futures & OI")
    st.page_link("pages/3_options_flow.py", label="🔗 Options Flow")
    st.page_link("pages/4_macro_dashboard.py", label="🌍 Macro Dashboard")
    st.page_link("pages/5_intelligence.py", label="📡 Intelligence Feed")
    st.page_link("pages/6_trading_tools.py", label="🛠️ Trading Tools")
    st.page_link("pages/7_analytics.py", label="📊 Analytics Lab")
    st.page_link("pages/8_risk_dashboard.py", label="⚠️ Risk Dashboard")
    st.page_link("pages/9_vol_trading.py", label="🌊 Vol Trading Lab")
    st.divider()
    # Data source status
    try:
        from src.data.kite_feed import is_configured as kite_ok
        if kite_ok():
            st.markdown("🟢 **MCX Live** via Kite")
        else:
            st.markdown("🟡 **Delayed** — yfinance")
            st.caption("Add KITE keys to .env for live MCX")
    except Exception:
        st.markdown("🟡 **Delayed** — yfinance")
    st.caption("Data: yfinance • FRED • CFTC • Polymarket")

# ── Main Page: Market Overview ──
st.title("🏠 Market Overview")

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.data.spot_prices import fetch_live_prices, fetch_history, TICKERS
    from src.data.etf_flows import fetch_etf_data
    from src.analytics.ratios import compute_ratio
    import plotly.graph_objects as go

    # ── Spot Prices Grid ──
    with st.spinner("Loading live prices..."):
        prices_df = fetch_live_prices()

    if prices_df is not None and not prices_df.empty:
        # Hero metrics — Gold, Silver, DXY, Oil
        hero_instruments = ["XAU/USD", "XAG/USD", "DXY", "WTI Crude", "BTC/USD", "VIX"]
        hero_data = prices_df[prices_df["instrument"].isin(hero_instruments)]

        cols = st.columns(len(hero_data))
        for i, (_, row) in enumerate(hero_data.iterrows()):
            with cols[i]:
                delta_color = "normal" if row["instrument"] not in ["VIX"] else "inverse"
                st.metric(
                    label=row["instrument"],
                    value=f"{row['price']:,.2f}",
                    delta=f"{row['change_pct']:+.2f}%",
                    delta_color=delta_color,
                )

        st.divider()

        # ── Full Price Table ──
        st.subheader("All Instruments")
        # Color the change column
        display_df = prices_df[["instrument", "price", "change", "change_pct"]].copy()
        display_df.columns = ["Instrument", "Price", "Change", "Change %"]
        st.dataframe(
            display_df.style.map(
                lambda v: "color: #10b981" if isinstance(v, (int, float)) and v > 0 else "color: #ef4444" if isinstance(v, (int, float)) and v < 0 else "",
                subset=["Change", "Change %"]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Could not load live prices. Check your internet connection.")

    # ── Gold Chart ──
    st.subheader("Gold — 1 Year")
    gold_hist = fetch_history("XAU/USD", period="1y")
    if gold_hist is not None and not gold_hist.empty:
        fig = go.Figure()
        close_col = "close" if "close" in gold_hist.columns else gold_hist.columns[-1]
        fig.add_trace(go.Candlestick(
            x=gold_hist["date"] if "date" in gold_hist.columns else gold_hist.index,
            open=gold_hist.get("open", gold_hist[close_col]),
            high=gold_hist.get("high", gold_hist[close_col]),
            low=gold_hist.get("low", gold_hist[close_col]),
            close=gold_hist[close_col],
            increasing_line_color="#10b981", decreasing_line_color="#ef4444",
        ))
        fig.update_layout(
            template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            xaxis_rangeslider_visible=False, height=450,
            font=dict(family="JetBrains Mono", color="#E0E0E8"),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Key Ratios ──
    col1, col2 = st.columns(2)
    gold_hist_data = fetch_history("XAU/USD", period="2y")
    silver_hist_data = fetch_history("XAG/USD", period="2y")

    if gold_hist_data is not None and silver_hist_data is not None and not gold_hist_data.empty and not silver_hist_data.empty:
        g_close = "close" if "close" in gold_hist_data.columns else gold_hist_data.columns[-1]
        s_close = "close" if "close" in silver_hist_data.columns else silver_hist_data.columns[-1]
        ratio = gold_hist_data[g_close].values[-1] / silver_hist_data[s_close].values[-1] if silver_hist_data[s_close].values[-1] != 0 else 0
        with col1:
            st.metric("Gold/Silver Ratio", f"{ratio:.1f}", help="Historical avg ~68, current elevated = silver undervalued")
        with col2:
            oil_data = fetch_history("WTI Crude", period="2y")
            if oil_data is not None and not oil_data.empty:
                o_close = "close" if "close" in oil_data.columns else oil_data.columns[-1]
                go_ratio = gold_hist_data[g_close].values[-1] / oil_data[o_close].values[-1] if oil_data[o_close].values[-1] != 0 else 0
                st.metric("Gold/Oil Ratio", f"{go_ratio:.1f}", help="Higher = gold expensive vs oil")

    # ── ETF Flows ──
    st.subheader("Metal ETF Monitor")
    etf_df = fetch_etf_data()
    if etf_df is not None and not etf_df.empty:
        st.dataframe(etf_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure you have internet access and required packages installed. Run: pip install -r requirements.txt")
