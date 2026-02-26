# ADR-0002: Deployment Runbook

## Status: Accepted

## Context

Pythia v3.1.0 runs as a multi-container stack (backend + Prometheus + Grafana) with Docker Compose. The orchestrator manages 4 concurrent tasks: Prometheus Exporter, FreqTrade Strategy, Streamlit UI, and Prediction Market Arbitrage Worker.

## Pre-Deployment Checklist

1. **Secrets provisioned** — All files in `./secrets/` must exist:
   - `kalshi_api_key.txt`
   - `kalshi_private_key.pem`
   - `polymarket_wallet_key.txt`
   - `encryption_key.bin`

2. **Environment validated** — `.env` contains required variables.

3. **Docker images built** — Run: `docker compose -f docker-compose.prod.yml build`

## Deployment Steps

```bash
# 1. Build backend image
docker compose -f docker-compose.prod.yml build --no-cache pythia-backend

# 2. Start all services
docker compose -f docker-compose.prod.yml up -d

# 3. Verify backend logs
docker compose -f docker-compose.prod.yml logs -f pythia-backend

# 4. Verify Prometheus scraping
curl -s http://localhost:9091/targets

# 5. Verify Streamlit UI
curl -I http://localhost:8501

# 6. Verify Grafana
curl -I http://localhost:3000
```

## Rollback Procedure

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Revert to previous image (if tagged)
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

## Service Ports

| Service | Internal Port | External Port |
|---|---|---|
| Pythia Backend (API) | 8000 | 8000 |
| Prometheus Exporter | 9090 | 9090 |
| Streamlit UI | 8501 | 8501 |
| Prometheus Server | 9090 | 9091 |
| Grafana | 3000 | 3000 |

## Health Checks

- **Backend**: `[ORCHESTRATOR]` log messages within 10s of start
- **Streamlit**: HTTP 200 on `:8501`
- **Prometheus**: Metrics at `:9090/metrics`
- **Prediction Markets**: `[PREDICTION_MARKETS]` logs within 5 minutes
