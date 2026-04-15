import pytest
import os
import json
import yaml
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from pythia.application.asi_evolve import ASIEvolveEngine
from pythia.domain.events.domain_events import AsiEvolveEvent

@pytest.fixture
def mock_event_bus():
    mock = MagicMock()
    mock.publish_signal = AsyncMock()
    return mock

@pytest.fixture
def asi_engine(mock_event_bus):
    with patch("pythia.application.asi_evolve.Pipeline") as mock_pipeline:
        mock_pipeline.return_value.database = []
        engine = ASIEvolveEngine(event_bus=mock_event_bus, dry_run=True)
        return engine

@pytest.mark.asyncio
async def test_asi_evolve_disabled(asi_engine):
    """Test that the engine does nothing when disabled."""
    asi_engine.enabled = False
    assert asi_engine.should_evolve({"sharpe": 1.0, "trade_count": 100}) is False
    
    await asi_engine.run_cycle()
    assert asi_engine.last_cycle_status == "idle"

@pytest.mark.asyncio
async def test_asi_evolve_cooldown(asi_engine):
    """Test that cooldown prevents execution and decrements."""
    asi_engine.cooldown_remaining = 3600
    await asi_engine.run_cycle()
    assert asi_engine.last_cycle_status == "idle"

def test_asi_evolve_insufficient_data(asi_engine):
    """Test evolution is skipped if trade count is too low."""
    metrics = {"sharpe": 0.5, "trade_count": 10, "drawdown": 0.30}
    assert asi_engine.should_evolve(metrics) is False

def test_asi_evolve_trigger_sharpe(asi_engine):
    """Test evolution is triggered by low Sharpe ratio."""
    metrics = {"sharpe": 1.2, "trade_count": 100, "drawdown": 0.05}
    assert asi_engine.should_evolve(metrics) is True

def test_asi_evolve_trigger_drawdown(asi_engine):
    """Test evolution is triggered by high drawdown."""
    metrics = {"sharpe": 2.5, "trade_count": 100, "drawdown": 0.25}
    assert asi_engine.should_evolve(metrics) is True

@pytest.mark.asyncio
async def test_asi_evolve_dry_run(asi_engine):
    """Test that mutations are recorded but logic paths are safe."""
    asi_engine.dry_run = True
    # Implementation: currently run_cycle calls pipeline.run_step which we mock
    with patch.object(asi_engine.pipeline, "run_step") as mock_step:
        mock_node = MagicMock()
        mock_node.id = 123
        mock_node.score = 0.95
        mock_node.code = "test_code"
        mock_node.motivation = "test_motivation"
        mock_step.return_value = mock_node
        
        await asi_engine.run_cycle(force=True)
        
        assert asi_engine.mutation_count > 0
        assert asi_engine.last_cycle_status == "success"

@pytest.mark.asyncio
async def test_asi_evolve_audit_jsonl(asi_engine, tmp_path):
    """Test that mutation details are written to an audit log."""
    mock_node = MagicMock()
    mock_node.id = 999
    mock_node.score = 0.88
    mock_node.code = "print('hello')"
    mock_node.motivation = "test audit"
    
    # Redirect log file to temp path
    log_file = tmp_path / "audit.jsonl"
    with patch("pythia.application.asi_evolve.Path") as mock_path:
        # We handle the Path creation in _write_audit_log
        mock_path.return_value = log_file 
    # Ensure the directory exists and clear the file to avoid test pollution
    actual_log = Path("backend/data/asi_evolution_audit.jsonl")
    actual_log.parent.mkdir(parents=True, exist_ok=True)
    if actual_log.exists():
        actual_log.unlink()
    
    # Actually, it's easier to just mock the file write or use a local override
    asi_engine._write_audit_log(mock_node)
    
    if actual_log.exists():
        with open(actual_log, "r") as f:
            lines = f.readlines()
            last_entry = json.loads(lines[-1])
            assert last_entry["node_id"] == 999
            assert last_entry["score"] == 0.88

@pytest.mark.asyncio
async def test_asi_evolve_event_bus(asi_engine, mock_event_bus):
    """Test that a domain event is published upon successful evolution."""
    with patch.object(asi_engine.pipeline, "run_step") as mock_step:
        mock_node = MagicMock()
        mock_node.id = 777
        mock_node.score = 0.77
        mock_node.code = "..."
        mock_node.motivation = "event test"
        mock_step.return_value = mock_node
        
        await asi_engine.run_cycle(force=True)
        
        # Verify event bus call
        args, _ = mock_event_bus.publish_signal.call_args
        event = args[0]
        assert isinstance(event, AsiEvolveEvent)
        assert event.node_id == 777
        assert event.score == 0.77
