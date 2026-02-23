import pytest
from unittest.mock import Mock, patch
from app.agents.specialized_agents import AgentCoordinator

@pytest.fixture
def agent_coordinator():
    return AgentCoordinator()

def test_evaluate_trade_opportunity_strong_buy(agent_coordinator):
    # Mock sub-agents
    agent_coordinator.technical_agent.analyze_trend = Mock(return_value={
        "direction": "bullish", "strength": 0.8, "confidence": 0.9
    })
    agent_coordinator.technical_agent.detect_support_resistance = Mock(return_value={
        "support": 100, "resistance": 120
    })
    agent_coordinator.technical_agent.check_bollinger_bands = Mock(return_value={})
    
    agent_coordinator.sentiment_agent.analyze_volume = Mock(return_value={
        "sentiment": "strong_interest", "strength": 0.8
    })
    
    agent_coordinator.risk_agent.calculate_position_size = Mock(return_value=1000)
    agent_coordinator.risk_agent.assess_trade_risk = Mock(return_value={
        "approved": True, "risk_score": 0.1
    })
    
    agent_coordinator.execution_agent.determine_entry_timing = Mock(return_value={
        "urgency": 0.9
    })
    
    result = agent_coordinator.evaluate_trade_opportunity(
        symbol="AAPL",
        prices=[100.0] * 20,
        volumes=[1000] * 20,
        portfolio_value=10000
    )
    
    assert result["recommendation"] in ["buy", "strong_buy"]
    assert result["symbol"] == "AAPL"
    assert result["position_size"] == 1000

def test_evaluate_trade_opportunity_risk_rejection(agent_coordinator):
    # Mock risk rejection
    agent_coordinator.technical_agent.analyze_trend = Mock(return_value={
        "direction": "bullish", "strength": 0.8, "confidence": 0.9
    })
    agent_coordinator.technical_agent.detect_support_resistance = Mock(return_value={})
    agent_coordinator.technical_agent.check_bollinger_bands = Mock(return_value={})
    agent_coordinator.sentiment_agent.analyze_volume = Mock(return_value={"strength": 0.5})
    
    agent_coordinator.risk_agent.calculate_position_size = Mock(return_value=1000)
    agent_coordinator.risk_agent.assess_trade_risk = Mock(return_value={
        "approved": False, "risk_score": 0.9, "reason": "Too risky"
    })
    
    agent_coordinator.execution_agent.determine_entry_timing = Mock(return_value={"urgency": 0.5})
    
    result = agent_coordinator.evaluate_trade_opportunity(
        symbol="AAPL",
        prices=[100.0] * 20,
        volumes=[1000] * 20,
        portfolio_value=10000
    )
    
    assert result["recommendation"] == "reject"
