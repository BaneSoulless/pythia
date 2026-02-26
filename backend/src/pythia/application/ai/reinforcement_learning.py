"""
SOTA-2026 Enhanced Reinforcement Learning Agent with State Management.
Migrated to PyTorch instead of TensorFlow to reduce overhead and 
enable better integration with modern ONNX pipelines.

Dependencies: torch>=2.2.0, numpy

Edge Cases:
- Network dimensions dynamically adapt to state/action inputs.
- Safe device fallback (CUDA if available, else CPU) avoiding crashes.
"""
# Step-1: PyTorch Imports
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Tuple, List, Optional, Dict
from collections import deque
import random
import logging

logger = logging.getLogger(__name__)

# Device isolation
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Step-2: PyTorch Model Definition
class DQNModule(nn.Module):
    """Deep Q-Network Pytorch implementation."""
    def __init__(self, state_size: int, action_size: int):
        super(DQNModule, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_size)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

class StateBuilder:
    """Builds state representations from market data"""

    @staticmethod
    def build_state(portfolio_state: Dict, market_indicators: Dict, recent_trades: List) -> np.ndarray:
        state_features = []
        initial_balance = 10.0
        
        # Safe `.get()` lookups
        state_features.extend([
            portfolio_state.get('balance', 10.0) / initial_balance, 
            portfolio_state.get('total_value', 10.0) / initial_balance, 
            portfolio_state.get('positions_count', 0) / 5.0
        ])
        
        state_features.extend([
            market_indicators.get('rsi', 50) / 100.0, 
            market_indicators.get('sma_20', 100) / 200.0, 
            market_indicators.get('sma_50', 100) / 200.0 if market_indicators.get('sma_50') else 0.5
        ])
        
        recent_pnl = [t.get('pnl', 0) for t in recent_trades[:3]]
        while len(recent_pnl) < 3:
            recent_pnl.append(0)
            
        state_features.extend([pnl / 10.0 for pnl in recent_pnl])
        state_features.append(0.5)
        return np.array(state_features, dtype=np.float32)

class TradingRLAgent:
    """Deep Q-Network (DQN) agent for learning trading strategies (PyTorch Native)."""

    def __init__(self, state_size: int=10, action_size: int=3, learning_rate: float=0.001, 
                 gamma: float=0.95, epsilon: float=1.0, epsilon_decay: float=0.995, 
                 epsilon_min: float=0.01, memory_size: int=10000):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=memory_size)
        
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.learning_rate = learning_rate
        
        # Step-3: Model Initialization & Target sync
        self.model = DQNModule(state_size, action_size).to(device)
        self.target_model = DQNModule(state_size, action_size).to(device)
        self.update_target_model()
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.MSELoss()
        
        self.training_history = {'loss': [], 'rewards': [], 'epsilon': []}

    def update_target_model(self):
        """Copy weights from model to target_model avoiding deepcopy overhead."""
        self.target_model.load_state_dict(self.model.state_dict())

    def remember(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        """Store experience in deque memory."""
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state: np.ndarray, training: bool=True) -> Tuple[int, float]:
        """Choose an action using epsilon-greedy policy."""
        # Step-4: Neuro-Symbolic Inference
        if training and np.random.random() <= self.epsilon:
            action = random.randrange(self.action_size)
            confidence = 0.33
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)
            self.model.eval()
            with torch.no_grad():
                q_values = self.model(state_tensor).cpu().numpy()[0]
            self.model.train()
                
            action = int(np.argmax(q_values))
            exp_q = np.exp(q_values - np.max(q_values))
            confidence = float(exp_q[action] / np.sum(exp_q))
            
        return (action, confidence)

    def replay(self, batch_size: int=32) -> Optional[float]:
        """Experience replay for training against MSE Loss."""
        if len(self.memory) < batch_size:
            return None
            
        minibatch = random.sample(self.memory, batch_size)
        
        # Step-5: Batch Construction
        states = torch.FloatTensor(np.array([exp[0] for exp in minibatch])).to(device)
        actions = torch.LongTensor(np.array([exp[1] for exp in minibatch])).unsqueeze(1).to(device)
        rewards = torch.FloatTensor(np.array([exp[2] for exp in minibatch])).to(device)
        next_states = torch.FloatTensor(np.array([exp[3] for exp in minibatch])).to(device)
        dones = torch.FloatTensor(np.array([exp[4] for exp in minibatch])).to(device)

        # Step-6: Q-Learning target calculation
        current_q_values = self.model(states).gather(1, actions).squeeze(1)
        
        with torch.no_grad():
            next_q_values = self.target_model(next_states).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
            
        # Optimization Step
        loss = self.loss_fn(current_q_values, target_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        loss_val = loss.item()
        self.training_history['loss'].append(loss_val)
        self.training_history['epsilon'].append(self.epsilon)
        return loss_val

    def save(self, filepath: str):
        """Save PyTorch state dict."""
        torch.save(self.model.state_dict(), filepath)
        logger.info(f'Model saved to {filepath}')

    def load(self, filepath: str):
        """Load PyTorch state dict securely."""
        self.model.load_state_dict(torch.load(filepath, map_location=device, weights_only=True))
        self.update_target_model()
        logger.info(f'Model loaded from {filepath}')

    def get_action_name(self, action: int) -> str:
        action_names = ['hold', 'buy', 'sell']
        return action_names[action]

    def get_metrics(self) -> Dict:
        return {
            'epsilon': self.epsilon, 
            'memory_size': len(self.memory), 
            'avg_loss': float(np.mean(self.training_history['loss'][-100:])) if self.training_history['loss'] else 0.0, 
            'total_experiences': len(self.memory)
        }

class TradingEnvironment:
    """Gym-like Environment for RL Agent"""
    def __init__(self, data: List[Dict], initial_balance: float=10000.0):
        self.data = data
        self.initial_balance = initial_balance
        self.reset()

    def reset(self):
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0.0
        self.trades = []
        self.done = False
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        if self.done:
            return (self._get_state(), 0, True, {})
            
        current_price = self.data[self.current_step]['close']
        reward = 0
        
        if action == 1:
            if self.position == 0:
                self.position = self.balance / current_price
                self.balance = 0
                self.entry_price = current_price
        elif action == 2:
            if self.position > 0:
                self.balance = self.position * current_price
                reward = (current_price - self.entry_price) / self.entry_price
                self.position = 0
                self.entry_price = 0
                
        self.current_step += 1
        if self.current_step >= len(self.data) - 1:
            self.done = True
            
        return (self._get_state(), reward, self.done, {})

    def _get_state(self) -> np.ndarray:
        current_data = self.data[self.current_step]
        return np.array([current_data['close'], current_data.get('rsi', 50), self.balance, self.position], dtype=np.float32)