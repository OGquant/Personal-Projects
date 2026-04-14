"""Page 2: Futures Term Structure & Open Interest."""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Futures & OI", layout="wide", page_icon="📈")
st.title("📈 Futures & Open Interest")

from src.data.spot_prices import fetch_history
from src.data.cot_reports import fetch_cot_current
from src.data.kite_feed import is_configured as kite_configured, fetch_mcx_quotes, compute_intraday_rv

# ── Kite Status Banner ──
if kite_configured():
    st.success("MCX Live Feed: Connected via Kite Connect", icon="🟢")
    mcx_df = fetch_mcx_quotes()
    if mcx_df is not None and not mcx_df.empty:
        st.subheader("MCX Live Quotes")
        cols = st.columns(len(mcx_df))
        for i, (_, row) in enumerate(mcx_df.iterrows()):
            with cols[i]:
                st.metric(
                    label=row["symbol"],
                    value=f"₹{row['ltp']:,.0f}",
                    delta=f"{row['change_pct']:+.2f}%",
                )
        st.dataframe(mcx_df, use_container_width=True, hide_index=True)
        st.divider()

    # Intraday RV from live ticks
    rv = compute_intraday_rv("GOLD", interval="5minute")
    if rv["rv_annualized"] is not None:
        st.caption(f"MCX Gold — 5-min Realized Vol (annualized): **{rv['rv_annualized']*100:.1f}%** from {rv['n_bars']} bars")
else:
    st.info(
        "MCX live feed inactive. Set KITE_API_KEY + KITE_ACCESS_TOKEN in .env to enable "
        "real-time MCX quotes, option chains & intraday vol. Falling back to yfinance.",
        icon="ℹ️",
    )

# ── Futures Term Structure (using available contract months) ──
st.subheader("Gold Futures — Price History")
tab1, tab2 = st.tabs(["Gold (GC)", "Silver (SI)"])

with tab1:
    period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=1, key="gc_period")
    df = fetch_history("XAU/USD", period=period)
    if df is not None and not df.empty:
        close_col = "close" if "close" in df.columns else df.columns[-1]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.get("date", df.index), y=df[close_col], mode="lines",
                                 line=dict(color="#F5A623", width=2), name="Gold"))
        fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                          height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    period_si = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=1, key="si_period")
    df_si = fetch_history("XAG/USD", period=period_si)
    if df_si is not None and not df_si.empty:
        close_col = "close" if "close" in df_si.columns else df_si.columns[-1]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_si.get("date", df_si.index), y=df_si[close_col], mode="lines",
                                 line=dict(color="#C0C0C0", width=2), name="Silver"))
        fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                          height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

# ── CFTC COT Positioning ──
st.divider()
st.subheader("CFTC Commitments of Traders")
st.caption("Managed money net positioning — weekly update")

cot = fetch_cot_current()
if cot is not None and not cot.empty:
    for _, row in cot.iterrows():
        commodity = row.get("commodity", "Unknown")
        st.markdown(f"**{commodity}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Net Long (MM)", f"{int(row.get('mm_net', 0)):,}")
        c2.metric("Gross Long", f"{int(row.get('mm_long', 0)):,}")
        c3.metric("Gross Short", f"{int(row.get('mm_short', 0)):,}")
        c4.metric("Total OI", f"{int(row.get('oi_total', 0)):,}")
    st.dataframe(cot, use_container_width=True, hide_index=True)
else:
    st.info("COT data unavailable — CFTC reports update weekly on Fridays.")
