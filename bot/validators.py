"""Input validation for order parameters.

Centralises all validation logic so that both the CLI layer and the
order-placement layer can rely on sanitised, well-typed data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,20}$")


class ValidationError(Exception):
    """Raised when user input fails validation."""


@dataclass(frozen=True)
class OrderParams:
    """Validated, immutable order parameters ready for submission."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None


def validate_symbol(symbol: str) -> str:
    """Return the uppercased symbol or raise on invalid format."""
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Must be 2-20 uppercase letters (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return the uppercased side or raise if not BUY/SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {VALID_SIDES}.")
    return side


def validate_order_type(order_type: str) -> str:
    """Return the uppercased order type or raise if unsupported."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {VALID_ORDER_TYPES}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Return a positive Decimal quantity or raise."""
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be positive, got {qty}.")
    return qty


def validate_price(price: str | float | None, order_type: str) -> Optional[Decimal]:
    """Return a positive Decimal price (required for LIMIT) or None."""
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            p = Decimal(str(price))
        except (InvalidOperation, ValueError):
            raise ValidationError(f"Invalid price '{price}'. Must be a positive number.")
        if p <= 0:
            raise ValidationError(f"Price must be positive, got {p}.")
        return p
    return None


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
) -> OrderParams:
    """Run full validation and return an ``OrderParams`` instance.

    Raises
    ------
    ValidationError
        If any parameter is invalid.
    """
    v_symbol = validate_symbol(symbol)
    v_side = validate_side(side)
    v_type = validate_order_type(order_type)
    v_qty = validate_quantity(quantity)
    v_price = validate_price(price, v_type)
    return OrderParams(
        symbol=v_symbol,
        side=v_side,
        order_type=v_type,
        quantity=v_qty,
        price=v_price,
    )
