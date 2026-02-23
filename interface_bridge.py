from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import zmq
import zmq.asyncio
import asyncio
import json
import logging
import platform
import uvicorn
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
logger = logging.getLogger('Bridge')
from pythia.db.database import engine, Base
from pythia.core.auth import decode_token
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info('Database Schema: VERIFIED')
    except Exception as e:
        logger.error(f'Database Init Error: {e}')
    task = asyncio.create_task(zmq_bridge_loop())
    yield
    task.cancel()
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
try:
    from pythia.api import auth
    app.include_router(auth.router, prefix='/api/auth', tags=['authentication'])
except Exception as e:
    logger.error(f'Auth Router Import Failed: {e}')
ZMQ_PUB_PORT = 5555
ZMQ_SUB_ADDR = f'tcp://localhost:{ZMQ_PUB_PORT}'

class ConnectionManager:

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f'Client Connected. Total: {len(self.active_connections)}')

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f'Client Disconnected. Total: {len(self.active_connections)}')

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass
manager = ConnectionManager()

@app.get('/health')
async def health_check():
    return {'status': 'ok', 'timestamp': time.time()}

@app.get('/api/portfolio')
async def get_portfolio_status():
    """PnL Telemetry Endpoint - Returns portfolio status and P&L"""
    try:
        from architecture.execution_layer.connector import ExchangeConnector
        connector = ExchangeConnector({})
        status = connector.get_portfolio_status()
        return status
    except Exception as e:
        logger.error(f'Portfolio Status Error: {e}')
        return {'error': str(e)}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, token: str=None):
    if token:
        try:
            payload = decode_token(token)
            logger.info(f"WS Auth Success: {payload.get('sub')}")
        except Exception as e:
            logger.warning(f'WS Auth Failed: {e}')
            await websocket.close(code=4003)
            return
    else:
        logger.warning('WS Connection missing Token! (Insecure Mode)')
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f'WebSocket Error: {e}')
        manager.disconnect(websocket)

async def zmq_bridge_loop():
    """Relays ZMQ messages to WebSockets"""
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(ZMQ_SUB_ADDR)
    sock.subscribe('')
    logger.info(f'Bridge: Listening to ZMQ Bus (Port {ZMQ_PUB_PORT})...')
    while True:
        try:
            if await sock.poll(100):
                msg = await sock.recv_string()
                await manager.broadcast(msg)
            else:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f'ZMQ Relay Error: {e}')
            await asyncio.sleep(1)
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')