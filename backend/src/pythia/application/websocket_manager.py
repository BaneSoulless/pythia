"""
WebSocket Support for Real-Time Updates

Provides real-time portfolio and market data updates to connected clients.
P0-1 FIX: Added JWT authentication for WebSocket connections.
"""

import json
import logging
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

from pythia.core.websocket_auth import (
    authenticate_websocket,
    verify_portfolio_ownership,
)

# Deleted inline authenticate_websocket and verify_portfolio_ownership
# to use SOTA implementation from pythia.core.websocket_auth


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    """

    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.portfolio_subscribers: dict[int | str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            "WebSocket connected. Total connections: %d", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        self.active_connections.discard(websocket)

        # Remove from all portfolio subscriptions
        for subscribers in self.portfolio_subscribers.values():
            subscribers.discard(websocket)

        logger.info(
            "WebSocket disconnected. Total connections: %d", len(self.active_connections)
        )

    async def subscribe_portfolio(self, websocket: WebSocket, portfolio_id: int):
        """Subscribe to portfolio updates"""
        if portfolio_id not in self.portfolio_subscribers:
            self.portfolio_subscribers[portfolio_id] = set()

        self.portfolio_subscribers[portfolio_id].add(websocket)
        logger.info("Client subscribed to portfolio %s", portfolio_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:  # noqa: BLE001
                logger.error("Error broadcasting to client: %s", str(e))
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_portfolio_subscribers(self, portfolio_id: int, message: dict):
        """Send message to all subscribers of a specific portfolio"""
        if portfolio_id not in self.portfolio_subscribers:
            return

        disconnected = set()
        subscribers = self.portfolio_subscribers[portfolio_id]

        for connection in subscribers:
            try:
                await connection.send_json(message)
            except Exception as e:  # noqa: BLE001
                logger.error("Error sending to subscriber: %s", str(e))
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_portfolio_update(self, portfolio_id: int, data: dict):
        """Send portfolio update to subscribers"""
        message = {
            "type": "portfolio_update",
            "portfolio_id": portfolio_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        await self.send_to_portfolio_subscribers(portfolio_id, message)

    async def send_trade_execution(self, portfolio_id: int, trade_data: dict):
        """Notify subscribers of trade execution"""
        message = {
            "type": "trade_executed",
            "portfolio_id": portfolio_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": trade_data,
        }
        await self.send_to_portfolio_subscribers(portfolio_id, message)

    async def send_market_update(self, symbol: str, price_data: dict):
        """Broadcast market price update"""
        message = {
            "type": "market_update",
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "data": price_data,
        }
        await self.broadcast(message)

    async def send_ai_update(self, portfolio_id: int, ai_data: dict):
        """Send AI model update"""
        message = {
            "type": "ai_update",
            "portfolio_id": portfolio_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": ai_data,
        }
        await self.send_to_portfolio_subscribers(portfolio_id, message)


# Global connection manager
connection_manager = ConnectionManager()


async def portfolio_websocket_endpoint(websocket: WebSocket, portfolio_id: int):
    """
    WebSocket endpoint for portfolio updates.

    P0-1 FIX: Now requires JWT authentication via query parameter.

    Usage from frontend:
    ```javascript
    const token = localStorage.getItem('access_token');
    const ws = new WebSocket(`ws://localhost:8000/ws/portfolio/1?token=${token}`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Update:', data);
    };
    ```
    """
    # Accept connection first to be able to close with proper code
    await websocket.accept()

    # Authenticate user
    user = await authenticate_websocket(websocket)
    if not user:
        return  # Connection already closed by authenticate_websocket

    # Verify portfolio ownership
    if not await verify_portfolio_ownership(user, portfolio_id):
        logger.warning(
            "User %s denied access to portfolio %s", user.username, portfolio_id
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Register connection
    connection_manager.active_connections.add(websocket)
    await connection_manager.subscribe_portfolio(websocket, portfolio_id)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client commands
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:  # noqa: BLE001
        logger.error("WebSocket error: %s", str(e))

        connection_manager.disconnect(websocket)


async def market_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for market data updates
    """
    await websocket.accept()
    user = await authenticate_websocket(websocket)
    if not user:
        return

    await connection_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "subscribe":
                symbols = message.get("symbols", [])
                # Handle symbol subscription
                await websocket.send_json({"type": "subscribed", "symbols": symbols})

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:  # noqa: BLE001
        logger.error("WebSocket error: %s", str(e))
        connection_manager.disconnect(websocket)


async def intelligence_feed_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint dedicated to live AI Trading Intelligence stream.
    Requires operator/admin JWT authentication.
    """
    await websocket.accept()
    user = await authenticate_websocket(websocket)
    if not user:
        return

    # Subscribe to general intelligence channels via ConnectionManager
    await connection_manager.connect(websocket)

    # Track intent subscription explicitly for isolated intelligence feeds
    if "intelligence_feed" not in connection_manager.portfolio_subscribers:
        connection_manager.portfolio_subscribers["intelligence_feed"] = set()
    connection_manager.portfolio_subscribers["intelligence_feed"].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:  # noqa: BLE001
        logger.error("Intelligence feed WS error: %s", str(e))
        connection_manager.disconnect(websocket)

