"""Seeded 6-bit currency index table (indices 1–31). Index 0 = session default sentinel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bitledger.errors import ProfileError

# Wire order is normative — do not reorder after deployment (TASK-2.02).
_SEED: Final[tuple[tuple[int, str, str, str], ...]] = (
    (0, "", "SESSION_DEFAULT", "Session default (not a wire currency)"),
    (1, "USD", "US Dollar", "$"),
    (2, "EUR", "Euro", "€"),
    (3, "JPY", "Japanese Yen", "¥"),
    (4, "GBP", "British Pound", "£"),
    (5, "AUD", "Australian Dollar", "A$"),
    (6, "CAD", "Canadian Dollar", "C$"),
    (7, "CHF", "Swiss Franc", "Fr"),
    (8, "CNY", "Chinese Yuan", "¥"),
    (9, "SEK", "Swedish Krona", "kr"),
    (10, "NZD", "New Zealand Dollar", "NZ$"),
    (11, "MXN", "Mexican Peso", "$"),
    (12, "SGD", "Singapore Dollar", "S$"),
    (13, "HKD", "Hong Kong Dollar", "HK$"),
    (14, "NOK", "Norwegian Krone", "kr"),
    (15, "KRW", "South Korean Won", "₩"),
    (16, "TRY", "Turkish Lira", "₺"),
    (17, "RUB", "Russian Ruble", "₽"),
    (18, "INR", "Indian Rupee", "₹"),
    (19, "BRL", "Brazilian Real", "R$"),
    (20, "ZAR", "South African Rand", "R"),
    (21, "DKK", "Danish Krone", "kr"),
    (22, "PLN", "Polish Złoty", "zł"),
    (23, "TWD", "New Taiwan Dollar", "NT$"),
    (24, "THB", "Thai Baht", "฿"),
    (25, "MYR", "Malaysian Ringgit", "RM"),
    (26, "IDR", "Indonesian Rupiah", "Rp"),
    (27, "HUF", "Hungarian Forint", "Ft"),
    (28, "CZK", "Czech Koruna", "Kč"),
    (29, "ILS", "Israeli Shekel", "₪"),
    (30, "CLP", "Chilean Peso", "$"),
    (31, "PHP", "Philippine Peso", "₱"),
)


@dataclass(frozen=True)
class CurrencyRow:
    index: int
    code: str
    name: str
    symbol: str


def _row(n: int) -> CurrencyRow:
    idx, code, name, sym = _SEED[n]
    return CurrencyRow(index=idx, code=code, name=name, symbol=sym)


def lookup_by_index(n: int) -> dict[str, str | int]:
    """Return currency dict; index 0 is session-default sentinel."""
    if n < 0 or n > 31:
        raise ProfileError(f"currency index out of range: {n}")
    r = _row(n)
    return {"index": r.index, "code": r.code, "name": r.name, "symbol": r.symbol}


def lookup_by_code(code: str) -> int:
    """Case-insensitive code → index 1–31; ProfileError if unknown (reserved 32–63 pass-through elsewhere)."""
    c = code.strip().upper()
    for i in range(1, 32):
        if _SEED[i][1].upper() == c:
            return i
    raise ProfileError(f"unknown currency code: {code!r}")
