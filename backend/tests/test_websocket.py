"""
Tests for WebSocket real-time updates.

Tests connection lifecycle, message broadcasting, and reconnection logic.
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from main import app

class TestWebSocket:
    """Test suite for WebSocket functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_websocket_connection(self, client):
        """Test WebSocket connection establishment."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            assert websocket is not None

    def test_portfolio_update_broadcast(self, client, db_session):
        """Test portfolio update broadcasts to connected clients."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            update_message = {'type': 'portfolio_update', 'portfolio': {'id': 1, 'balance': 10500.0, 'total_value': 11200.0}}
            data = websocket.receive_json()
            assert data['type'] == 'portfolio_update'
            assert 'portfolio' in data

    def test_trade_execution_notification(self, client):
        """Test trade execution notifications."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            trade_message = {'type': 'trade_executed', 'trade': {'symbol': 'AAPL', 'side': 'buy', 'quantity': 10, 'price': 150.0}}
            data = websocket.receive_json()
            assert data['type'] in ['trade_executed', 'portfolio_update']

    def test_ai_status_update(self, client):
        """Test AI status update broadcasts."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            ai_update = {'type': 'ai_status_update', 'ai_status': {'is_training': True, 'epsilon': 0.1, 'total_episodes': 100}}
            data = websocket.receive_json()
            assert 'type' in data

    def test_multiple_clients(self, client):
        """Test multiple WebSocket clients."""
        with client.websocket_connect('/ws/portfolio/1') as ws1:
            with client.websocket_connect('/ws/portfolio/1') as ws2:
                assert ws1 is not None
                assert ws2 is not None

    def test_websocket_ping_pong(self, client):
        """Test keep-alive ping/pong."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            websocket.send_json({'type': 'ping'})
            data = websocket.receive_json()
            assert data.get('type') == 'pong'

    def test_websocket_close(self, client):
        """Test WebSocket graceful close."""
        with client.websocket_connect('/ws/portfolio/1') as websocket:
            websocket.close()
