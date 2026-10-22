"""Formatters for currency, status badges, and business text."""

from decimal import Decimal
from app.config import settings


def format_currency(amount: float | Decimal | int | None, symbol: str | None = None) -> str:
    """Format numeric amount into currency string, e.g. $1,250.00"""
    sym = symbol if symbol is not None else settings.CURRENCY_SYMBOL
    if amount is None:
        return f"{sym}0.00"
    try:
        val = float(amount)
        return f"{sym}{val:,.2f}"
    except (ValueError, TypeError):
        return f"{sym}0.00"


def format_number(val: int | float | None) -> str:
    """Format integers or counts with thousands separator."""
    if val is None:
        return "0"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return "0"


def format_percent(val: float | None) -> str:
    """Format percentage with +/- prefix."""
    if val is None:
        return "0.0%"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"
