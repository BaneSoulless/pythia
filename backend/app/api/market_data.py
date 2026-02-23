"""
Market Data API Endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from app.services.market_data import market_data_service
from app.core.errors import TradingBotError, MarketDataError
import structlog

logger = structlog.get_logger()

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current price for a symbol"""
    try:
        price = market_data_service.get_current_price(symbol)
        if price is None:
            raise MarketDataError(f"Could not fetch price for {symbol}")
        return {"symbol": symbol, "price": price}
    except MarketDataError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_quote_error", error=str(e), symbol=symbol)
        raise TradingBotError(f"Failed to fetch quote: {str(e)}")

@router.get("/history/{symbol}")
async def get_history(
    symbol: str, 
    days: int = Query(30, ge=1, le=365)
):
    """Get historical data"""
    try:
        data = market_data_service.get_historical_data(symbol, days)
        if not data:
            raise MarketDataError(f"No historical data found for {symbol}")
        return data
    except MarketDataError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_history_error", error=str(e), symbol=symbol)
        raise TradingBotError(f"Failed to fetch history: {str(e)}")
        
        data = market_data_service.get_historical_data(symbol.upper(), days)
        return {
            "symbol": symbol.upper(),
            "days": days,
            "data": data
        }
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Get technical indicators"""
    try:
        # Get enough data for indicators
        data = market_data_service.get_historical_data(symbol, 60)
        if not data:
            raise MarketDataError(f"Insufficient data for indicators: {symbol}")
        
        prices = [d['close'] for d in data]
        
        sma_20 = market_data_service.calculate_sma(prices, 20)
        rsi_14 = market_data_service.calculate_rsi(prices, 14)
        
        return {
            "symbol": symbol,
            "sma_20": sma_20,
            "rsi_14": rsi_14
        }
    except MarketDataError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_indicators_error", error=str(e), symbol=symbol)
        raise TradingBotError(f"Failed to calculate indicators: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
