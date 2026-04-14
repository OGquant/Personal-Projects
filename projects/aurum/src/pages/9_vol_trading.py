import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.data.spot_prices import fetch_live_prices, fetch_history
from src.analytics.volatility import (
    realized_vol, ewma_vol_halflife, parkinson_vol, 
    garman_klass_vol, rogers_satchell_vol
)
from src.analytics.greeks import implied_vol
from src.config import Config

# Page Config
st.set_page_config(page_title="AURUM | Vol Trading Lab", layout="wide")

# Theme Colors
GOLD = "#F5A623"
GREEN = "#10b981"
RED = "#ef4444"
BLUE = "#00d4ff"
PURPLE = "#a855f7"
BG_COLOR = "#0E1117"

def load_data(asset_key: str):
    """Fetch 1Y history and live price for the asset."""
    history = fetch_history(asset_key, period="1y")
    live_prices = fetch_live_prices()
    
    # Extract current spot price
    if not live_prices.empty:
        current_row = live_prices[live_prices['instrument'] == asset_key]
        if not current_row.empty:
            spot = float(current_row.iloc[0]['price'])
        else:
            # Fallback to last close in history
            spot = float(history['close'].iloc[-1]) if not history.empty else 0.0
    else:
        spot = float(history['close'].iloc[-1]) if not history.empty else 0.0
        
    return history, spot

