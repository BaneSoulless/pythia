"""
Paper Execution Service (Fallback)
SOTA 2026

Simulates execution against real-time data when API keys are missing.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any
from app.infrastructure.messaging.system_bus import SystemBus
from app.core.neuro_symbolic import neuro_validator

logger = logging.getLogger(__name__)

class PaperTradingConnector:
    """
    Virtual Exchange Simulator.
    Maintains local state for Portfolio/Orders.
    """
    def __init__(self, initial_balance=10000.0):
        self.balance = initial_balance
        self.positions: Dict[str, float] = {} # Symbol -> Qty
        self.open_orders = []
        self.fee_rate = 0.001 # 0.1%
        self.slippage = 0.001 # 0.1%

    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: float):
        """Simulate order execution."""
        # Simulate slippage
        exec_price = price * (1 + self.slippage) if side == 'buy' else price * (1 - self.slippage)
        cost = exec_price * amount
        fee = cost * self.fee_rate
        total_cost = cost + fee

        if side == 'buy':
            if total_cost > self.balance:
                raise Exception("Insufficient Paper Funds")
            self.balance -= total_cost
            self.positions[symbol] = self.positions.get(symbol, 0) + amount
            
        elif side == 'sell':
            current_pos = self.positions.get(symbol, 0)
            if amount > current_pos:
                raise Exception("Insufficient Paper Position")
            self.positions[symbol] -= amount
            self.balance += (exec_price * amount) - fee

        return {
            'id': f"paper-{int(time.time()*1000)}",
            'status': 'closed',
            'symbol': symbol,
            'amount': amount,
            'price': exec_price,
            'fee': fee,
            'side': side
        }

    async def fetch_balance(self):
        return {'total': {'USDT': self.balance}, 'free': {'USDT': self.balance}}


class ExecutionService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bus = SystemBus(config)
        self.connector = PaperTradingConnector() # Default to Paper for Fallback

    async def execute_trade(self, order: Dict[str, Any]):
        """Execute order on VIRTUAL exchange."""
        symbol = order.get('symbol')
        side = order.get('action')
        amount = order.get('quantity')
        price = order.get('price')
        
        # Neuro-Symbolic Validation
        if not neuro_validator.validate(order, confidence=0.9):
            logger.warning(f"Paper Execution BLOCKED by NeuroSymbolic Validator: {order}")
            return

        logger.info(f"EXECUTING PAPER TRADE: {side.upper()} {amount} {symbol} @ {price}")
        
        try:
            response = await self.connector.create_order(
                symbol=symbol, type='limit', side=side, amount=amount, price=price
            )
            logger.info(f"PAPER ORDER FILLED: {response}")
            
            # Log new balance
            bal = await self.connector.fetch_balance()
            logger.info(f"New Paper Balance: {bal['total']['USDT']:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Paper Execution Failed: {e}")

    async def start(self):
        self.bus.connect_execution_subscriber()
        logger.info("Execution Service: PAPER TRADING ONLINE (Virtual Portfolio)")
        
        while True:
            try:
                msg = await self.bus.receive_execution_command()
                if msg:
                   await self.execute_trade(msg)
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Execution Loop Error: {e}")
                await asyncio.sleep(1)

def run_service(config: Dict[str, Any]):
    service = ExecutionService(config)
    asyncio.run(service.start())
