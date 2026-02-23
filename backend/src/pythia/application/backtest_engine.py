"""
Backtesting Engine

Allows testing trading strategies against historical data
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
logger = logging.getLogger(__name__)

@dataclass
class BacktestTrade:
    """Single backtested trade"""
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.quantity * self.price + self.commission

@dataclass
class BacktestResults:
    """Results from a backtest run"""
    initial_balance: float
    final_balance: float
    total_return: float
    total_return_pct: float
    num_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[BacktestTrade]
    equity_curve: List[Tuple[datetime, float]]

    def to_dict(self) -> Dict:
        return {'initial_balance': self.initial_balance, 'final_balance': self.final_balance, 'total_return': self.total_return, 'total_return_pct': self.total_return_pct, 'num_trades': self.num_trades, 'winning_trades': self.winning_trades, 'losing_trades': self.losing_trades, 'win_rate': self.win_rate, 'max_drawdown': self.max_drawdown, 'sharpe_ratio': self.sharpe_ratio}

class BacktestEngine:
    """
    Backtesting engine for trading strategies
    """

    def __init__(self, initial_balance: float=10000.0, commission_rate: float=0.001, min_balance: float=10.0):
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.min_balance = min_balance
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def reset(self):
        """Reset backtest state"""
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def execute_buy(self, timestamp: datetime, symbol: str, quantity: float, price: float) -> bool:
        """Execute buy order in backtest"""
        commission = price * quantity * self.commission_rate
        total_cost = price * quantity + commission
        if self.balance - total_cost < self.min_balance:
            return False
        self.balance -= total_cost
        self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        trade = BacktestTrade(timestamp=timestamp, symbol=symbol, side='buy', quantity=quantity, price=price, commission=commission)
        self.trades.append(trade)
        return True

    def execute_sell(self, timestamp: datetime, symbol: str, quantity: float, price: float) -> bool:
        """Execute sell order in backtest"""
        if symbol not in self.positions or self.positions[symbol] < quantity:
            return False
        commission = price * quantity * self.commission_rate
        proceeds = price * quantity - commission
        self.balance += proceeds
        self.positions[symbol] -= quantity
        if self.positions[symbol] == 0:
            del self.positions[symbol]
        trade = BacktestTrade(timestamp=timestamp, symbol=symbol, side='sell', quantity=quantity, price=price, commission=commission)
        self.trades.append(trade)
        return True

    def record_equity(self, timestamp: datetime, current_prices: Dict[str, float]):
        """Record current portfolio value"""
        positions_value = sum((self.positions.get(symbol, 0) * current_prices.get(symbol, 0) for symbol in self.positions))
        total_value = self.balance + positions_value
        self.equity_curve.append((timestamp, total_value))

    def calculate_metrics(self) -> BacktestResults:
        """Calculate backtest performance metrics"""
        final_balance = self.equity_curve[-1][1] if self.equity_curve else self.initial_balance
        total_return = final_balance - self.initial_balance
        total_return_pct = total_return / self.initial_balance * 100
        winning_trades = 0
        losing_trades = 0
        buy_trades = {}
        for trade in self.trades:
            if trade.side == 'buy':
                if trade.symbol not in buy_trades:
                    buy_trades[trade.symbol] = []
                buy_trades[trade.symbol].append(trade)
            elif trade.side == 'sell':
                if trade.symbol in buy_trades and buy_trades[trade.symbol]:
                    buy_trade = buy_trades[trade.symbol].pop(0)
                    pnl = (trade.price - buy_trade.price) * trade.quantity - trade.commission - buy_trade.commission
                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
        total_closed_trades = winning_trades + losing_trades
        win_rate = winning_trades / total_closed_trades * 100 if total_closed_trades > 0 else 0
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio()
        return BacktestResults(initial_balance=self.initial_balance, final_balance=final_balance, total_return=total_return, total_return_pct=total_return_pct, num_trades=len(self.trades), winning_trades=winning_trades, losing_trades=losing_trades, win_rate=win_rate, max_drawdown=max_drawdown, sharpe_ratio=sharpe_ratio, trades=self.trades, equity_curve=self.equity_curve)

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve"""
        if not self.equity_curve:
            return 0.0
        values = [val for _, val in self.equity_curve]
        peak = values[0]
        max_dd = 0
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100

    def _calculate_sharpe_ratio(self, risk_free_rate: float=0.02) -> float:
        """Calculate Sharpe ratio from returns"""
        if len(self.equity_curve) < 2:
            return 0.0
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_value = self.equity_curve[i - 1][1]
            curr_value = self.equity_curve[i][1]
            returns.append((curr_value - prev_value) / prev_value)
        if not returns:
            return 0.0
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        if std_return == 0:
            return 0.0
        sharpe = (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)
        return sharpe

def run_strategy_backtest(strategy_func, historical_data: pd.DataFrame, initial_balance: float=10000.0, **strategy_params) -> BacktestResults:
    """
    Run a backtest with a given strategy function
    
    Args:
        strategy_func: Function that takes (engine, data, **params) and executes trades
        historical_data: DataFrame with columns: timestamp, symbol, open, high, low, close, volume
        initial_balance: Starting balance
        **strategy_params: Additional parameters to pass to strategy
    
    Returns:
        BacktestResults object
    """
    engine = BacktestEngine(initial_balance=initial_balance)
    strategy_func(engine, historical_data, **strategy_params)
    return engine.calculate_metrics()