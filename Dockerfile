FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /build/
# Create dummy package structure to trick setuptools into installing dependencies first
RUN mkdir -p /build/backend/src/pythia && touch /build/backend/src/pythia/__init__.py
RUN pip install --no-cache-dir --prefix=/install .

# Now copy actual source code. This layer will invalidate only when source changes, 
# keeping the heavy dependency download layer cached!
COPY backend/src /build/backend/src/
RUN pip install --no-cache-dir --prefix=/install .


FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r pythia && useradd -r -g pythia pythia

COPY --from=builder /install /usr/local
COPY --from=builder /build/backend/src /app/backend/src/
COPY pyproject.toml /app/

RUN pip install --no-cache-dir . \
    && mkdir -p /app/data /app/logs \
    && chown -R pythia:pythia /app

ENV PYTHONPATH=/app/backend/src
ENV EXECUTION_MODE=production
ENV STREAMLIT_SERVER_PORT=8501

EXPOSE 8000 8501 9090

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/health || exit 1

USER pythia

CMD ["python", "-m", "pythia.infrastructure.orchestrator"]
