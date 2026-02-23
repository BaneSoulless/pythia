import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket
from pythia.application.websocket_manager import ConnectionManager

@pytest.fixture
def connection_manager():
    return ConnectionManager()

@pytest.fixture
def mock_websocket():
    ws = AsyncMock(spec=WebSocket)
    return ws

@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager, mock_websocket):
    await connection_manager.connect(mock_websocket)
    assert mock_websocket in connection_manager.active_connections
    mock_websocket.accept.assert_called_once()

@pytest.mark.asyncio
async def test_connection_manager_disconnect(connection_manager, mock_websocket):
    await connection_manager.connect(mock_websocket)
    connection_manager.disconnect(mock_websocket)
    assert mock_websocket not in connection_manager.active_connections

@pytest.mark.asyncio
async def test_subscribe_portfolio(connection_manager, mock_websocket):
    portfolio_id = 1
    await connection_manager.subscribe_portfolio(mock_websocket, portfolio_id)
    assert mock_websocket in connection_manager.portfolio_subscribers[portfolio_id]

@pytest.mark.asyncio
async def test_broadcast(connection_manager, mock_websocket):
    await connection_manager.connect(mock_websocket)
    message = {'type': 'test', 'data': 'hello'}
    await connection_manager.broadcast(message)
    mock_websocket.send_json.assert_called_with(message)
