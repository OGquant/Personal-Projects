"""Page 3: Options Flow — Chain, IV Smile, Greeks."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Options Flow", layout="wide", page_icon="🔗")
st.title("🔗 Options Flow & Greeks")

from src.analytics.greeks import greeks, implied_vol, black76_price
from src.trading.contracts import MCX_CONTRACTS, CME_CONTRACTS

# ── Options Calculator ──
st.subheader("Black-76 Options Calculator")
st.caption("For futures options (Gold/Silver on CME/MCX)")

col1, col2, col3 = st.columns(3)
with col1:
    F = st.number_input("Futures Price", value=3300.0, step=10.0)
    K = st.number_input("Strike Price", value=3300.0, step=10.0)
with col2:
    T_days = st.number_input("Days to Expiry", value=30, min_value=1, max_value=365)
    T = T_days / 365
    sigma = st.number_input("Implied Volatility (%)", value=18.0, min_value=1.0, max_value=100.0) / 100
with col3:
    r = st.number_input("Risk-Free Rate (%)", value=5.0, min_value=0.0, max_value=20.0) / 100
    opt_type = st.selectbox("Option Type", ["call", "put"])

g = greeks(F, K, T, r, sigma, opt_type)
cols = st.columns(6)
cols[0].metric("Price", f"${g.price:.2f}")
cols[1].metric("Delta", f"{g.delta:.4f}")
cols[2].metric("Gamma", f"{g.gamma:.6f}")
cols[3].metric("Theta", f"{g.theta:.4f}")
cols[4].metric("Vega", f"{g.vega:.4f}")
cols[5].metric("Rho", f"{g.rho:.4f}")

# ── IV Smile Simulator ──
st.divider()
st.subheader("IV Smile Visualizer")

strikes = np.linspace(F * 0.85, F * 1.15, 30)
base_vol = sigma
# Simulated smile using quadratic skew
moneyness = np.log(strikes / F)
smile_vols = base_vol * (1 + 0.5 * moneyness**2 + 0.3 * moneyness)  # skew + smile

fig = go.Figure()
fig.add_trace(go.Scatter(x=strikes, y=smile_vols * 100, mode="lines+markers",
                         line=dict(color="#F5A623", width=2), marker=dict(size=4), name="IV"))
fig.add_vline(x=F, line_dash="dash", line_color="#555", annotation_text="ATM")
fig.update_layout(
    title="Implied Volatility Smile", xaxis_title="Strike", yaxis_title="IV (%)",
    template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", height=350,
    font=dict(family="JetBrains Mono", color="#E0E0E8"),
)
st.plotly_chart(fig, use_container_width=True)

# ── Synthetic Option Chain ──
st.divider()
st.subheader("Option Chain (Computed)")
chain_strikes = np.arange(F - 200, F + 210, 50)
chain_data = []
for k in chain_strikes:
    for ot in ["call", "put"]:
        m = np.log(k / F)
        iv = base_vol * (1 + 0.5 * m**2 + 0.3 * m)
        g = greeks(F, k, T, r, iv, ot)
        chain_data.append({
            "Strike": k, "Type": ot.upper(), "Price": f"${g.price:.2f}", "IV": f"{iv*100:.1f}%",
            "Delta": f"{g.delta:.3f}", "Gamma": f"{g.gamma:.5f}", "Theta": f"{g.theta:.3f}", "Vega": f"{g.vega:.3f}",
        })
chain_df = pd.DataFrame(chain_data)
st.dataframe(chain_df, use_container_width=True, hide_index=True, height=400)

# ── Contract Specs Reference ──
st.divider()
st.subheader("Contract Specifications")
tab_mcx, tab_cme = st.tabs(["MCX Contracts", "CME COMEX Contracts"])
with tab_mcx:
    mcx_data = [{"Name": s.name, "Symbol": s.symbol, "Lot Size": f"{s.lot_size} {s.lot_unit}",
                 "Tick": s.tick_size, "Margin %": s.margin_pct, "Quote": s.quote_unit}
                for s in MCX_CONTRACTS.values()]
    st.dataframe(pd.DataFrame(mcx_data), use_container_width=True, hide_index=True)
with tab_cme:
    cme_data = [{"Name": s.name, "Symbol": s.symbol, "Lot Size": f"{s.lot_size} {s.lot_unit}",
                 "Tick": s.tick_size, "Margin %": s.margin_pct, "Quote": s.quote_unit}
                for s in CME_CONTRACTS.values()]
    st.dataframe(pd.DataFrame(cme_data), use_container_width=True, hide_index=True)
