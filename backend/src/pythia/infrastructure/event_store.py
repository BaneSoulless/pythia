"""
Event Store Infrastructure
SOTA 2026 Persistence

This module implements the Append-Only Log pattern for Event Sourcing.
It uses SQLAlchemy for persistence, supporting both PostgreSQL and SQLite.

Schema:
- id: Sequence ID (Global ordering)
- stream_id: Aggregate ID (e.g., 'order-123')
- event_type: String identifier (e.g., 'OrderCreated')
- data: JSON payload
- created_at: Timestamp (UTC)
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func
from typing import List, Dict, Any, Optional
import datetime
from pythia.infrastructure.persistence.database import Base, get_db

class EventLog(Base):
    """
    Immutable Event Log table.
    """
    __tablename__ = 'event_log'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stream_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'stream_id': self.stream_id, 'event_type': self.event_type, 'data': self.data, 'version': self.version, 'created_at': self.created_at.isoformat() if self.created_at else None}

class EventStore:

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def append(self, stream_id: str, event_type: str, data: Dict[str, Any], expected_version: Optional[int]=None) -> EventLog:
        """
        Append a new event to the stream.
        """
        db = self.session_factory()
        try:
            if expected_version:
                last_event = db.query(EventLog).filter(EventLog.stream_id == stream_id).order_by(EventLog.id.desc()).first()
                current_version = last_event.version if last_event else 0
                if current_version != expected_version:
                    raise ValueError(f'Concurrency conflict: Expected v{expected_version}, found v{current_version}')
                version = current_version + 1
            else:
                version = 1
            new_event = EventLog(stream_id=stream_id, event_type=event_type, data=data, version=version)
            db.add(new_event)
            db.commit()
            db.refresh(new_event)
            return new_event
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_stream(self, stream_id: str) -> List[EventLog]:
        """
        Read all events for a given stream.
        """
        db = self.session_factory()
        try:
            events = db.query(EventLog).filter(EventLog.stream_id == stream_id).order_by(EventLog.id.asc()).all()
            return events
        finally:
            db.close()