def main():
    st.title("🌊 Vol Trading Lab")
    st.markdown("Institutional volatility intelligence: IV vs RV spreads & signals.")

    # --- Section 1: Instrument + IV Input ---
    with st.sidebar:
        st.header("Parameters")
        asset = st.selectbox("Asset", ["XAU/USD", "XAG/USD"])
        history, spot = load_data(asset)
        
        st.metric(f"Current {asset} Spot", f"${spot:,.2f}")
        
        st.subheader("Option Quote")
        atm_price = st.number_input("ATM Option Price", value=spot * 0.02, format="%.2f")
        days_to_expiry = st.number_input("Days to Expiry", value=30, min_value=1)
        risk_free_rate = st.number_input("Risk-free Rate (%)", value=5.0, step=0.1) / 100
        
        compute_btn = st.button("Compute IV", use_container_width=True)

    # Calculate Current IV
    iv_current = None
    if compute_btn or "iv_current" in st.session_state:
        # T = days / 365, F = spot (proxy), K = spot (ATM)
        T = days_to_expiry / 365.0
        try:
            iv_current = implied_vol(
                F=spot, K=spot, T=T, r=risk_free_rate, 
                market_price=atm_price, option_type="call"
            )
            st.session_state.iv_current = iv_current
        except Exception as e:
            st.error(f"IV Computation failed: {e}")
    
    iv_display = st.session_state.get("iv_current", 0.0)

    # --- Section 2: RV Measure Selector ---
    st.divider()
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("RV Measure")
        rv_choice = st.selectbox(
            "Realized Volatility Measure",
            [
                "EWMA (Half-life 120d)",
                "EWMA (Half-life 60d)",
                "EWMA (Half-life 30d)",
                "Close-to-Close 21d",
                "Close-to-Close 63d",
                "Parkinson 21d",
                "Garman-Klass 21d",
                "Rogers-Satchell 21d",
                "Custom EWMA Half-life"
            ]
        )
        
        half_life = 120
        if rv_choice == "Custom EWMA Half-life":
            half_life = st.slider("Half-life (days)", 5, 252, 60)
            
        # Compute RV series for the chosen measure
        if history.empty:
            st.error("No historical data found.")
            return

        prices = history['close']
        if "EWMA" in rv_choice:
            if "120d" in rv_choice: hl = 120
            elif "60d" in rv_choice: hl = 60
            elif "30d" in rv_choice: hl = 30
            else: hl = half_life
            rv_series = ewma_vol_halflife(prices, half_life=hl)
        elif "Close-to-Close 21d" in rv_choice:
            rv_series = realized_vol(prices, window=21)
        elif "Close-to-Close 63d" in rv_choice:
            rv_series = realized_vol(prices, window=63)
        elif "Parkinson" in rv_choice:
            rv_series = parkinson_vol(history, window=21)
        elif "Garman-Klass" in rv_choice:
            rv_series = garman_klass_vol(history, window=21)
        elif "Rogers-Satchell" in rv_choice:
            rv_series = rogers_satchell_vol(history, window=21)
        
        current_rv = float(rv_series.iloc[-1]) if not rv_series.empty else 0.0

    # --- Section 3: Vol Premium Dashboard ---
    with col2:
        # 1Y Proxy IV Series (30d IV proxy = 30d EWMA * 1.12)
        iv_proxy_series = ewma_vol_halflife(prices, half_life=30) * 1.12
        premium_series = iv_proxy_series - rv_series
        
        # Current Metrics
        premium_current = iv_display - current_rv
        
        # Z-score vs 1Y history
        mean_prem = premium_series.mean()
        std_prem = premium_series.std()
        z_score = (premium_current - mean_prem) / std_prem if std_prem != 0 else 0.0
        
        # Signal
        if premium_current > 0.02: signal, sig_color = "SELL VOL", GREEN
        elif premium_current < -0.02: signal, sig_color = "BUY VOL", RED
        else: signal, sig_color = "NEUTRAL", "gray"

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("IV (Current)", f"{iv_display:.1%}")
        m2.metric("RV (Selected)", f"{current_rv:.1%}")
        m3.metric("Vol Premium", f"{premium_current:+.1%}", 
                  delta=f"{premium_current:.1%}", delta_color="normal")
        m4.metric("Z-Score", f"{z_score:.2f}")
        m5.markdown(f"**Signal**\n\n<h3 style='color:{sig_color}; margin:0;'>{signal}</h3>", unsafe_allow_html=True)

    # --- Charts ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Rolling Vol Premium History (1Y)")
        fig_vol = go.Figure()
        
        fig_vol.add_trace(go.Scatter(
            x=history['date'], y=iv_proxy_series, name="Proxy IV (30d EWMA * 1.12)",
            line=dict(color=PURPLE, width=1.5)
        ))
        fig_vol.add_trace(go.Scatter(
            x=history['date'], y=rv_series, name=f"RV ({rv_choice})",
            line=dict(color=BLUE, width=1.5)
        ))
        
        # Spread Chart
        fig_prem = go.Figure()
        fig_prem.add_trace(go.Scatter(
            x=history['date'], y=premium_series, name="IV-RV Spread",
            line=dict(color=GOLD, width=1),
            fill='tozeroy', fillcolor='rgba(245, 166, 35, 0.1)'
        ))
        fig_prem.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
        
        fig_vol.update_layout(
            plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR, 
            template="plotly_dark", height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_vol, use_container_width=True)
        
        fig_prem.update_layout(
            title="Vol Premium (IV - RV)",
            plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR, 
            template="plotly_dark", height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_prem, use_container_width=True)

    with c2:
        st.subheader("Vol Premium Distribution")
        
        clean_premium = premium_series.dropna()
        hist_data = clean_premium.values
        
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=hist_data, nbinsx=50, name="Frequency",
            marker_color=GOLD, opacity=0.6
        ))
        
        # Vertical line for current premium
        fig_dist.add_vline(x=premium_current, line_width=3, line_dash="dash", line_color=RED)
        fig_dist.add_annotation(
            x=premium_current, y=1, yref="paper",
            text=f"Current: {premium_current:.1%}",
            showarrow=True, arrowhead=1, ax=40, ay=-40,
            bgcolor=RED, font=dict(color="white")
        )
        
        percentile = (clean_premium < premium_current).mean() * 100
        
        fig_dist.update_layout(
            plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR, 
            template="plotly_dark", height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Premium (IV - RV)",
            yaxis_title="Frequency"
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        st.info(f"The current vol premium is at the **{percentile:.1f}th percentile** of the past 1 year.")

    # --- Section 4: Strategy Implications ---
    st.divider()
    st.subheader("Strategy Implications")
    
    col_strat1, col_strat2 = st.columns([2, 1])
    
    with col_strat1:
        if z_score > 1.5:
            st.success("### 🔥 IV is Rich (Z > 1.5)")
            st.markdown("""
            **Market Regime:** Fear is overpriced. Realized volatility is significantly lower than what options are pricing.
            
            **Recommended Structures:**
            - **Short Straddles / Strangles:** High theta decay, profit from IV crush.
            - **Iron Condors:** Defined risk vol selling if you expect a range.
            - **Covered Calls:** Enhanced yield on core positions as call premium is inflated.
            """)
        elif z_score < -1.5:
            st.error("### ❄️ IV is Cheap (Z < -1.5)")
            st.markdown("""
            **Market Regime:** Complacency. Market is pricing very little movement despite historical evidence.
            
            **Recommended Structures:**
            - **Long Straddles:** Cheap gamma. Profitable if the asset breaks out in either direction.
            - **Calendar Spreads:** Buy back month, sell front month to play for a vol pick-up.
            - **Protective Puts:** Ideal time to hedge long positions as protection is 'on sale'.
            """)
        elif abs(z_score) < 0.5:
            st.info("### ⚖️ IV is Fair Value")
            st.markdown("""
            **Market Regime:** Efficiency. Premium is near historical norms.
            
            **Recommended Approach:**
            - Focus on **directional positioning** (Delta) rather than Vol/Theta plays.
            - Use spreads (Bull Call / Bear Put) to keep costs low while taking a view.
            """)
        else:
            st.warning("### ⚠️ Moderate Premium/Discount")
            st.markdown("IV is drifting away from RV. Monitor for trend reversal or wait for extreme Z-score before aggressive vol positioning.")

    with col_strat2:
        st.markdown("**Quick Reference**")
        strat_df = pd.DataFrame([
            {"Strategy": "Short Straddle", "Vol View": "Short", "Edge": "High Theta"},
            {"Strategy": "Long Straddle", "Vol View": "Long", "Edge": "Cheap Gamma"},
            {"Strategy": "Iron Condor", "Vol View": "Short", "Edge": "Risk-Defined"},
            {"Strategy": "Calendar Spread", "Vol View": "Long (Term)", "Edge": "Vol Pick-up"},
        ])
        st.table(strat_df)

if __name__ == "__main__":
    main()
