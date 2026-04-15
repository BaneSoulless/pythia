"""Tests for PaperTradingBroker and TradingModeRouter."""

import os
from unittest.mock import MagicMock, patch

import pytest

from pythia.core.ports import TradingPort


class TestTradingModeRouter:
    def test_default_is_paper(self):
        """TRADING_MODE unset → always paper."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TRADING_MODE", None)
            from pythia.infrastructure.trading_mode_router import get_trading_mode

            assert get_trading_mode() == "paper"

    def test_explicit_paper(self):
        with patch.dict(os.environ, {"TRADING_MODE": "paper"}):
            from pythia.infrastructure.trading_mode_router import is_paper_mode

            assert is_paper_mode() is True

    def test_explicit_live(self):
        with patch.dict(os.environ, {"TRADING_MODE": "live"}):
            from pythia.infrastructure.trading_mode_router import is_live_mode

            assert is_live_mode() is True

    def test_invalid_mode_falls_back_to_paper(self):
        with patch.dict(os.environ, {"TRADING_MODE": "YOLO"}):
            from pythia.infrastructure.trading_mode_router import get_trading_mode

            assert get_trading_mode() == "paper"

    def test_get_broker_factory(self):
        """Test get_broker correctly returns PaperTradingBroker or AlpacaAdapter."""
        with patch.dict(os.environ, {"TRADING_MODE": "paper"}):
            from pythia.infrastructure.trading_mode_router import get_broker
            from pythia.infrastructure.brokers.paper_trading_broker import PaperTradingBroker
            
            db = MagicMock()
            db.execute.return_value.fetchone.return_value = ("session-123",)
            
            
            with patch("pythia.infrastructure.brokers.paper_trading_broker.settings") as mock_settings:
                mock_settings.PAPER_INITIAL_CAPITAL = 10000.0
                mock_settings.ALPACA_PAPER_API_KEY = "test"
                mock_settings.ALPACA_PAPER_SECRET_KEY = "test"
                broker = get_broker(db_session=db)
                assert isinstance(broker, PaperTradingBroker)
                assert isinstance(broker, TradingPort)

        with patch.dict(os.environ, {"TRADING_MODE": "live"}):
            from pythia.infrastructure.trading_mode_router import get_broker
            from pythia.adapters.alpaca_adapter import AlpacaAdapter
            
            with patch("pythia.core.config.settings") as mock_settings:
                mock_settings.ALPACA_API_KEY = "test_key"
                mock_settings.ALPACA_SECRET_KEY = "test_secret"
                mock_settings.EXCHANGE_API_KEY = "test_key"
                mock_settings.EXCHANGE_SECRET_KEY = "test_secret"
                
                broker = get_broker(db_session=db)
                assert isinstance(broker, AlpacaAdapter)
                assert isinstance(broker, TradingPort)


class TestPaperTradingBroker:
    """Tests PaperTradingBroker with mocked Alpaca client and DB."""

    def _make_broker(self):
        with patch("pythia.infrastructure.brokers.paper_trading_broker.TradingClient"), patch(
            "pythia.infrastructure.brokers.paper_trading_broker.settings"
        ) as mock_settings:
            mock_settings.ALPACA_PAPER_API_KEY = "test_key"
            mock_settings.ALPACA_PAPER_SECRET_KEY = "test_secret"
            mock_settings.PAPER_INITIAL_CAPITAL = 10000.0

            db = MagicMock()
            db.execute.return_value.fetchone.return_value = None
            from pythia.infrastructure.brokers.paper_trading_broker import (
                PaperTradingBroker,
            )

            return PaperTradingBroker(db_session=db)

    def test_initialization(self):
        broker = self._make_broker()
        assert broker.initial_capital == 10000

    @pytest.mark.asyncio
    async def test_submit_order_records_trade(self):
        broker = self._make_broker()
        mock_order = MagicMock()
        mock_order.id = "test-order-123"
        mock_order.filled_avg_price = "50000.0"
        mock_order.limit_price = None
        broker._client.submit_order = MagicMock(return_value=mock_order)
        
        result = await broker.place_order(
            symbol="BTCUSD",
            quantity=0.001,
            side="buy",
            price=None,
            signal_scores={"rl": 0.7},
            evolved_node_id="47",
        )
        assert result["paper"] is True
        assert result["fill_price"] == 50000.0
        assert result["id"] == "test-order-123"

    @pytest.mark.asyncio
    async def test_close_position_calculates_pnl(self):
        broker = self._make_broker()
        # First query is for paper_trades, second is for paper_sessions in get_session_summary
        broker.db.execute.return_value.fetchone.side_effect = [
            (1, "50000.0", "0.001", "BUY"),
            (1, 1, 1.0, 10001.0, 10000.0, 0.0, 0.0, False),
            (1,),
            (1, 1, 1.0, 10001.0, 10000.0, 0.0, 0.0, False),
        ]
        result = await broker.close_position(symbol="BTCUSD", exit_price=51000.0)
        assert result["is_win"] is True
        assert result["pnl"] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_close_position_no_open_returns_error(self):
        broker = self._make_broker()
        broker.db.execute.return_value.fetchone.return_value = None
        result = await broker.close_position(symbol="BTCUSD", exit_price=51000.0)
        assert "error" in result

    def test_get_session_summary_empty(self):
        broker = self._make_broker()
        broker.db.execute.return_value.fetchone.return_value = None
        summary = broker.get_session_summary()
        assert summary == {}
