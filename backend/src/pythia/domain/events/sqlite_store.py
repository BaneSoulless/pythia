import sqlite3
import os
import json
from contextlib import contextmanager
DB_PATH = os.getenv('SQLITE_DB_PATH', 'pythia_test.db')

class SQLiteEventStore:
    """Local SQLite append-only datastore test mode proxy."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('\n                CREATE TABLE IF NOT EXISTS trade_events (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,\n                    pair TEXT,\n                    action TEXT,\n                    pnl REAL,\n                    confidence REAL,\n                    raw_event JSON\n                )\n            ')

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            conn.close()

    def append_event(self, pair: str, action: str, pnl: float=0.0, confidence: float=0.0, raw_data: dict=None):
        """Aggiunge un evento immutabile al log di test."""
        with self._get_connection() as conn:
            conn.execute('INSERT INTO trade_events (pair, action, pnl, confidence, raw_event) VALUES (?, ?, ?, ?, ?)', (pair, action, pnl, confidence, json.dumps(raw_data or {})))