"""Page 7: Analytics Lab — Monte Carlo, GARCH, correlation, seasonality, technicals."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Analytics", layout="wide", page_icon="📊")
st.title("📊 Analytics Lab")

from src.data.spot_prices import fetch_history, fetch_multi_history
from src.analytics.monte_carlo import simulate_gold
from src.analytics.volatility import (
    realized_vol, ewma_vol, garch_forecast, vol_cone,
    ewma_vol_halflife, parkinson_vol, garman_klass_vol, rogers_satchell_vol
)
from src.analytics.correlation import current_correlation
from src.analytics.seasonality import monthly_seasonality, monthly_heatmap
from src.analytics.technicals import compute_all, support_resistance

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎲 Monte Carlo", "📈 Volatility", "🔗 Correlation", "📅 Seasonality", "📉 Technicals"])

# ── Monte Carlo ──
with tab1:
    st.subheader("Monte Carlo Price Simulation")
    c1, c2, c3 = st.columns(3)
    with c1:
        S0 = st.number_input("Current Price", value=3300.0, step=10.0, key="mc_s0")
        model = st.selectbox("Model", ["gbm", "jump"], key="mc_model")
    with c2:
        sigma_mc = st.number_input("Volatility (%)", value=18.0, step=1.0, key="mc_sig") / 100
        mu_mc = st.number_input("Drift (%)", value=5.0, step=1.0, key="mc_mu") / 100
    with c3:
        T_mc = st.number_input("Horizon (years)", value=1.0, step=0.25, key="mc_T")
        n_paths = st.selectbox("Simulations", [1000, 5000, 10000, 50000], index=2)

    if st.button("Run Simulation", key="mc_run"):
        with st.spinner("Simulating..."):
            result = simulate_gold(S0, sigma_mc, T_mc, mu_mc, model, n_paths)
        cone = result["cone"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cone["step"], y=cone["p95"], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=cone["step"], y=cone["p5"], fill="tonexty", fillcolor="rgba(245,166,35,0.1)",
                                 line=dict(width=0), name="90% CI"))
        fig.add_trace(go.Scatter(x=cone["step"], y=cone["p75"], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=cone["step"], y=cone["p25"], fill="tonexty", fillcolor="rgba(245,166,35,0.2)",
                                 line=dict(width=0), name="50% CI"))
        fig.add_trace(go.Scatter(x=cone["step"], y=cone["p50"], mode="lines",
                                 line=dict(color="#F5A623", width=2), name="Median"))
        fig.add_hline(y=S0, line_dash="dash", line_color="#555")
        fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                          height=450, title="Price Simulation Cone", xaxis_title="Trading Days",
                          yaxis_title="Price", font=dict(family="JetBrains Mono"))
        st.plotly_chart(fig, use_container_width=True)
        term = result["terminal"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Median End Price", f"${term['median']:,.0f}")
        c2.metric("95th Percentile", f"${term['p95']:,.0f}")
        c3.metric("5th Percentile", f"${term['p5']:,.0f}")
        c4.metric("P(Up)", f"{term['prob_up']:.1f}%")

# ── Volatility ──
with tab2:
    st.subheader("Configurable Volatility Analytics")
    gold_data = fetch_history("XAU/USD", period="3y")

    if gold_data is not None and not gold_data.empty:
        # Standardize columns
        gold_data.columns = [c.lower() for c in gold_data.columns]
        close_col = "close" if "close" in gold_data.columns else gold_data.columns[-1]
        prices = gold_data[close_col].dropna()

        # UI Selectors
        c1, c2 = st.columns(2)
        with c1:
            measure1 = st.selectbox(
                "Primary Volatility Measure",
                ["Close-to-Close (Standard)", "EWMA (Exponentially Weighted)", "Parkinson (High-Low)", "Garman-Klass (OHLC)", "Rogers-Satchell"],
                index=0, key="vol_m1"
            )
        with c2:
            measure2 = st.selectbox(
                "Comparison Measure (Optional)",
                ["None", "Close-to-Close (Standard)", "EWMA (Exponentially Weighted)", "Parkinson (High-Low)", "Garman-Klass (OHLC)", "Rogers-Satchell"],
                index=0, key="vol_m2"
            )

        # Parameters
        p1, p2 = st.columns(2)

        def get_vol_params(measure, key_suffix, col):
            with col:
                if measure == "EWMA (Exponentially Weighted)":
                    hl = st.slider(f"Half-life (days) - {key_suffix}", 5, 500, 120, key=f"hl_{key_suffix}")
                    span = 2 / (1 - np.exp(-np.log(2) / hl)) - 1
                    st.caption(f"λ ≈ {np.exp(-np.log(2) / hl):.4f} | Span ≈ {span:.1f}d")
                    return {"half_life": hl}
                elif measure != "None":
                    win = st.selectbox(f"Window (days) - {key_suffix}", [5, 10, 21, 42, 63, 126, 252], index=2, key=f"win_{key_suffix}")
                    return {"window": win}
            return {}

        params1 = get_vol_params(measure1, "Primary", p1)
        params2 = get_vol_params(measure2, "Secondary", p2)

        def compute_vol(measure, params):
            if measure == "Close-to-Close (Standard)":
                return realized_vol(prices, params.get("window", 21))
            elif measure == "EWMA (Exponentially Weighted)":
                return ewma_vol_halflife(prices, params.get("half_life", 120))
            elif measure == "Parkinson (High-Low)":
                return parkinson_vol(gold_data, params.get("window", 21))
            elif measure == "Garman-Klass (OHLC)":
                return garman_klass_vol(gold_data, params.get("window", 21))
            elif measure == "Rogers-Satchell":
                return rogers_satchell_vol(gold_data, params.get("window", 21))
            return None

        v1 = compute_vol(measure1, params1)
        v2 = compute_vol(measure2, params2)

        # Main Metric
        if v1 is not None and not v1.empty:
            curr_v1 = v1.iloc[-1]
            avg_v1 = v1.mean()
            std_v1 = v1.std()
            st.metric("Current Vol (Annualized)", f"{curr_v1:.2%}", delta=f"{curr_v1 - avg_v1:+.2%}")

            # Plotting
            fig = go.Figure()

            # Std Band for primary
            fig.add_hline(y=avg_v1, line_dash="dash", line_color="#555", annotation_text="Mean")
            fig.add_hrect(y0=max(0, avg_v1 - std_v1), y1=avg_v1 + std_v1,
                          fillcolor="rgba(245,166,35,0.05)", line_width=0, name="1 Std Band")

            # Primary line
            fig.add_trace(go.Scatter(x=v1.index, y=v1, name=measure1, line=dict(color="#F5A623", width=2)))

            # Secondary line
            if v2 is not None and not v2.empty:
                fig.add_trace(go.Scatter(x=v2.index, y=v2, name=measure2, line=dict(color="#00d4ff", width=1.5)))

            fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                              height=450, title=f"Realized Volatility: {measure1}", yaxis_title="Annualized Vol",
                              yaxis_tickformat=".0%", font=dict(family="JetBrains Mono"))
            st.plotly_chart(fig, use_container_width=True)

        # Vol cone
        vc = vol_cone(prices)
        if not vc.empty:
            st.markdown("**Volatility Cone**")
            st.dataframe(vc.style.format({
                "min": "{:.2%}", "q25": "{:.2%}", "median": "{:.2%}", "q75": "{:.2%}", "max": "{:.2%}", "current": "{:.2%}"
            }), use_container_width=True, hide_index=True)

        # GARCH
        garch = garch_forecast(prices)
        if garch.get("forecast"):
            st.markdown("**GARCH(1,1) Forecast**")
            gc1, gc2 = st.columns([1, 2])
            with gc1:
                st.write(f"Persistence: `{garch['params'].get('persistence', 'N/A')}`")
                st.write(f"Current GARCH Vol: `{garch.get('current_vol', 'N/A')}`")
            with gc2:
                forecast_df = pd.DataFrame({"Day": range(1, len(garch["forecast"])+1), "Forecast": garch["forecast"]})
                st.line_chart(forecast_df.set_index("Day"), height=150)

# ── Correlation ──
with tab3:
    st.subheader("Cross-Asset Correlation Matrix")
    assets = ["XAU/USD", "XAG/USD", "DXY", "WTI Crude", "BTC/USD", "S&P 500"]
    multi = fetch_multi_history(assets, period="1y")
    if multi:
        prices_dict = {}
        for name, df in multi.items():
            c = "close" if "close" in df.columns else df.columns[-1]
            prices_dict[name] = df.set_index(df.columns[0])[c] if "date" in df.columns else df[c]
        corr = current_correlation(prices_dict, window=60)
        if not corr.empty:
            fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn",
                            zmin=-1, zmax=1, aspect="auto")
            fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                              height=450, font=dict(family="JetBrains Mono"))
            st.plotly_chart(fig, use_container_width=True)

# ── Seasonality ──
with tab4:
    st.subheader("Gold Seasonality")
    gold_seas = fetch_history("XAU/USD", period="10y")
    if gold_seas is not None and not gold_seas.empty:
        monthly = monthly_seasonality(gold_seas, years=10)
        if not monthly.empty:
            colors = ["#10b981" if v > 0 else "#ef4444" for v in monthly["avg_return_pct"]]
            fig = go.Figure(go.Bar(x=monthly.index, y=monthly["avg_return_pct"], marker_color=colors))
            fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                              height=350, title="Average Monthly Returns (10Y)", yaxis_title="Return %",
                              font=dict(family="JetBrains Mono"))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(monthly[["avg_return_pct", "win_rate", "count"]], use_container_width=True)

# ── Technicals ──
with tab5:
    st.subheader("Technical Analysis")
    gold_tech = fetch_history("XAU/USD", period="1y")
    if gold_tech is not None and not gold_tech.empty:
        enhanced = compute_all(gold_tech)
        close_col = "close" if "close" in enhanced.columns else enhanced.columns[-1]
        date_col = "date" if "date" in enhanced.columns else enhanced.index
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=enhanced[date_col] if isinstance(date_col, str) else date_col,
                                 y=enhanced[close_col], name="Price", line=dict(color="#F5A623", width=2)))
        for ma, color in [("sma_20", "#00d4ff"), ("sma_50", "#a855f7"), ("sma_200", "#ef4444")]:
            if ma in enhanced.columns:
                fig.add_trace(go.Scatter(x=enhanced[date_col] if isinstance(date_col, str) else date_col,
                                         y=enhanced[ma], name=ma.upper(), line=dict(color=color, width=1, dash="dash")))
        fig.update_layout(template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                          height=400, title="Gold with Moving Averages", font=dict(family="JetBrains Mono"))
        st.plotly_chart(fig, use_container_width=True)
        # S/R levels
        sr = support_resistance(enhanced[close_col])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("R2", f"${sr['r2']:,.0f}")
        c2.metric("R1", f"${sr['r1']:,.0f}")
        c3.metric("Pivot", f"${sr['pivot']:,.0f}")
        c4.metric("S1", f"${sr['s1']:,.0f}")
        c5.metric("S2", f"${sr['s2']:,.0f}")
        # RSI
        if "rsi_14" in enhanced.columns:
            rsi_val = enhanced["rsi_14"].iloc[-1]
            st.metric("RSI (14)", f"{rsi_val:.1f}",
                      delta="Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral")
