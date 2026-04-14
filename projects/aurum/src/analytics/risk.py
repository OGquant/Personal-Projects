"""Risk metrics: Parametric VaR, Historical VaR, CVaR, stress scenarios."""
import numpy as np
import pandas as pd


def parametric_var(returns: pd.Series, confidence: float = 0.95, horizon: int = 1, portfolio_value: float = 1e6) -> dict:
    """Parametric (Gaussian) VaR."""
    mu = returns.mean() * horizon
    sigma = returns.std() * np.sqrt(horizon)
    from scipy.stats import norm
    z = norm.ppf(1 - confidence)
    var_pct = -(mu + z * sigma)
    var_abs = var_pct * portfolio_value
    return {"var_pct": round(var_pct * 100, 2), "var_abs": round(var_abs, 0), "confidence": confidence, "horizon_days": horizon}


def historical_var(returns: pd.Series, confidence: float = 0.95, portfolio_value: float = 1e6) -> dict:
    """Historical simulation VaR."""
    sorted_returns = returns.sort_values()
    idx = int((1 - confidence) * len(sorted_returns))
    var_pct = -sorted_returns.iloc[idx]
    return {"var_pct": round(var_pct * 100, 2), "var_abs": round(var_pct * portfolio_value, 0), "confidence": confidence}


def cvar(returns: pd.Series, confidence: float = 0.95, portfolio_value: float = 1e6) -> dict:
    """Conditional VaR (Expected Shortfall)."""
    sorted_returns = returns.sort_values()
    idx = int((1 - confidence) * len(sorted_returns))
    tail = sorted_returns.iloc[:idx]
    cvar_pct = -tail.mean()
    return {"cvar_pct": round(cvar_pct * 100, 2), "cvar_abs": round(cvar_pct * portfolio_value, 0), "confidence": confidence}


def stress_scenarios(current_price: float) -> pd.DataFrame:
    """Pre-defined stress scenarios for gold with expanded metadata."""
    scenarios = [
        ("2008 GFC", -30.0, "Liquidity crisis, margin calls force gold selling",
         {"duration_days": 90, "trigger": "Lehman collapse + deleveraging", 
          "peak_vix": 89.5, "usd_change": +15.0, "rates_change": -3.0,
          "recovery_days": 180, "analog_asset_moves": {"S&P 500": -55, "DXY": +20, "Oil": -70}}),
        ("2013 Taper Tantrum", -28.0, "Sharp real rate spike on QE tapering fears",
         {"duration_days": 60, "trigger": "Bernanke QE tapering hint", 
          "peak_vix": 25.0, "usd_change": +8.0, "rates_change": +1.5,
          "recovery_days": 365, "analog_asset_moves": {"10Y Yield": +100, "EM Equities": -20}}),
        ("2020 COVID Crash", -12.0, "Brief margin-call selloff before recovery",
         {"duration_days": 15, "trigger": "Global lockdown, dash for cash", 
          "peak_vix": 82.7, "usd_change": +10.0, "rates_change": -1.0,
          "recovery_days": 30, "analog_asset_moves": {"S&P 500": -34, "BTC": -50}}),
        ("2022 Rate Hike Cycle", -22.0, "Aggressive Fed hiking, DXY surge",
         {"duration_days": 200, "trigger": "Inflation pivot, 75bps hikes", 
          "peak_vix": 35.0, "usd_change": +18.0, "rates_change": +4.0,
          "recovery_days": 150, "analog_asset_moves": {"Nasdaq": -33, "DXY": +20}}),
        ("Geopolitical Shock", +15.0, "Major conflict escalation, safe-haven bid",
         {"duration_days": 10, "trigger": "Suez/Hormuz closure or similar", 
          "peak_vix": 45.0, "usd_change": +5.0, "rates_change": -0.5,
          "recovery_days": 90, "analog_asset_moves": {"Oil": +40, "Defense Stocks": +25}}),
        ("Dollar Collapse", +35.0, "Loss of reserve currency confidence",
         {"duration_days": 365, "trigger": "Sovereign debt crisis, hyperinflation", 
          "peak_vix": 40.0, "usd_change": -40.0, "rates_change": +10.0,
          "recovery_days": 1000, "analog_asset_moves": {"BTC": +500, "DXY": -40}}),
        ("Stagflation", +25.0, "High inflation + recession = gold rally",
         {"duration_days": 500, "trigger": "Supply shocks + wage-price spiral", 
          "peak_vix": 30.0, "usd_change": -5.0, "rates_change": +2.0,
          "recovery_days": 730, "analog_asset_moves": {"Real Estate": -20, "CPI": +10}}),
        ("Deflation Scare", -20.0, "Demand destruction, real rates spike",
         {"duration_days": 180, "trigger": "China property crash / AI-led glut", 
          "peak_vix": 50.0, "usd_change": +15.0, "rates_change": -2.0,
          "recovery_days": 365, "analog_asset_moves": {"Commodities": -40, "CPI": -2}}),
        ("Central Bank Panic Buy", +20.0, "Coordinated EM central bank buying",
         {"duration_days": 120, "trigger": "Sanctions-driven reserve diversification", 
          "peak_vix": 20.0, "usd_change": -5.0, "rates_change": 0.0,
          "recovery_days": 0, "analog_asset_moves": {"Treasuries": -10, "Gold Stocks": +40}}),
        ("India/China Demand Shock", +10.0, "Festival/policy-driven physical demand surge",
         {"duration_days": 45, "trigger": "Import duty cuts + wedding season", 
          "peak_vix": 15.0, "usd_change": 0.0, "rates_change": 0.0,
          "recovery_days": 60, "analog_asset_moves": {"Silver": +15, "INR": -2}}),
    ]
    records = []
    for name, shock_pct, desc, details in scenarios:
        stressed = current_price * (1 + shock_pct / 100)
        record = {
            "scenario": name,
            "shock_pct": shock_pct,
            "stressed_price": round(stressed, 0),
            "description": desc,
            **details
        }
        records.append(record)
    return pd.DataFrame(records)
