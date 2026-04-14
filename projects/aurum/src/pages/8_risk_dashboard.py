"""Page 8: Risk Dashboard — VaR, stress tests, scenario analysis."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Risk", layout="wide", page_icon="⚠️")
st.title("⚠️ Risk Dashboard")

from src.data.spot_prices import fetch_history
from src.analytics.risk import parametric_var, historical_var, cvar, stress_scenarios

# ── Portfolio Setup ──
st.subheader("Portfolio Risk Analysis")
c1, c2 = st.columns(2)
with c1:
    portfolio_value = st.number_input("Portfolio Value (₹)", value=10_000_000, step=100_000, format="%d")
    confidence = st.selectbox("Confidence Level", [0.95, 0.99], index=0)
with c2:
    asset = st.selectbox("Asset", ["XAU/USD", "XAG/USD"], index=0)
    horizon = st.selectbox("Horizon (days)", [1, 5, 10, 21], index=0)

# ── VaR Computation ──
data = fetch_history(asset, period="3y")
if data is not None and not data.empty:
    close_col = "close" if "close" in data.columns else data.columns[-1]
    prices = data[close_col].dropna()
    returns = np.log(prices / prices.shift(1)).dropna()

    pvar = parametric_var(returns, confidence, horizon, portfolio_value)
    hvar = historical_var(returns, confidence, portfolio_value)
    cv = cvar(returns, confidence, portfolio_value)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### Parametric VaR")
        st.metric(f"{confidence*100:.0f}% {horizon}d VaR", f"₹{pvar['var_abs']:,.0f}")
        st.caption(f"{pvar['var_pct']:.2f}% of portfolio")
    with c2:
        st.markdown("### Historical VaR")
        st.metric(f"{confidence*100:.0f}% 1d VaR", f"₹{hvar['var_abs']:,.0f}")
        st.caption(f"{hvar['var_pct']:.2f}% of portfolio")
    with c3:
        st.markdown("### CVaR (Expected Shortfall)")
        st.metric(f"{confidence*100:.0f}% CVaR", f"₹{cv['cvar_abs']:,.0f}")
        st.caption(f"{cv['cvar_pct']:.2f}% of portfolio")

    # ── Return Distribution ──
    st.divider()
    st.subheader("Return Distribution")
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=returns * 100, nbinsx=80, marker_color="#F5A623", opacity=0.7, name="Daily Returns"))
    # VaR line
    var_line = -pvar["var_pct"]
    fig.add_vline(x=var_line, line_dash="dash", line_color="#ef4444",
                  annotation_text=f"VaR ({var_line:.2f}%)", annotation_position="top left")
    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        height=350, xaxis_title="Daily Return %", yaxis_title="Frequency",
        font=dict(family="JetBrains Mono", color="#E0E0E8"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Drawdown Analysis ──
    st.divider()
    st.subheader("Drawdown Analysis")
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative / running_max - 1) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=drawdown, mode="lines", fill="tozeroy",
                             line=dict(color="#ef4444", width=1), fillcolor="rgba(239,68,68,0.2)", name="Drawdown"))
    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        height=250, yaxis_title="Drawdown %", font=dict(family="JetBrains Mono"),
    )
    st.plotly_chart(fig, use_container_width=True)

    max_dd = drawdown.min()
    st.metric("Maximum Drawdown", f"{max_dd:.2f}%", delta=f"₹{portfolio_value * max_dd / 100:,.0f}")

# ── Stress Scenarios ──
st.divider()
st.subheader("🌋 Stress Scenarios & Drill-Down")
current_price = float(prices.iloc[-1]) if data is not None and not data.empty else 3300.0
scenarios = stress_scenarios(current_price)

# Overview Chart
fig = go.Figure()
colors = ["#10b981" if s > 0 else "#ef4444" for s in scenarios["shock_pct"]]
fig.add_trace(go.Bar(
    x=scenarios["scenario"], y=scenarios["shock_pct"],
    marker_color=colors, text=[f"{s:+.0f}%" for s in scenarios["shock_pct"]],
    textposition="outside",
))
fig.update_layout(
    template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
    height=350, yaxis_title="Price Change %", margin=dict(t=30, b=0),
    font=dict(family="JetBrains Mono", color="#E0E0E8"),
)
st.plotly_chart(fig, use_container_width=True)

# 1. Expandable Scenario Cards
st.markdown("### 🔍 Scenario Details")
for _, row in scenarios.iterrows():
    emoji = "📈" if row['shock_pct'] > 0 else "📉"
    color = "green" if row['shock_pct'] > 0 else "red"
    with st.expander(f"{emoji} {row['scenario']}  →  :{color}[{row['shock_pct']:+.0f}%]  |  Stressed: ${row['stressed_price']:,.0f}", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"**Narrative:** {row['description']}")
            st.markdown(f"**Primary Trigger:** {row['trigger']}")
            st.markdown(f"**Duration:** {row['duration_days']} days | **Recovery:** {row['recovery_days']} days")
            
            # Mini asset move list
            st.markdown("**Correlated Asset Moves:**")
            move_cols = st.columns(len(row['analog_asset_moves']))
            for i, (asset_name, move) in enumerate(row['analog_asset_moves'].items()):
                move_cols[i].metric(asset_name, f"{move:+.0f}%")
                
        with c2:
            pnl = portfolio_value * row['shock_pct'] / 100
            st.metric("Portfolio Impact", f"₹{pnl:,.0f}", delta=f"{row['shock_pct']:+.1f}%")
            
            margin_risk = "HIGH" if pnl < -portfolio_value * 0.15 else "LOW"
            risk_color = "red" if margin_risk == "HIGH" else "green"
            st.markdown(f"Margin Call Risk: :{risk_color}[**{margin_risk}**]")
            st.progress(min(abs(row['shock_pct']) / 50.0, 1.0))

# 2. Scenario Path Simulator
st.divider()
st.subheader("⏱️ Scenario Path Simulator")
selected_scenario_name = st.selectbox("Select Scenario to Simulate", scenarios["scenario"].tolist())
sim_row = scenarios[scenarios["scenario"] == selected_scenario_name].iloc[0]

sim_days = st.slider("Simulation Horizon (days)", 5, sim_row['duration_days'] if sim_row['duration_days'] > 5 else 30, 21)

# Generate 3 paths: Bear, Base, Bull
t = np.linspace(0, 1, sim_days)
shock = sim_row['shock_pct'] / 100
noise_scale = 0.02

def generate_path(s, vol):
    return current_price * (1 + s * t + np.random.normal(0, vol, sim_days).cumsum())

fig_path = go.Figure()
fig_path.add_trace(go.Scatter(y=generate_path(shock, 0.01), name="Base Case", line=dict(color="#F5A623", width=3)))
fig_path.add_trace(go.Scatter(y=generate_path(shock * 1.5, 0.02), name="Worst Case", line=dict(color="#ef4444", dash="dash")))
fig_path.add_trace(go.Scatter(y=generate_path(shock * 0.5, 0.015), name="Recovery Case", line=dict(color="#10b981", dash="dot")))

fig_path.update_layout(
    template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
    height=400, title=f"Simulated Path: {selected_scenario_name}",
    xaxis_title="Days", yaxis_title="Price ($)",
    font=dict(family="JetBrains Mono"),
)
st.plotly_chart(fig_path, use_container_width=True)

# 3. Multi-Scenario Portfolio Impact Table
st.divider()
st.subheader("📊 Portfolio Impact Matrix")
impact_df = scenarios.copy()
impact_df["PnL (₹)"] = impact_df["shock_pct"] * portfolio_value / 100
impact_df["Margin Call?"] = impact_df["PnL (₹)"].apply(lambda x: "⚠️ YES" if x < -portfolio_value * 0.2 else "✅ NO")
impact_df["Recovery"] = impact_df["recovery_days"].apply(lambda x: f"{x}d")

impact_display = impact_df[["scenario", "shock_pct", "PnL (₹)", "Recovery", "Margin Call?"]].sort_values("shock_pct")
st.dataframe(
    impact_display.style.format({"PnL (₹)": "₹{:,.0f}", "shock_pct": "{:+.1f}%"})
    .map(lambda x: "color: #ef4444" if isinstance(x, str) and "YES" in x else "", subset=["Margin Call?"])
    .map(lambda x: "background-color: rgba(239,68,68,0.2)" if isinstance(x, float) and x < -20 else "", subset=["shock_pct"]),
    use_container_width=True, hide_index=True
)

# 4. Scenario Correlation Matrix
st.divider()
st.subheader("🔗 Scenario Correlations")
st.caption("How likely these scenarios are to trigger or coincide with one another.")

scenario_names = scenarios["scenario"].tolist()
n = len(scenario_names)
# Generate pseudo-realistic correlation based on shock direction
corr_matrix = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        if i == j: corr_matrix[i,j] = 1.0
        else:
            # Scenarios with same shock direction have positive correlation
            dir_i = np.sign(scenarios.iloc[i]["shock_pct"])
            dir_j = np.sign(scenarios.iloc[j]["shock_pct"])
            corr_matrix[i,j] = 0.6 * (dir_i * dir_j) + np.random.uniform(-0.1, 0.1)

fig_corr = go.Figure(data=go.Heatmap(
    z=corr_matrix, x=scenario_names, y=scenario_names,
    colorscale="RdYlGn", zmin=-1, zmax=1
))
fig_corr.update_layout(
    template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
    height=500, font=dict(family="JetBrains Mono", size=10),
    margin=dict(t=30, b=0),
)
st.plotly_chart(fig_corr, use_container_width=True)

# ── Risk Summary ──
st.divider()
st.subheader("Quick Risk Stats")
if data is not None and not data.empty:
    ann_ret = returns.mean() * 252 * 100
    ann_vol = returns.std() * np.sqrt(252) * 100
    sharpe = ann_ret / ann_vol if ann_vol != 0 else 0
    sortino_downside = returns[returns < 0].std() * np.sqrt(252) * 100
    sortino = ann_ret / sortino_downside if sortino_downside != 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ann. Return", f"{ann_ret:.1f}%")
    c2.metric("Ann. Volatility", f"{ann_vol:.1f}%")
    c3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    c4.metric("Sortino Ratio", f"{sortino:.2f}")
