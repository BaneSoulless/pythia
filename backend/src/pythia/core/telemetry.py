"""
OpenTelemetry Instrumentation
SOTA 2026 Observability

Provides distributed tracing and metrics.
"""

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, db_engine=None):
    """
    Configure OpenTelemetry for the application.
    """
    try:
        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        if db_engine:
            SQLAlchemyInstrumentor().instrument(engine=db_engine)
        logger.info("OpenTelemetry calibrated and active.")
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
