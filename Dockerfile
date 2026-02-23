# Stage 1: Builder (Dependencies)
FROM python:3.11-slim as builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install to local user directory
RUN pip install --user --no-warn-script-location -r requirements.txt
RUN pip install --user redis prometheus_client

# Stage 2: Runtime (Minimal)
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Copy installed packages
COPY --from=builder /root/.local /root/.local

# Copy Source Code
COPY . .

# Healthcheck for Watchdog Daemon
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "nexus_launcher.py"]
