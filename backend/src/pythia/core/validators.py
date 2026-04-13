"""
Input validation utilities with strict type checking.

Architectural why: PriceValidator and QuantityValidator enforce Decimal precision
at the boundary between user input and the trading engine, preventing float-drift
accumulation in multi-step P&L calculations. SymbolValidator accepts both standard
spot symbols (e.g. "BTCUSDT") and synthetic prediction-market symbols with the
"PM_" prefix (e.g. "PM_marketId_outcomeId"), which contain underscores.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from pythia.core.errors import ErrorCode, ValidationError

# Matches: standard alphanumeric (BTCUSDT) AND synthetic PM symbols (PM_abc_123)
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9_]+$")


class PriceValidator:
    """Strict price validation with Decimal precision."""

    MIN_PRICE = Decimal("0.01")
    MAX_PRICE = Decimal("1000000.00")

    @staticmethod
    def validate(price: float) -> Decimal:
        """Validate and convert price to Decimal."""
        try:
            price_decimal = Decimal(str(price))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid price format: {price}",
            ) from None

        if price_decimal.is_nan():
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid price format: {price}",
            )

        if price_decimal <= 0:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price must be positive: {price}",
            )

        if price_decimal < PriceValidator.MIN_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price below minimum: {price} < {PriceValidator.MIN_PRICE}",
            )

        if price_decimal > PriceValidator.MAX_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price exceeds maximum: {price} > {PriceValidator.MAX_PRICE}",
            )

        return price_decimal.quantize(Decimal("0.01"), ROUND_HALF_UP)


class QuantityValidator:
    """Validate trade quantities."""

    MIN_QUANTITY = Decimal("0.0001")
    MAX_QUANTITY = Decimal("1000000.0")

    @staticmethod
    def validate(quantity: float) -> Decimal:
        """Validate and convert quantity to Decimal."""
        try:
            qty_decimal = Decimal(str(quantity))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid quantity format: {quantity}",
            ) from None

        if qty_decimal.is_nan():
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid quantity format: {quantity}",
            )

        if qty_decimal <= 0:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity must be positive: {quantity}",
            )

        if qty_decimal < QuantityValidator.MIN_QUANTITY:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity below minimum: {quantity}",
            )

        if qty_decimal > QuantityValidator.MAX_QUANTITY:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity exceeds maximum: {quantity}",
            )

        return qty_decimal.quantize(Decimal("0.0001"), ROUND_HALF_UP)


class SymbolValidator:
    """
    Validate trading symbols.

    Accepts:
      - Standard spot symbols:  "BTCUSDT", "ETHUSDT"  (alphanumeric, ≤10 chars)
      - Synthetic PM symbols:   "PM_abc123_outcome1"   (alphanumeric + underscore, ≤64 chars)
    """

    MAX_LENGTH = 10
    MAX_LENGTH_SYNTHETIC = 64

    @staticmethod
    def validate(symbol: str) -> str:
        """Validate symbol format; permits PM_ synthetic prefixes."""
        if not symbol or not isinstance(symbol, str):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR, message="Symbol is required"
            )

        symbol = symbol.strip().upper()

        if not _SYMBOL_PATTERN.match(symbol):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Symbol contains invalid characters: {symbol}",
            )

        is_synthetic = symbol.startswith("PM_")
        max_len = SymbolValidator.MAX_LENGTH_SYNTHETIC if is_synthetic else SymbolValidator.MAX_LENGTH

        if len(symbol) > max_len:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Symbol too long ({len(symbol)} > {max_len}): {symbol}",
            )

        return symbol
