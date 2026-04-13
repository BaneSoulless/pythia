"""
Celery tasks for the Intelligence layer.
Executes signal generation and publishes `TradeIntent` payloads safely to Redis.
"""

import asyncio

import redis
import structlog

from pythia.application.ai_providers.groq_client import GroqClient
from pythia.core.config import settings
from pythia.domain.prediction_markets.models import TradeIntent
from pythia.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Initialize a direct Redis client for emitting TradeIntents outside Celery's result backend
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

INTENT_QUEUE_KEY = "pythia:intents:queue"


@celery_app.task(name="pythia.workers.tasks.evaluate_market")
def evaluate_market_task(market_id: str, question_title: str, outcomes: list[dict], news_context: str):
    """
    Synchronous Celery wrapper to evaluate a market. Runs the async GroqClient in an event loop.
    Emits a TradeIntent to Redis if probability edges exceed thresholds.
    """
    logger.info("Starting intelligence evaluation", market_id=market_id)

    async def _run_evaluation():
        client = GroqClient()

        # Simplified dynamic prompt for PMs
        prompt = (
            f"Evaluate the probability of this prediction market resolving 'Yes'.\n"
            f"Market: {question_title}\n"
            f"Context: {news_context}\n"
            f"Output strictly valid JSON with 'confidence' (0.0-1.0), 'action' ('BUY'/'SELL'), "
            f"and 'rationale' (max 280 chars). Focus on statistical edge."
        )
        # Using the internal executor directly since get_signal assumes crypt/stock schemas
        result = await client._execute_groq_request(prompt, market_id)

        # Determine the target outcome dynamically (Usually outcome[0] is YES for binary)
        target_outcome = outcomes[0]
        market_implied = target_outcome.get("implied_probability", 0.5)

        # In a real setup, agent_probability comes back from Groq structured output.
        # Using the confidence field as a proxy for this MVP transition to TradeIntent.
        intent = TradeIntent(
            signal_id=f"sig_{market_id}_{len(prompt)}",
            market_id=market_id,
            outcome_id=target_outcome["id"],
            action=result.action,  # Normally BUY to accumulate 'Yes' shares if agent_prob > implied
            confidence=result.confidence,
            agent_probability=result.confidence, # simplified
            market_implied_probability=market_implied,
            rationale=result.rationale,
            max_slippage=0.03
        )

        if intent.action in ("BUY", "SELL"):
            payload = intent.model_dump_json()
            redis_client.lpush(INTENT_QUEUE_KEY, payload)
            logger.info("Published TradeIntent", intent=intent.model_dump())
        else:
            logger.info("Holding market, no intent published", market_id=market_id)

    # Execute async core
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_evaluation())
    return True
