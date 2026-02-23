import sqlite3
import os
import json
from contextlib import contextmanager
DB_PATH = os.path.abspath(os.getenv('SQLITE_DB_PATH', '/app/data/pythia_prod.db'))

class SQLiteEventStore:
    """Local SQLite append-only datastore test mode proxy."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stream_id TEXT,
                    event_type TEXT,
                    data TEXT
                )
            ''')

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
        data = {
            "pair": pair,
            "action": action,
            "pnl": pnl,
            "confidence": confidence,
            "price": raw_data.get('price', 0.0) if raw_data else 0.0,
            ** (raw_data or {})
        }
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO event_log (stream_id, event_type, data) VALUES (?, ?, ?)",
                (pair, "trade.executed", json.dumps(data))
            )