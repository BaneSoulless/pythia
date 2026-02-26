FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for build and runtime
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy build config first
COPY pyproject.toml /app/
COPY backend/src /app/backend/src/

# Install the package in editable mode
# Note: pyproject.toml points to backend/src for package discovery
RUN pip install --no-cache-dir -e .

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Environment variables
ENV PYTHONPATH=/app/backend/src
ENV EXECUTION_MODE=production
ENV STREAMLIT_SERVER_PORT=8501

# Expose ports for API, UI, and Metrics
EXPOSE 8000 8501 9090

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default entrypoint: Run the Pythia Orchestrator (Supervisor)
CMD ["python", "-m", "pythia.infrastructure.orchestrator"]
