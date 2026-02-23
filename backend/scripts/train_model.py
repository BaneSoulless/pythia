import sys
import os
import argparse
import logging
import traceback
import numpy as np
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.structured_logging import setup_structured_logging as setup_logging
from app.ml.reinforcement_learning import TradingRLAgent, TradingEnvironment
from app.services.market_data import market_data_service

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def fetch_training_data(symbol: str, days: int):
    """Fetch historical data for training"""
    logger.info(f"Fetching {days} days of data for {symbol}")
    try:
        data = market_data_service.get_historical_data(symbol, days=days)
        if not data:
            logger.warning(f"No data found for {symbol}")
            return []
        
        # Calculate indicators
        # Note: In a real scenario, we'd pre-calculate these for all data points
        # For now, we'll let the environment handle it or mock it
        return data
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return []

def train_agent(
    agent: TradingRLAgent,
    historical_data: list,
    episodes: int = 100,
    initial_balance: float = 10000.0
):
    """
    Train the RL agent on historical data

    Args:
        agent: The trading agent
        historical_data: List of price data
        episodes: Number of training episodes
        initial_balance: Starting balance
    """
    env = TradingEnvironment(
        data=historical_data,
        initial_balance=initial_balance
    )

    total_rewards = []
    losses = []

    logger.info(f"Starting training for {episodes} episodes")

    for episode in range(episodes):
        state = env.reset()
        total_reward = 0
        done = False
        step = 0

        while not done:
            # Agent decides action
            action = agent.act(state)

            # Execute action in environment
            next_state, reward, done, _ = env.step(action)

            # Store experience
            agent.remember(state, action, reward, next_state, done)

            total_reward += reward
            state = next_state
            step += 1

            # Training step
            if len(agent.memory) > 32:
                loss = agent.replay(batch_size=32)
                if loss:
                    losses.append(loss)

        total_rewards.append(total_reward)

        # Update target network every 10 episodes
        if episode % 10 == 0:
            agent.update_target_model()
            logger.info(
                f"Episode {episode}/{episodes} | "
                f"Total Reward: {total_reward:.4f} | "
                f"Epsilon: {agent.epsilon:.4f} | "
                f"Avg Loss: {np.mean(losses[-100:]) if losses else 0:.4f}"
            )

    logger.info("Training completed!")
    logger.info(f"Average Reward: {np.mean(total_rewards):.4f}")
    logger.info(f"Max Reward: {np.max(total_rewards):.4f}")
    logger.info(f"Final Epsilon: {agent.epsilon:.4f}")

    return {
        "rewards": total_rewards,
        "losses": losses,
        "avg_reward": np.mean(total_rewards),
        "max_reward": np.max(total_rewards),
        "final_epsilon": agent.epsilon
    }


def main():
    parser = argparse.ArgumentParser(description="Train the AI trading agent")
    parser.add_argument("--symbol", default="SPY", help="Stock symbol to train on")
    parser.add_argument("--days", type=int, default=365, help="Days of historical data")
    parser.add_argument("--episodes", type=int, default=100, help="Training episodes")
    parser.add_argument("--balance", type=float, default=10000.0, help="Initial balance")
    parser.add_argument("--output", default="trading_agent.h5", help="Output model file")

    args = parser.parse_args()

    # Fetch training data
    data = fetch_training_data(args.symbol, args.days)

    if not data:
        logger.error("No training data available")
        return

    # Create agent
    state_size = 4  # Close, RSI, Balance, Position
    agent = TradingRLAgent(
        state_size=state_size,
        action_size=3,  # hold, buy, sell
    )

    # Train
    results = train_agent(
        agent,
        data,
        episodes=args.episodes,
        initial_balance=args.balance
    )

    # Ensure directory exists
    os.makedirs("ml-models", exist_ok=True)

    # Save model
    model_path = f"ml-models/{args.output}"
    agent.save(model_path)
    logger.info(f"Model saved to {model_path}")

    # Generate report
    report = f"""
    Training Report
    ===============
    Symbol: {args.symbol}
    Episodes: {args.episodes}
    Initial Balance: €{args.balance}

    Results:
    - Average Reward: {results['avg_reward']:.4f}
    - Max Reward: {results['max_reward']:.4f}
    - Final Epsilon: {results['final_epsilon']:.4f}

    Model saved to: {model_path}
    Training completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """

    print(report)

    with open("ml-models/training_report.txt", "w") as f:
        f.write(report)


if __name__ == "__main__":
    try:
        print("DEBUG: Script starting...")
        main()
        print("DEBUG: Script finished successfully")
    except Exception:
        print("DEBUG: Exception occurred")
        traceback.print_exc()
        sys.exit(1)
