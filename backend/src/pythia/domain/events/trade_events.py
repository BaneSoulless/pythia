"""
Event Sourcing aggregates per il trading.
"""
from eventsourcing.domain import Aggregate, event

class TradeAggregate(Aggregate):
    """Aggregato per gestire il ciclo di vita di un trade con Event Sourcing."""
    
    @event('Opened')
    def open_trade(self, pair: str, action: str, confidence: float, stake_amount: float):
        """Apre il trade."""
        self.pair = pair
        self.action = action
        self.confidence = confidence
        self.stake_amount = stake_amount
        self.status = "OPEN"
        self.pnl = 0.0
        self.reason = ""
        
    @event('Closed')
    def close_trade(self, pnl: float, reason: str):
        """Chiude il trade registrando il Profit & Loss."""
        self.pnl = pnl
        self.reason = reason
        self.status = "CLOSED"
        
    @event('Modified')
    def update_stop_loss(self, new_sl: float):
        """Aggiorna lo stop loss dinamico."""
        self.stop_loss = new_sl
