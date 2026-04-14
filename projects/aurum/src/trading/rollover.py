"""Rollover calculator and MCX-COMEX basis arbitrage scanner."""
import numpy as np


def rollover_cost(near_price: float, far_price: float, lot_size: float, days_to_expiry: int) -> dict:
    """Calculate cost/benefit of rolling from near to far contract."""
    spread = far_price - near_price
    spread_pct = (spread / near_price * 100) if near_price else 0
    annualized = (spread_pct / days_to_expiry * 365) if days_to_expiry > 0 else 0
    total_cost = spread * lot_size
    return {
        "near_price": near_price, "far_price": far_price, "spread": round(spread, 2),
        "spread_pct": round(spread_pct, 3), "annualized_pct": round(annualized, 2),
        "total_roll_cost": round(total_cost, 2), "days_to_expiry": days_to_expiry,
        "signal": "contango" if spread > 0 else "backwardation",
    }


def basis_arb(mcx_price_inr: float, comex_price_usd: float, usdinr: float,
              mcx_lot_grams: float = 100, comex_lot_oz: float = 100,
              transaction_cost_pct: float = 0.05) -> dict:
    """MCX vs COMEX basis arbitrage calculator."""
    # Convert COMEX to INR per 10g for comparison
    grams_per_oz = 31.1035
    comex_per_gram = comex_price_usd / grams_per_oz
    comex_inr_per_10g = comex_per_gram * usdinr * 10
    # MCX quotes in INR per 10g
    basis = mcx_price_inr - comex_inr_per_10g
    basis_pct = (basis / comex_inr_per_10g * 100) if comex_inr_per_10g else 0
    net_basis_pct = basis_pct - transaction_cost_pct * 2  # round trip
    return {
        "mcx_inr_10g": round(mcx_price_inr, 0), "comex_inr_10g": round(comex_inr_per_10g, 0),
        "basis_inr": round(basis, 0), "basis_pct": round(basis_pct, 3),
        "net_after_costs_pct": round(net_basis_pct, 3),
        "signal": "MCX premium" if basis > 0 else "COMEX premium",
        "arb_viable": abs(net_basis_pct) > 0.1,
    }


def almgren_chriss(total_qty: int, T_periods: int, sigma: float, eta: float,
                   gamma: float, lam: float) -> dict:
    """
    Almgren-Chriss optimal execution schedule.
    total_qty: shares to execute, T_periods: time periods,
    sigma: volatility, eta: temporary impact, gamma: permanent impact, lam: risk aversion.
    """
    kappa_sq = lam * sigma**2 / eta
    kappa = np.sqrt(kappa_sq)
    schedule = []
    remaining = total_qty
    for j in range(T_periods):
        # Optimal trade rate
        trade = total_qty * np.sinh(kappa * (T_periods - j)) / np.sinh(kappa * T_periods)
        trade_qty = min(int(trade), remaining)
        remaining -= trade_qty
        schedule.append({"period": j + 1, "trade_qty": trade_qty, "remaining": remaining})
    # If rounding left residual
    if remaining > 0:
        schedule[-1]["trade_qty"] += remaining
        schedule[-1]["remaining"] = 0
    expected_cost = 0.5 * gamma * total_qty**2 + eta * sum(s["trade_qty"]**2 for s in schedule)
    return {"schedule": schedule, "expected_cost": round(expected_cost, 2), "kappa": round(kappa, 4)}
