"""
Modular Core - Strategy Layer
Cognitive Transplant: TensorFlow/Keras Inference Engine
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Dict, Any, Tuple, Optional
import logging
import random
from collections import deque
import os

logger = logging.getLogger("CognitiveCore")

# --- TF OPTIMIZATION ---
# Disable oneDNN optimizations if they cause issues, though usually fine.
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

class InferenceEngine:
    """
    Thread-safe, Optimized TensorFlow Inference Engine.
    Encapsulates the model and enforces static graph execution.
    """
    def __init__(self, state_size: int, action_size: int, model_path: Optional[str] = None):
        self.state_size = state_size
        self.action_size = action_size
        self.model = self._build_model()
        
        # Pre-compile graph
        self._compile_graph()
        
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def _build_model(self) -> keras.Model:
        model = keras.Sequential([
            keras.layers.Input(shape=(self.state_size,), dtype=tf.float32),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dense(self.action_size, activation='linear')
        ])
        model.compile(loss='mse', optimizer=keras.optimizers.Adam(learning_rate=0.001))
        return model

    def _compile_graph(self):
        """Warm up the tf.function to trace the graph once."""
        dummy_input = np.zeros((1, self.state_size), dtype=np.float32)
        _ = self.predict(dummy_input)

    @tf.function(reduce_retracing=True)
    def _predict_graph(self, inputs: tf.Tensor) -> tf.Tensor:
        """Static execution graph for inference."""
        return self.model(inputs, training=False)

    def predict(self, state: np.ndarray) -> np.ndarray:
        """
        Thread-safe prediction with automatic tensor casting.
        Args:
            state: shape (state_size,) or (batch, state_size)
        """
        # Ensure input is 2D (batch, features)
        if state.ndim == 1:
            state = state.reshape(1, -1)
            
        # Strict casting to float32 tensor
        tensor_input = tf.convert_to_tensor(state, dtype=tf.float32)
        
        # Execute static graph
        q_values = self._predict_graph(tensor_input)
        return q_values.numpy()

    def save(self, path: str):
        self.model.save_weights(path)

    def load(self, path: str):
        self.model.load_weights(path)
        logger.info(f"Weights loaded from {path}")


class RLAgent:
    """
    Reinforcement Learning Agent using InferenceEngine.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_size = 10 # Fixed for now, strictly enforced
        self.action_size = 3 # HOLD, BUY, SELL
        
        self.engine = InferenceEngine(self.state_size, self.action_size)
        
        # Hyperparameters
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        
    def act(self, state: np.ndarray, training: bool = True) -> Dict[str, Any]:
        """
        Decision making process.
        Returns: {'action': 'buy'|'sell'|'hold', 'confidence': float, 'q_values': list}
        """
        # SAFE INIT
        action_idx = 0 # Hold
        confidence = 0.0
        q_values = [0.0] * self.action_size

        # Normalize state
        state = np.nan_to_num(state).astype(np.float32)
        
        if training and random.random() <= self.epsilon:
            action_idx = random.randrange(self.action_size)
            confidence = 0.0
            q_values = [0.0] * self.action_size
        else:
            q_values_arr = self.engine.predict(state)
            q_values = q_values_arr[0].tolist()
            action_idx = np.argmax(q_values)
            
            # Softmax confidence
            exp_q = np.exp(q_values - np.max(q_values))
            confidence = float(exp_q[action_idx] / np.sum(exp_q))

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        actions = ['hold', 'buy', 'sell']
        return {
            'action': actions[action_idx],
            'confidence': confidence,
            'q_values': q_values
        }

