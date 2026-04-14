"""Page 6: Trading Tools — Payoff diagrams, margin calc, basis arb."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Trading Tools", layout="wide", page_icon="🛠️")
st.title("🛠️ Trading Tools")

from src.trading.payoff import single_leg_payoff, multi_leg_payoff, plot_payoff, net_greeks
from src.trading.payoff import straddle, strangle, bull_call_spread, iron_condor
from src.trading.margin_calc import calculate_margin, margin_table
from src.trading.rollover import rollover_cost, basis_arb, almgren_chriss
from src.trading.contracts import MCX_CONTRACTS

tab1, tab2, tab3, tab4 = st.tabs(["📊 Payoff Builder", "💰 Margin Calculator", "🔄 Basis & Arb", "📐 Execution Model"])

# ── Payoff Builder ──
with tab1:
    st.subheader("Options Payoff Diagram")
    strategy = st.selectbox("Strategy Template", ["Custom", "Straddle", "Strangle", "Bull Call Spread", "Iron Condor"])
    F_price = st.number_input("Underlying Futures Price", value=3300.0, step=10.0, key="payoff_F")
    lot_size = st.number_input("Lot Size", value=100, step=10, key="payoff_lot")

    if strategy == "Custom":
        st.markdown("**Add Legs**")
        n_legs = st.number_input("Number of legs", 1, 6, 1)
        legs = []
        for i in range(n_legs):
            st.markdown(f"--- Leg {i+1}")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                k = st.number_input("Strike", value=F_price, step=10.0, key=f"k_{i}")
            with c2:
                p = st.number_input("Premium", value=50.0, step=1.0, key=f"p_{i}")
            with c3:
                ot = st.selectbox("Type", ["call", "put"], key=f"ot_{i}")
            with c4:
                pos = st.selectbox("Position", ["long", "short"], key=f"pos_{i}")
            legs.append({"strike": k, "premium": p, "type": ot, "position": pos, "qty": 1, "iv": 0.18})
    elif strategy == "Straddle":
        atm_k = st.number_input("ATM Strike", value=F_price, step=10.0, key="strad_k")
        c_prem = st.number_input("Call Premium", value=80.0, step=1.0, key="strad_cp")
        p_prem = st.number_input("Put Premium", value=75.0, step=1.0, key="strad_pp")
        pos = st.selectbox("Position", ["long", "short"], key="strad_pos")
        legs = straddle(atm_k, c_prem, p_prem, pos)
    elif strategy == "Strangle":
        ck = st.number_input("Call Strike (OTM)", value=F_price + 100, step=10.0, key="str_ck")
        pk = st.number_input("Put Strike (OTM)", value=F_price - 100, step=10.0, key="str_pk")
        cp = st.number_input("Call Premium", value=40.0, key="str_cp")
        pp = st.number_input("Put Premium", value=35.0, key="str_pp")
        pos = st.selectbox("Position", ["long", "short"], key="str_pos")
        legs = strangle(ck, pk, cp, pp, pos)
    elif strategy == "Bull Call Spread":
        lk = st.number_input("Lower Strike (Buy)", value=F_price - 50, step=10.0, key="bcs_lk")
        hk = st.number_input("Upper Strike (Sell)", value=F_price + 50, step=10.0, key="bcs_hk")
        lp = st.number_input("Lower Premium (Paid)", value=90.0, key="bcs_lp")
        hp = st.number_input("Upper Premium (Received)", value=50.0, key="bcs_hp")
        legs = bull_call_spread(lk, hk, lp, hp)
    else:  # Iron Condor
        legs = iron_condor(F_price - 200, F_price - 100, F_price + 100, F_price + 200, 15, 40, 40, 15)

    if legs:
        payoff_df = multi_leg_payoff(legs, lot_size=lot_size)
        if not payoff_df.empty:
            fig = plot_payoff(payoff_df, title=f"{strategy} Payoff")
            st.plotly_chart(fig, use_container_width=True)
            # Net Greeks
            ng = net_greeks(legs, F_price, 30 / 365)
            gc1, gc2, gc3, gc4 = st.columns(4)
            gc1.metric("Net Delta", f"{ng['delta']:.4f}")
            gc2.metric("Net Gamma", f"{ng['gamma']:.4f}")
            gc3.metric("Net Theta", f"{ng['theta']:.4f}")
            gc4.metric("Net Vega", f"{ng['vega']:.4f}")

# ── Margin Calculator ──
with tab2:
    st.subheader("MCX Margin Calculator")
    contract = st.selectbox("Contract", list(MCX_CONTRACTS.keys()))
    price = st.number_input("Current Price (₹)", value=95000.0, step=100.0, key="margin_price")
    lots = st.number_input("Number of Lots", value=1, min_value=1, max_value=100, key="margin_lots")
    result = calculate_margin(contract, price, lots)
    if "error" not in result:
        c1, c2, c3 = st.columns(3)
        c1.metric("Notional Value", f"₹{result['notional']:,.0f}")
        c2.metric("Initial Margin", f"₹{result['initial_margin']:,.0f}")
        c3.metric("Maintenance Margin", f"₹{result['maintenance_margin']:,.0f}")
    st.divider()
    st.markdown("**All MCX Contracts at ₹" + f"{price:,.0f}**")
    all_margins = margin_table(price)
    st.dataframe(pd.DataFrame(all_margins), use_container_width=True, hide_index=True)

# ── Basis & Arb ──
with tab3:
    st.subheader("MCX vs COMEX Basis")
    c1, c2, c3 = st.columns(3)
    with c1:
        mcx_p = st.number_input("MCX Price (₹/10g)", value=95000.0, step=100.0)
    with c2:
        comex_p = st.number_input("COMEX Price ($/oz)", value=3300.0, step=10.0)
    with c3:
        usdinr_p = st.number_input("USD/INR", value=84.5, step=0.1)
    arb = basis_arb(mcx_p, comex_p, usdinr_p)
    c1, c2, c3 = st.columns(3)
    c1.metric("MCX (₹/10g)", f"₹{arb['mcx_inr_10g']:,.0f}")
    c2.metric("COMEX→INR (₹/10g)", f"₹{arb['comex_inr_10g']:,.0f}")
    c3.metric("Basis", f"{arb['basis_pct']:.3f}%", delta=arb["signal"])
    if arb["arb_viable"]:
        st.success(f"Arbitrage opportunity detected: net {arb['net_after_costs_pct']:.3f}% after costs")
    else:
        st.info("No actionable arb — basis within transaction cost range")

    st.divider()
    st.subheader("Rollover Cost Calculator")
    c1, c2, c3 = st.columns(3)
    with c1:
        near = st.number_input("Near Month Price", value=95000.0, step=100.0, key="roll_near")
    with c2:
        far = st.number_input("Far Month Price", value=95500.0, step=100.0, key="roll_far")
    with c3:
        dte = st.number_input("Days to Near Expiry", value=15, min_value=1, key="roll_dte")
    roll = rollover_cost(near, far, 100, dte)
    c1, c2, c3 = st.columns(3)
    c1.metric("Spread", f"₹{roll['spread']:,.2f}")
    c2.metric("Annualized", f"{roll['annualized_pct']:.2f}%")
    c3.metric("Signal", roll["signal"])

# ── Execution Model ──
with tab4:
    st.subheader("Almgren-Chriss Optimal Execution")
    c1, c2 = st.columns(2)
    with c1:
        total_qty = st.number_input("Total Quantity", value=1000, step=100)
        T_periods = st.number_input("Time Periods", value=10, min_value=2, max_value=50)
        sigma_exec = st.number_input("Volatility (σ)", value=0.02, step=0.005, format="%.3f")
    with c2:
        eta = st.number_input("Temporary Impact (η)", value=0.001, step=0.0005, format="%.4f")
        gamma_exec = st.number_input("Permanent Impact (γ)", value=0.0005, step=0.0001, format="%.4f")
        lam = st.number_input("Risk Aversion (λ)", value=1e-6, format="%.7f")
    exec_result = almgren_chriss(total_qty, T_periods, sigma_exec, eta, gamma_exec, lam)
    sched_df = pd.DataFrame(exec_result["schedule"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sched_df["period"], y=sched_df["trade_qty"], marker_color="#F5A623", name="Trade Qty"))
    fig.add_trace(go.Scatter(x=sched_df["period"], y=sched_df["remaining"], mode="lines+markers",
                             line=dict(color="#00d4ff"), name="Remaining", yaxis="y2"))
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", height=350,
                      yaxis=dict(title="Trade Qty"), yaxis2=dict(title="Remaining", overlaying="y", side="right"),
                      font=dict(family="JetBrains Mono"))
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Expected Execution Cost", f"{exec_result['expected_cost']:,.2f}")
