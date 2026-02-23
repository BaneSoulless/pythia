import asyncio
import logging
import time
import sys
from datetime import datetime
logging.basicConfig(level=logging.INFO)

class ResilienceMonitor:

    def __init__(self):
        self.start_time = time.time()
        self.heartbeat_interval = 60

    async def heartbeat(self):
        while True:
            uptime = time.time() - self.start_time
            logging.info(f'System uptime: {uptime:.2f} seconds')
            await asyncio.sleep(self.heartbeat_interval)

    def reboot_on_error(self, coro):

        async def wrapper():
            try:
                await coro
            except Exception as e:
                logging.error(f'Unhandled exception: {e}, rebooting...')
                sys.exit(1)
        return wrapper
monitor = ResilienceMonitor()

async def start_monitoring():
    await monitor.heartbeat()