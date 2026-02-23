"""
Integration Tests for AI Ensemble
"""
import pytest
import numpy as np
from pythia.application.ai.reinforcement_learning import TradingRLAgent
from pythia.application.ai.ensemble import AIModelEnsemble, MultiAPIManager

class TestAIEnsemble:
    """Test suite for AI ensemble functionality"""

    @pytest.fixture
    def models(self):
        """Create test models"""
        model1 = TradingRLAgent(state_size=10, action_size=3)
        model2 = TradingRLAgent(state_size=10, action_size=3)
        model3 = TradingRLAgent(state_size=10, action_size=3)
        return [model1, model2, model3]

    @pytest.fixture
    def ensemble(self, models):
        """Create ensemble"""
        return AIModelEnsemble(models, voting_strategy='majority')

    def test_ensemble_creation(self, ensemble, models):
        """Test ensemble is created correctly"""
        assert len(ensemble.models) == 3
        assert ensemble.voting_strategy == 'majority'
        assert len(ensemble.model_weights) == 3

    def test_majority_voting(self, ensemble):
        """Test majority voting strategy"""
        state = np.random.random(10)
        action, confidence = ensemble.predict(state)
        assert action in [0, 1, 2]
        assert 0.0 <= confidence <= 1.0

    def test_unanimous_voting(self, models):
        """Test unanimous voting strategy"""
        ensemble = AIModelEnsemble(models, voting_strategy='unanimous')
        state = np.random.random(10)
        action, confidence = ensemble.predict(state)
        assert action in [0, 1, 2]

    def test_weighted_voting(self, models):
        """Test weighted voting strategy"""
        ensemble = AIModelEnsemble(models, voting_strategy='weighted')
        state = np.random.random(10)
        action, confidence = ensemble.predict(state)
        assert action in [0, 1, 2]

    def test_weight_update(self, ensemble):
        """Test model weight updates"""
        initial_weights = ensemble.model_weights.copy()
        trade_results = [5.0, 10.0, 3.0]
        ensemble.update_weights(trade_results)
        assert not np.array_equal(ensemble.model_weights, initial_weights)
        assert ensemble.model_weights[1] > ensemble.model_weights[0]
        assert ensemble.model_weights[1] > ensemble.model_weights[2]

    def test_add_model(self, ensemble):
        """Test adding a new model to ensemble"""
        new_model = TradingRLAgent(state_size=10, action_size=3)
        ensemble.add_model(new_model)
        assert len(ensemble.models) == 4
        assert len(ensemble.model_weights) == 4

class TestMultiAPIManager:
    """Test suite for multi-API manager"""

    @pytest.fixture
    def mock_apis(self):
        """Create mock API clients"""

        class MockAPI:

            def __init__(self, name, should_fail=False):
                self.name = name
                self.should_fail = should_fail

            def get_quote(self, symbol):
                if self.should_fail:
                    raise Exception(f'{self.name} failed')
                return {'symbol': symbol, 'price': 100.0, 'source': self.name}
        return [{'name': 'primary', 'client': MockAPI('primary'), 'priority': 1}, {'name': 'backup', 'client': MockAPI('backup'), 'priority': 2}, {'name': 'fallback', 'client': MockAPI('fallback'), 'priority': 3}]

    def test_api_manager_creation(self, mock_apis):
        """Test API manager initialization"""
        manager = MultiAPIManager(mock_apis)
        assert len(manager.apis) == 3
        assert manager.apis[0]['name'] == 'primary'

    def test_successful_quote_fetch(self, mock_apis):
        """Test fetching quote from primary API"""
        manager = MultiAPIManager(mock_apis)
        quote = manager.get_quote('AAPL')
        assert quote['symbol'] == 'AAPL'
        assert quote['source'] == 'primary'

    def test_failover_to_backup(self, mock_apis):
        """Test failover when primary fails"""
        mock_apis[0]['client'].should_fail = True
        manager = MultiAPIManager(mock_apis)
        quote = manager.get_quote('AAPL')
        assert quote['source'] == 'backup'

    def test_all_apis_fail(self, mock_apis):
        """Test behavior when all APIs fail"""
        for api in mock_apis:
            api['client'].should_fail = True
        manager = MultiAPIManager(mock_apis)
        with pytest.raises(Exception, match='All APIs failed'):
            manager.get_quote('AAPL')
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
