"""
Operator Console APIs.
Serves settings for Paper Trading status and global Kill Switch.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import SystemAuditEvent
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory kill switch for demonstration. In production, connect this to Redis/DB.
OPERATOR_STATE = {"kill_switch_active": False}

class KillSwitchState(BaseModel):
    is_active: bool
    reason: str | None = None

class SystemConfig(BaseModel):
    is_paper_trading: bool
    is_kill_switch_active: bool

@router.get("/config", response_model=SystemConfig)
async def get_system_config() -> Any:
    """Provides visual markers for the dashboard."""
    # SOTA-2026: Paper trading flag reflects whether we are simulating API keys
    # or utilizing Mock PM adapters. In default PYTHIA, it's always true initially.
    return {
        "is_paper_trading": True,
        "is_kill_switch_active": OPERATOR_STATE["kill_switch_active"]
    }

@router.post("/kill-switch", response_model=KillSwitchState)
async def toggle_kill_switch(state: KillSwitchState, db: Session = Depends(get_db)) -> Any:
    """Toggles global execution engine Kill Switch and logs audit event."""
    OPERATOR_STATE["kill_switch_active"] = state.is_active

    logger.warning(
        "operator_kill_switch_toggled",
        active=OPERATOR_STATE["kill_switch_active"],
        reason=state.reason
    )

    audit_event = SystemAuditEvent(
        event_type="KILL_SWITCH_TOGGLED",
        old_state=str(not state.is_active),
        new_state=str(state.is_active),
        actor="operator_api",
        details=state.reason or "No reason provided"
    )
    db.add(audit_event)
    db.commit()

    if OPERATOR_STATE["kill_switch_active"]:
        # Code to actively cancel open un-filled orders would go here
        pass

    return state
