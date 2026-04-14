"""Page 4: Macro Dashboard — FRED, real rates, DXY, central banks."""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Macro", layout="wide", page_icon="🌍")
st.title("🌍 Macro Dashboard")

from src.data.fred_macro import fetch_series, compute_real_rate
from src.data.central_banks import fetch_reserves, fetch_buying_pace, fetch_annual_demand
from src.data.spot_prices import fetch_history

# ── Real Rates vs Gold ──
st.subheader("Gold vs Real Interest Rates")
st.caption("Gold typically rallies when real rates decline")

gold = fetch_history("XAU/USD", period="5y")
real = compute_real_rate()

if gold is not None and not gold.empty and real is not None and not real.empty:
    fig = go.Figure()
    g_close = "close" if "close" in gold.columns else gold.columns[-1]
    fig.add_trace(go.Scatter(x=gold.get("date", gold.index), y=gold[g_close],
                             name="Gold ($/oz)", line=dict(color="#F5A623", width=2), yaxis="y"))
    fig.add_trace(go.Scatter(x=real["date"], y=real["real_rate_approx"],
                             name="10Y TIPS (Real Rate)", line=dict(color="#00d4ff", width=2), yaxis="y2"))
    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", height=400,
        yaxis=dict(title="Gold $/oz", side="left"),
        yaxis2=dict(title="Real Rate %", side="right", overlaying="y"),
        legend=dict(orientation="h", y=1.1),
        font=dict(family="JetBrains Mono", color="#E0E0E8"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Key Macro Series ──
st.divider()
st.subheader("Key Macro Indicators")
macro_series = ["Fed Funds Rate", "CPI (YoY)", "M2 Money Supply", "Unemployment"]
tabs = st.tabs(macro_series)

for tab, name in zip(tabs, macro_series):
    with tab:
        data = fetch_series(name)
        if data is not None and not data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data["date"], y=data["value"], mode="lines",
                                     line=dict(color="#F5A623", width=2), name=name))
            fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                              height=300, title=name, font=dict(family="JetBrains Mono"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No data for {name}. Set FRED_API_KEY in config/.env for full access.")

# ── DXY vs Gold ──
st.divider()
st.subheader("DXY (Dollar Index) vs Gold")
dxy = fetch_history("DXY", period="2y")
if gold is not None and dxy is not None and not gold.empty and not dxy.empty:
    fig = go.Figure()
    g_close = "close" if "close" in gold.columns else gold.columns[-1]
    d_close = "close" if "close" in dxy.columns else dxy.columns[-1]
    fig.add_trace(go.Scatter(x=gold.get("date", gold.index), y=gold[g_close],
                             name="Gold", line=dict(color="#F5A623"), yaxis="y"))
    fig.add_trace(go.Scatter(x=dxy.get("date", dxy.index), y=dxy[d_close],
                             name="DXY", line=dict(color="#ef4444"), yaxis="y2"))
    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", height=350,
        yaxis=dict(title="Gold", side="left"), yaxis2=dict(title="DXY", side="right", overlaying="y"),
        font=dict(family="JetBrains Mono"), legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Central Bank Gold ──
st.divider()
st.subheader("Central Bank Gold Reserves")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Top Holders (tonnes)**")
    reserves = fetch_reserves()
    if reserves is not None and not reserves.empty:
        st.dataframe(reserves.head(15), use_container_width=True, hide_index=True)

with c2:
    st.markdown("**2025 Top Buyers**")
    buyers = fetch_buying_pace()
    if buyers is not None and not buyers.empty:
        fig = go.Figure(go.Bar(x=buyers["country"], y=buyers["tonnes_2025"],
                               marker_color="#F5A623"))
        fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                          height=300, font=dict(family="JetBrains Mono"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Annual Net Purchases (tonnes)**")
    annual = fetch_annual_demand()
    fig = go.Figure(go.Bar(x=annual["year"], y=annual["net_purchases_tonnes"], marker_color="#00d4ff"))
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                      height=250, font=dict(family="JetBrains Mono"))
    st.plotly_chart(fig, use_container_width=True)
