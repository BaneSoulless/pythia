"""
Enhanced Reinforcement Learning Agent with State Management
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Tuple, List, Optional, Dict
from collections import deque
import random
import logging

logger = logging.getLogger(__name__)


# --- ANTI-RETRACING: Pre-compiled prediction function with fixed signature ---
@tf.function(reduce_retracing=True)
def _compiled_predict(model: keras.Model, inputs: tf.Tensor) -> tf.Tensor:
    """
    Pre-compiled prediction wrapper to prevent excessive tf.function retracing.
    Uses reduce_retracing=True to allow minor shape variations without full recompilation.
    """
    return model(inputs, training=False)
# -----------------------------------------------------------------------------


class StateBuilder:
    """
    Builds state representations from market data
    """
    
    @staticmethod
    def build_state(
        portfolio_state: Dict,
        market_indicators: Dict,
        recent_trades: List
    ) -> np.ndarray:
        """
        Create comprehensive state representation
        
        Includes:
        - Portfolio metrics (normalized)
        - Technical indicators
        - Recent performance
        """
        state_features = []
        
        # Portfolio features
        initial_balance = 10.0
        state_features.extend([
            portfolio_state.get('balance', 10.0) / initial_balance,
            portfolio_state.get('total_value', 10.0) / initial_balance,
            portfolio_state.get('positions_count', 0) / 5.0,  # Normalize to max 5 positions
        ])
        
        # Technical indicators
        state_features.extend([
            market_indicators.get('rsi', 50) / 100.0,  # RSI normalized
            market_indicators.get('sma_20', 100) / 200.0,  # Price normalized
            market_indicators.get('sma_50', 100) / 200.0 if market_indicators.get('sma_50') else 0.5,
        ])
        
        # Recent performance (last 3 trades)
        recent_pnl = [t.get('pnl', 0) for t in recent_trades[:3]]
        while len(recent_pnl) < 3:
            recent_pnl.append(0)
        state_features.extend([pnl / 10.0 for pnl in recent_pnl])  # Normalize
        
        # Time features (market volatility proxy)
        state_features.append(0.5)  # Placeholder for volatility
        
        return np.array(state_features, dtype=np.float32)


class TradingRLAgent:
    """
    Deep Q-Network (DQN) agent for learning trading strategies
    """
    
    def __init__(
        self,
        state_size: int = 10,
        action_size: int = 3,  # hold, buy, sell
        learning_rate: float = 0.001,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        memory_size: int = 10000
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=memory_size)
        
        # Hyperparameters
        self.gamma = gamma  # Discount factor
        self.epsilon = epsilon  # Exploration rate
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.learning_rate = learning_rate
        
        # Build models
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()
        
        # Training metrics
        self.training_history = {
            'loss': [],
            'rewards': [],
            'epsilon': []
        }
    
    def _build_model(self) -> keras.Model:
        """Build the neural network model"""
        model = keras.Sequential([
            keras.layers.Dense(128, activation='relu', input_shape=(self.state_size,)),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dense(self.action_size, activation='linear')
        ])
        
        model.compile(
            loss='mse',
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate)
        )
        
        return model
    
    def update_target_model(self):
        """Copy weights from model to target_model"""
        self.target_model.set_weights(self.model.get_weights())
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                 next_state: np.ndarray, done: bool):
        """Store experience in memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: np.ndarray, training: bool = True) -> Tuple[int, float]:
        """
        Choose an action using epsilon-greedy policy
        Returns: (action, confidence)
        """
        if training and np.random.random() <= self.epsilon:
            action = random.randrange(self.action_size)
            confidence = 0.33  # Random action has low confidence
        else:
            # Use pre-compiled function to prevent TensorFlow retracing
            state_input = tf.constant(state.reshape(1, -1), dtype=tf.float32)
            q_values = _compiled_predict(self.model, state_input).numpy()[0]
            action = np.argmax(q_values)
            # Confidence is softmax of Q-values
            exp_q = np.exp(q_values - np.max(q_values))
            confidence = exp_q[action] / np.sum(exp_q)
        
        return action, float(confidence)
    
    def replay(self, batch_size: int = 32) -> Optional[float]:
        """
        Experience replay for training
        Returns: loss
        """
        if len(self.memory) < batch_size:
            return None
        
        # Sample batch
        minibatch = random.sample(self.memory, batch_size)
        
        states = np.array([experience[0] for experience in minibatch])
        actions = np.array([experience[1] for experience in minibatch])
        rewards = np.array([experience[2] for experience in minibatch])
        next_states = np.array([experience[3] for experience in minibatch])
        dones = np.array([experience[4] for experience in minibatch])
        
        # Predict Q-values for starting state (anti-retracing: use compiled function)
        states_tensor = tf.constant(states, dtype=tf.float32)
        current_q_values = _compiled_predict(self.model, states_tensor).numpy()
        
        # Predict Q-values for next state (using target model, anti-retracing)
        next_states_tensor = tf.constant(next_states, dtype=tf.float32)
        next_q_values = _compiled_predict(self.target_model, next_states_tensor).numpy()
        
        # Calculate target Q-values
        for i in range(batch_size):
            if dones[i]:
                current_q_values[i][actions[i]] = rewards[i]
            else:
                current_q_values[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
        
        # Train the model
        history = self.model.fit(
            states, 
            current_q_values, 
            epochs=1, 
            verbose=0
        )
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        loss = history.history['loss'][0]
        self.training_history['loss'].append(loss)
        self.training_history['epsilon'].append(self.epsilon)
        
        return loss
    
    def save(self, filepath: str):
        """Save model weights"""
        self.model.save_weights(filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model weights"""
        self.model.load_weights(filepath)
        self.update_target_model()
        logger.info(f"Model loaded from {filepath}")
    
    def get_action_name(self, action: int) -> str:
        """Convert action index to name"""
        action_names = ['hold', 'buy', 'sell']
        return action_names[action]
    
    def get_metrics(self) -> Dict:
        """Get current training metrics"""
        return {
            'epsilon': self.epsilon,
            'memory_size': len(self.memory),
            'avg_loss': np.mean(self.training_history['loss'][-100:]) if self.training_history['loss'] else 0,
            'total_experiences': len(self.memory)
        }

class TradingEnvironment:
    """
    Trading Environment for RL Agent
    """
    def __init__(self, data: List[Dict], initial_balance: float = 10000.0):
        self.data = data
        self.initial_balance = initial_balance
        self.reset()
        
    def reset(self):
        """Reset environment to initial state"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0  # 0: flat, >0: long, <0: short (not supported yet)
        self.entry_price = 0.0
        self.trades = []
        self.done = False
        return self._get_state()
        
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one step in the environment
        
        Actions:
        0: Hold
        1: Buy
        2: Sell
        """
        if self.done:
            return self._get_state(), 0, True, {}
            
        current_price = self.data[self.current_step]['close']
        reward = 0
        
        if action == 1:  # Buy
            if self.position == 0:
                self.position = self.balance / current_price
                self.balance = 0
                self.entry_price = current_price
                
        elif action == 2:  # Sell
            if self.position > 0:
                self.balance = self.position * current_price
                reward = (current_price - self.entry_price) / self.entry_price
                self.position = 0
                self.entry_price = 0
                
        # Move to next step
        self.current_step += 1
        if self.current_step >= len(self.data) - 1:
            self.done = True
            
        return self._get_state(), reward, self.done, {}
        
    def _get_state(self) -> np.ndarray:
        """Get current state representation"""
        # Simplified state for now
        # In real implementation, use StateBuilder
        current_data = self.data[self.current_step]
        return np.array([
            current_data['close'],
            current_data.get('rsi', 50),
            self.balance,
            self.position
        ])
