"""
Input validation utilities with strict type checking
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
from pythia.core.errors import ValidationError, ErrorCode


class PriceValidator:
    """Strict price validation with Decimal precision"""
    MIN_PRICE = Decimal("0.01")
    MAX_PRICE = Decimal("1000000.00")
    
    @staticmethod
    def validate(price: float) -> Decimal:
        """Validate and convert price to Decimal"""
        try:
            price_decimal = Decimal(str(price))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid price format: {price}"
            )
        
        if price_decimal <= 0:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price must be positive: {price}"
            )
        
        if price_decimal < PriceValidator.MIN_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price below minimum: {price} < {PriceValidator.MIN_PRICE}"
            )
        
        if price_decimal > PriceValidator.MAX_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price exceeds maximum: {price} > {PriceValidator.MAX_PRICE}"
            )
        
        return price_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP)


class QuantityValidator:
    """Validate trade quantities"""
    MIN_QUANTITY = Decimal("0.0001")
    MAX_QUANTITY = Decimal("1000000.0")
    
    @staticmethod
    def validate(quantity: float) -> Decimal:
        """Validate and convert quantity to Decimal"""
        try:
            qty_decimal = Decimal(str(quantity))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid quantity format: {quantity}"
            )
        
        if qty_decimal <= 0:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity must be positive: {quantity}"
            )
        
        if qty_decimal < QuantityValidator.MIN_QUANTITY:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity below minimum: {quantity}"
            )
        
        if qty_decimal > QuantityValidator.MAX_QUANTITY:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Quantity exceeds maximum: {quantity}"
            )
        
        return qty_decimal.quantize(Decimal('0.0001'), ROUND_HALF_UP)


class SymbolValidator:
    """Validate trading symbols"""
    MAX_LENGTH = 10
    
    @staticmethod
    def validate(symbol: str) -> str:
        """Validate symbol format"""
        if not symbol or not isinstance(symbol, str):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Symbol is required"
            )
        
        symbol = symbol.strip().upper()
        
        if not symbol.isalnum():
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Symbol must be alphanumeric: {symbol}"
            )
        
        if len(symbol) > SymbolValidator.MAX_LENGTH:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Symbol too long: {symbol}"
            )
        
        return symbol
