"""
Redis Pub/Sub Service
SOTA 2026 Scalability

Enables fan-out of real-time messages across multiple backend instances.
"""

import redis.asyncio as redis
import json
import logging
import asyncio
from typing import Callable, Any
from pythia.core.config import settings

logger = logging.getLogger(__name__)

class RedisPubSubManager:
    """
    Manages Redis Pub/Sub channels for distributed broadcasting.
    """
    def __init__(self):
        self.redis_url = f"redis://{getattr(settings, 'REDIS_HOST', 'localhost')}:{getattr(settings, 'REDIS_PORT', 6379)}"
        self.pub_conn = None
        self.sub_conn = None
        self.enabled = False

    async def connect(self):
        try:
            self.pub_conn = redis.from_url(self.redis_url, decode_responses=True)
            self.sub_conn = redis.from_url(self.redis_url, decode_responses=True)
            await self.pub_conn.ping()
            self.enabled = True
            logger.info("Redis Pub/Sub connected.")
        except Exception as e:
            logger.warning(f"Redis Pub/Sub connection failed: {e}. Distributed fan-out disabled.")
            self.enabled = False

    async def publish(self, channel: str, message: Any):
        if not self.enabled or not self.pub_conn:
            return
        try:
            payload = json.dumps(message)
            await self.pub_conn.publish(channel, payload)
        except Exception as e:
            logger.error(f"Redis publish error: {e}")

    async def subscribe(self, channel: str, callback: Callable[[str], Any]):
        if not self.enabled or not self.sub_conn:
            return
        
        pubsub = self.sub_conn.pubsub()
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to Redis channel: {channel}")

        async def listener():
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        await callback(message['data'])
            except Exception as e:
                logger.error(f"Redis listener error: {e}")

        # Run listener in background task
        asyncio.create_task(listener())

redis_pubsub = RedisPubSubManager()
