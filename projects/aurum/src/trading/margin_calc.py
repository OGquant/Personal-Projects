"""Margin calculator (SPAN approximation) for MCX."""
from src.trading.contracts import MCX_CONTRACTS, get_contract

def calculate_margin(contract_name: str, price: float, num_lots: int = 1) -> dict:
    spec = get_contract(contract_name)
    if not spec:
        return {"error": f"Unknown contract: {contract_name}"}
    notional = price * spec.lot_size * num_lots
    initial = notional * spec.margin_pct / 100
    maintenance = initial * 0.75  # ~75% of initial
    return {
        "contract": spec.name, "lots": num_lots, "lot_size": spec.lot_size,
        "price": price, "notional": round(notional, 0),
        "initial_margin": round(initial, 0), "maintenance_margin": round(maintenance, 0),
        "margin_pct": spec.margin_pct,
    }

def margin_table(price: float) -> list[dict]:
    """Margin for all MCX contracts at a given price."""
    results = []
    for name in MCX_CONTRACTS:
        results.append(calculate_margin(name, price))
    return results
