"""
Black-76 Options Greeks for futures options (Gold/Silver).
Black-76 is the correct model for options on futures, not Black-Scholes.
"""
import numpy as np
from scipy.stats import norm
from dataclasses import dataclass


@dataclass
class GreeksResult:
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    iv: float = 0.0


def black76_price(F: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """Black-76 option price. F=futures price, K=strike, T=time to expiry (years), r=risk-free rate, sigma=vol."""
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return max(F - K, 0)
        return max(K - F, 0)

    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    else:
        return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def greeks(F: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> GreeksResult:
    """Compute all Greeks using Black-76."""
    if T <= 1e-10 or sigma <= 1e-10:
        intrinsic = max(F - K, 0) if option_type == "call" else max(K - F, 0)
        delta = 1.0 if (option_type == "call" and F > K) else (-1.0 if option_type == "put" and F < K else 0.0)
        return GreeksResult(price=intrinsic, delta=delta, gamma=0, theta=0, vega=0, rho=0)

    sqrt_T = np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    df = np.exp(-r * T)

    price = black76_price(F, K, T, r, sigma, option_type)

    if option_type == "call":
        delta = df * norm.cdf(d1)
    else:
        delta = -df * norm.cdf(-d1)

    gamma = df * norm.pdf(d1) / (F * sigma * sqrt_T)
    vega = F * df * norm.pdf(d1) * sqrt_T / 100  # per 1% vol change
    theta = (-F * df * norm.pdf(d1) * sigma / (2 * sqrt_T) - r * price) / 365  # per day

    if option_type == "call":
        rho = T * df * F * norm.cdf(d1) / 100  # per 1% rate change
    else:
        rho = -T * df * F * norm.cdf(-d1) / 100

    return GreeksResult(
        price=round(price, 4), delta=round(delta, 4), gamma=round(gamma, 6),
        theta=round(theta, 4), vega=round(vega, 4), rho=round(rho, 4),
    )


def implied_vol(F: float, K: float, T: float, r: float, market_price: float,
                option_type: str = "call", tol: float = 1e-6, max_iter: int = 100) -> float:
    """Newton-Raphson implied volatility solver."""
    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        price = black76_price(F, K, T, r, sigma, option_type)
        diff = price - market_price
        if abs(diff) < tol:
            return sigma
        # Vega (not divided by 100 here)
        sqrt_T = np.sqrt(T)
        d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * sqrt_T)
        vega = F * np.exp(-r * T) * norm.pdf(d1) * sqrt_T
        if vega < 1e-12:
            break
        sigma -= diff / vega
        sigma = max(sigma, 0.001)
    return sigma


def compute_chain_greeks(chain: list[dict], F: float, T: float, r: float = 0.05) -> list[dict]:
    """Compute Greeks for an entire option chain."""
    results = []
    for opt in chain:
        K = opt["strike"]
        otype = opt.get("type", "call")
        sigma = opt.get("iv", 0.25)
        g = greeks(F, K, T, r, sigma, otype)
        results.append({**opt, "delta": g.delta, "gamma": g.gamma, "theta": g.theta, "vega": g.vega, "bs_price": g.price})
    return results
