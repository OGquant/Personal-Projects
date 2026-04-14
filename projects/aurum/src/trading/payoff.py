"""
Options payoff diagrams and multi-leg position builder.
Supports MCX Gold/Silver option strategies.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.analytics.greeks import greeks as compute_greeks


def single_leg_payoff(strike: float, premium: float, option_type: str = "call",
                      position: str = "long", lot_size: float = 100,
                      price_range: tuple = None) -> pd.DataFrame:
    """Compute payoff for a single option leg."""
    if price_range is None:
        price_range = (strike * 0.85, strike * 1.15)
    prices = np.linspace(price_range[0], price_range[1], 200)
    multiplier = 1 if position == "long" else -1

    if option_type == "call":
        intrinsic = np.maximum(prices - strike, 0)
    else:
        intrinsic = np.maximum(strike - prices, 0)

    payoff = multiplier * (intrinsic - premium) * lot_size
    return pd.DataFrame({"price": prices, "payoff": payoff})


def multi_leg_payoff(legs: list[dict], lot_size: float = 100, price_range: tuple = None) -> pd.DataFrame:
    """
    Compute combined payoff for multiple legs.
    Each leg: {"strike": K, "premium": P, "type": "call"|"put", "position": "long"|"short", "qty": 1}
    """
    if not legs:
        return pd.DataFrame()
    strikes = [l["strike"] for l in legs]
    if price_range is None:
        price_range = (min(strikes) * 0.80, max(strikes) * 1.20)
    prices = np.linspace(price_range[0], price_range[1], 300)
    total_payoff = np.zeros_like(prices)
    total_premium = 0

    for leg in legs:
        K = leg["strike"]
        P = leg["premium"]
        qty = leg.get("qty", 1)
        mult = qty if leg["position"] == "long" else -qty
        if leg["type"] == "call":
            intrinsic = np.maximum(prices - K, 0)
        else:
            intrinsic = np.maximum(K - prices, 0)
        total_payoff += mult * (intrinsic - P) * lot_size
        total_premium += mult * P * lot_size

    df = pd.DataFrame({"price": prices, "payoff": total_payoff})
    df["breakeven"] = np.isclose(df["payoff"], 0, atol=lot_size * 0.5)
    return df


def plot_payoff(df: pd.DataFrame, title: str = "Option Payoff") -> go.Figure:
    """Create interactive Plotly payoff diagram."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["price"], y=df["payoff"], mode="lines",
        line=dict(color="#F5A623", width=2), name="P&L",
        fill="tozeroy",
        fillcolor="rgba(245,166,35,0.1)",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    # Mark breakeven points
    zero_crossings = df[df["payoff"].diff().apply(np.sign) != 0]
    if not zero_crossings.empty:
        for _, row in zero_crossings.iterrows():
            fig.add_vline(x=row["price"], line_dash="dot", line_color="#00d4ff", opacity=0.5)
    fig.update_layout(
        title=title, xaxis_title="Underlying Price", yaxis_title="P&L",
        template="plotly_dark", plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font=dict(family="JetBrains Mono", color="#E0E0E8"),
    )
    return fig


def net_greeks(legs: list[dict], F: float, T: float, r: float = 0.05) -> dict:
    """Compute net portfolio Greeks across all legs."""
    net = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    for leg in legs:
        K, sigma = leg["strike"], leg.get("iv", 0.25)
        qty = leg.get("qty", 1)
        mult = qty if leg["position"] == "long" else -qty
        g = compute_greeks(F, K, T, r, sigma, leg["type"])
        net["delta"] += mult * g.delta
        net["gamma"] += mult * g.gamma
        net["theta"] += mult * g.theta
        net["vega"] += mult * g.vega
    return {k: round(v, 4) for k, v in net.items()}


# ── Pre-built strategies ──

def straddle(strike: float, call_prem: float, put_prem: float, position: str = "long") -> list[dict]:
    return [
        {"strike": strike, "premium": call_prem, "type": "call", "position": position, "qty": 1},
        {"strike": strike, "premium": put_prem, "type": "put", "position": position, "qty": 1},
    ]

def strangle(call_strike: float, put_strike: float, call_prem: float, put_prem: float, position: str = "long") -> list[dict]:
    return [
        {"strike": call_strike, "premium": call_prem, "type": "call", "position": position, "qty": 1},
        {"strike": put_strike, "premium": put_prem, "type": "put", "position": position, "qty": 1},
    ]

def bull_call_spread(low_K: float, high_K: float, low_prem: float, high_prem: float) -> list[dict]:
    return [
        {"strike": low_K, "premium": low_prem, "type": "call", "position": "long", "qty": 1},
        {"strike": high_K, "premium": high_prem, "type": "call", "position": "short", "qty": 1},
    ]

def iron_condor(put_low: float, put_high: float, call_low: float, call_high: float,
                p1: float, p2: float, c1: float, c2: float) -> list[dict]:
    return [
        {"strike": put_low, "premium": p1, "type": "put", "position": "long", "qty": 1},
        {"strike": put_high, "premium": p2, "type": "put", "position": "short", "qty": 1},
        {"strike": call_low, "premium": c1, "type": "call", "position": "short", "qty": 1},
        {"strike": call_high, "premium": c2, "type": "call", "position": "long", "qty": 1},
    ]
