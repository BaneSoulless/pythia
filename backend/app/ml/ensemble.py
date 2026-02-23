"""
AI Model Ensemble - Multiple Models Voting

Enables multiple AI models to vote on trading decisions
"""
import logging
import numpy as np
from typing import List, Dict, Tuple
from app.ml.reinforcement_learning import TradingRLAgent

logger = logging.getLogger(__name__)


class AIModelEnsemble:
    """
    Ensemble of multiple AI models that vote on decisions
    """
    
    def __init__(self, models: List[TradingRLAgent], voting_strategy: str = "majority"):
        """
        Initialize ensemble
        
        Args:
            models: List of trained AI models
            voting_strategy: 'majority', 'unanimous', 'weighted'
        """
        self.models = models
        self.voting_strategy = voting_strategy
        self.model_weights = [1.0 / len(models)] * len(models)  # Equal weights initially
    
    def predict(self, state: np.ndarray, training: bool = False) -> Tuple[int, float]:
        """
        Get ensemble prediction
        
        Returns:
            (action, confidence)
        """
        predictions = []
        confidences = []
        
        # Get prediction from each model
        for model in self.models:
            action, confidence = model.act(state, training=training)
            predictions.append(action)
            confidences.append(confidence)
        
        # Vote based on strategy
        if self.voting_strategy == "majority":
            return self._majority_vote(predictions, confidences)
        elif self.voting_strategy == "unanimous":
            return self._unanimous_vote(predictions, confidences)
        elif self.voting_strategy == "weighted":
            return self._weighted_vote(predictions, confidences)
        else:
            return self._majority_vote(predictions, confidences)
    
    def _majority_vote(self, predictions: List[int], confidences: List[float]) -> Tuple[int, float]:
        """Majority voting"""
        # Count votes
        votes = {}
        for pred, conf in zip(predictions, confidences):
            if pred not in votes:
                votes[pred] = []
            votes[pred].append(conf)
        
        # Find action with most votes
        max_votes = 0
        best_action = 0
        avg_confidence = 0.0
        
        for action, confs in votes.items():
            if len(confs) > max_votes:
                max_votes = len(confs)
                best_action = action
                avg_confidence = np.mean(confs)
        
        # Adjust confidence based on agreement
        agreement_factor = max_votes / len(predictions)
        final_confidence = avg_confidence * agreement_factor
        
        logger.debug(f"Majority vote: action={best_action}, conf={final_confidence:.2f}, agreement={agreement_factor:.2f}")
        
        return best_action, final_confidence
    
    def _unanimous_vote(self, predictions: List[int], confidences: List[float]) -> Tuple[int, float]:
        """Unanimous voting - all models must agree"""
        if len(set(predictions)) == 1:
            # All agree
            return predictions[0], np.mean(confidences)
        else:
            # No agreement - default to hold (action 0)
            return 0, 0.0
    
    def _weighted_vote(self, predictions: List[int], confidences: List[float]) -> Tuple[int, float]:
        """Weighted voting based on model performance"""
        weighted_votes = {}
        
        for pred, conf, weight in zip(predictions, confidences, self.model_weights):
            if pred not in weighted_votes:
                weighted_votes[pred] = 0
            weighted_votes[pred] += conf * weight
        
        best_action = max(weighted_votes, key=weighted_votes.get)
        confidence = weighted_votes[best_action]
        
        return best_action, confidence
    
    def update_weights(self, trade_results: List[float]):
        """
        Update model weights based on performance
        
        Args:
            trade_results: List of P&L results for each model's predictions
        """
        # Softmax of cumulative performance
        performance = np.array(trade_results)
        exp_perf = np.exp(performance - np.max(performance))
        self.model_weights = exp_perf / np.sum(exp_perf)
        
        logger.info(f"Updated model weights: {self.model_weights}")
    
    def add_model(self, model: TradingRLAgent):
        """Add a new model to the ensemble"""
        self.models.append(model)
        n = len(self.models)
        self.model_weights = [1.0 / n] * n
        logger.info(f"Added model to ensemble. Total models: {n}")
    
    def get_ensemble_metrics(self) -> Dict:
        """Get ensemble performance metrics"""
        return {
            "num_models": len(self.models),
            "voting_strategy": self.voting_strategy,
            "model_weights": self.model_weights.tolist() if hasattr(self.model_weights, 'tolist') else self.model_weights,
            "avg_epsilon": np.mean([m.epsilon for m in self.models])
        }


class MultiAPIManager:
    """
    Manages multiple API connections with failover
    """
    
    def __init__(self, apis: List[Dict]):
        """
        Initialize with list of API configurations
        
        Args:
            apis: List of dicts with 'name', 'client', 'priority'
        """
        self.apis = sorted(apis, key=lambda x: x.get('priority', 999))
        self.current_api_index = 0
        self.failure_counts = {api['name']: 0 for api in apis}
    
    def get_quote(self, symbol: str) -> Dict:
        """
        Get quote with automatic failover
        """
        for attempt, api in enumerate(self.apis):
            try:
                result = api['client'].get_quote(symbol)
                
                # Reset failure count on success
                self.failure_counts[api['name']] = 0
                
                logger.info(f"Got quote from {api['name']}")
                return result
                
            except Exception as e:
                self.failure_counts[api['name']] += 1
                logger.warning(f"API {api['name']} failed: {e}")
                
                if attempt == len(self.apis) - 1:
                    # All APIs failed
                    raise Exception(f"All APIs failed to fetch quote for {symbol}")
                
                continue
        
        raise Exception("No APIs available")
    
    def get_api_status(self) -> Dict:
        """Get status of all APIs"""
        return {
            "apis": [
                {
                    "name": api['name'],
                    "priority": api.get('priority', 999),
                    "failures": self.failure_counts[api['name']]
                }
                for api in self.apis
            ]
        }
