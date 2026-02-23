"""
OpenTelemetry Instrumentation
SOTA 2026 Observability

Provides distributed tracing and metrics.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from fastapi import FastAPI
from sqlalchemy import engine
import logging

logger = logging.getLogger(__name__)

def setup_telemetry(app: FastAPI, db_engine=None):
    """
    Configure OpenTelemetry for the application.
    """
    try:
        # 1. Setup Tracer
        provider = TracerProvider()
        
        # In production, use OTLPExporter to send to Jaeger/Prometheus/Datadog
        # For now, ConsoleExporter is safe default
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)
        
        # 2. Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        # 3. Instrument SQLAlchemy
        if db_engine:
            SQLAlchemyInstrumentor().instrument(
                engine=db_engine,
            )
            
        logger.info("OpenTelemetry calibrated and active.")
        
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
