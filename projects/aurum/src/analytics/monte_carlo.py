"""
Monte Carlo price simulator: GBM + Merton jump diffusion.
Produces cone charts and probability distributions.
"""
import numpy as np
import pandas as pd


def gbm_paths(S0: float, mu: float, sigma: float, T: float, steps: int = 252,
              n_paths: int = 10000, seed: int = 42) -> np.ndarray:
    """Geometric Brownian Motion paths. Returns (n_paths, steps+1) array."""
    np.random.seed(seed)
    dt = T / steps
    Z = np.random.standard_normal((n_paths, steps))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_paths = np.cumsum(log_returns, axis=1)
    log_paths = np.hstack([np.zeros((n_paths, 1)), log_paths])
    return S0 * np.exp(log_paths)


def jump_diffusion_paths(S0: float, mu: float, sigma: float, lam: float,
                         jump_mean: float, jump_std: float, T: float,
                         steps: int = 252, n_paths: int = 10000, seed: int = 42) -> np.ndarray:
    """Merton jump-diffusion model. lam=jump intensity, jump_mean/std=log-normal jump params."""
    np.random.seed(seed)
    dt = T / steps
    paths = np.zeros((n_paths, steps + 1))
    paths[:, 0] = S0

    for t in range(1, steps + 1):
        Z = np.random.standard_normal(n_paths)
        N_jumps = np.random.poisson(lam * dt, n_paths)
        J = np.zeros(n_paths)
        for i in range(n_paths):
            if N_jumps[i] > 0:
                J[i] = np.sum(np.random.normal(jump_mean, jump_std, N_jumps[i]))
        drift = (mu - 0.5 * sigma**2 - lam * (np.exp(jump_mean + 0.5 * jump_std**2) - 1)) * dt
        diffusion = sigma * np.sqrt(dt) * Z
        paths[:, t] = paths[:, t - 1] * np.exp(drift + diffusion + J)

    return paths


def cone_chart_data(paths: np.ndarray, percentiles: list[int] = None) -> pd.DataFrame:
    """Extract percentile bands from simulated paths for cone chart."""
    if percentiles is None:
        percentiles = [5, 10, 25, 50, 75, 90, 95]
    steps = paths.shape[1]
    records = []
    for t in range(steps):
        row = {"step": t}
        for p in percentiles:
            row[f"p{p}"] = float(np.percentile(paths[:, t], p))
        row["mean"] = float(np.mean(paths[:, t]))
        records.append(row)
    return pd.DataFrame(records)


def terminal_distribution(paths: np.ndarray) -> dict:
    """Summary statistics of terminal price distribution."""
    terminal = paths[:, -1]
    S0 = paths[0, 0]
    return {
        "mean": round(float(np.mean(terminal)), 2),
        "median": round(float(np.median(terminal)), 2),
        "std": round(float(np.std(terminal)), 2),
        "p5": round(float(np.percentile(terminal, 5)), 2),
        "p25": round(float(np.percentile(terminal, 25)), 2),
        "p75": round(float(np.percentile(terminal, 75)), 2),
        "p95": round(float(np.percentile(terminal, 95)), 2),
        "prob_up": round(float(np.mean(terminal > S0) * 100), 1),
        "prob_down": round(float(np.mean(terminal < S0) * 100), 1),
        "max_return_pct": round(float((np.max(terminal) / S0 - 1) * 100), 1),
        "max_drawdown_pct": round(float((np.min(terminal) / S0 - 1) * 100), 1),
    }


def simulate_gold(S0: float, sigma: float = 0.18, T: float = 1.0,
                   mu: float = 0.05, model: str = "gbm", n_paths: int = 10000) -> dict:
    """Convenience wrapper for gold simulation."""
    if model == "jump":
        paths = jump_diffusion_paths(S0, mu, sigma, lam=2.0, jump_mean=-0.01, jump_std=0.03, T=T, n_paths=n_paths)
    else:
        paths = gbm_paths(S0, mu, sigma, T, n_paths=n_paths)
    return {
        "paths": paths,
        "cone": cone_chart_data(paths),
        "terminal": terminal_distribution(paths),
    }
