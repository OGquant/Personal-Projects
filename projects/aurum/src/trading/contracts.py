"""MCX contract specifications for Gold and Silver."""
from dataclasses import dataclass

@dataclass
class ContractSpec:
    name: str
    symbol: str
    lot_size: float
    lot_unit: str
    tick_size: float
    margin_pct: float  # approximate initial margin %
    trading_hours: str
    expiry_cycle: str
    quote_unit: str

MCX_CONTRACTS = {
    "Gold": ContractSpec("Gold", "GOLD", 100, "grams", 1.0, 6.0, "09:00-23:30", "Bi-monthly (Feb,Apr,Jun,Aug,Oct,Dec)", "₹/10g"),
    "Gold Mini": ContractSpec("Gold Mini", "GOLDM", 10, "grams", 1.0, 6.0, "09:00-23:30", "Monthly", "₹/10g"),
    "Gold Guinea": ContractSpec("Gold Guinea", "GOLDGUINEA", 8, "grams", 1.0, 6.0, "09:00-23:30", "Monthly", "₹/8g"),
    "Gold Petal": ContractSpec("Gold Petal", "GOLDPETAL", 1, "gram", 1.0, 6.0, "09:00-23:30", "Monthly", "₹/1g"),
    "Silver": ContractSpec("Silver", "SILVER", 30, "kg", 1.0, 7.0, "09:00-23:30", "Bi-monthly", "₹/kg"),
    "Silver Mini": ContractSpec("Silver Mini", "SILVERM", 5, "kg", 1.0, 7.0, "09:00-23:30", "Monthly", "₹/kg"),
    "Silver Micro": ContractSpec("Silver Micro", "SILVERMIC", 1, "kg", 1.0, 7.0, "09:00-23:30", "Monthly", "₹/kg"),
}

# CME COMEX specs for reference
CME_CONTRACTS = {
    "Gold (GC)": ContractSpec("Gold Futures", "GC", 100, "troy oz", 0.10, 8.0, "Sun-Fri 17:00-16:00 CT", "Monthly (Feb,Apr,Jun,Aug,Oct,Dec)", "$/troy oz"),
    "Silver (SI)": ContractSpec("Silver Futures", "SI", 5000, "troy oz", 0.005, 9.0, "Sun-Fri 17:00-16:00 CT", "Monthly (Mar,May,Jul,Sep,Dec)", "$/troy oz"),
    "Micro Gold (MGC)": ContractSpec("Micro Gold", "MGC", 10, "troy oz", 0.10, 8.0, "Sun-Fri 17:00-16:00 CT", "Monthly", "$/troy oz"),
    "Micro Silver (SIL)": ContractSpec("Micro Silver", "SIL", 1000, "troy oz", 0.005, 9.0, "Sun-Fri 17:00-16:00 CT", "Monthly", "$/troy oz"),
}

def get_contract(name: str) -> ContractSpec | None:
    return MCX_CONTRACTS.get(name) or CME_CONTRACTS.get(name)

def get_margin(name: str, price: float) -> float:
    """Approximate initial margin for a contract."""
    spec = get_contract(name)
    if not spec:
        return 0.0
    notional = price * spec.lot_size
    return round(notional * spec.margin_pct / 100, 2)

def list_all() -> dict:
    return {**MCX_CONTRACTS, **CME_CONTRACTS}
