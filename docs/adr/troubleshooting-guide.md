# ADR-0003: Troubleshooting Guide

## Status: Accepted

## Common Issues

### 1. Streamlit Connection Refused (ERR_CONNECTION_REFUSED)

**Symptoms**: Browser shows "Impossibile raggiungere il sito" at `localhost:8501`.

**Root Causes**:
- Port 8501 not exposed in `docker-compose.prod.yml`
- Streamlit binding to `127.0.0.1` instead of `0.0.0.0`
- Container not starting due to missing dependencies

**Fix**:
```bash
# Verify port mapping
docker compose -f docker-compose.prod.yml ps

# Check if Streamlit is running inside container
docker compose -f docker-compose.prod.yml exec pythia-backend curl -I http://localhost:8501

# Check orchestrator logs
docker compose -f docker-compose.prod.yml logs pythia-backend | grep STREAMLIT
```

### 2. Docker Build Fails

**Symptoms**: `docker compose build` exits with code 1.

**Root Causes**:
- Build context misconfigured (must be `.`, not `./backend`)
- `pyproject.toml` not found in build context
- Python dependency resolution failure

**Fix**:
```bash
# Verify build context
grep "context:" docker-compose.prod.yml
# Should be: context: .

# Rebuild with verbose output
docker compose -f docker-compose.prod.yml build --no-cache --progress=plain pythia-backend
```

### 3. Secrets Not Loading (FileNotFoundError)

**Symptoms**: `[ORCHESTRATOR] ⚠️ No encrypted env found, falling back to plaintext.`

**Root Causes**:
- `./secrets/` directory empty or missing files
- Docker Secrets not mounted correctly
- `SecretsManager` encryption key not provisioned

**Fix**:
```bash
# Verify secrets exist
ls -la ./secrets/

# Generate encryption key for dev
python -c "from cryptography.fernet import Fernet; open('secrets/encryption_key.bin','wb').write(Fernet.generate_key())"

# In production: provision via CI/CD secret manager
```

### 4. Prediction Markets Worker Not Scanning

**Symptoms**: No `[PREDICTION_MARKETS]` or `[ORCHESTRATOR] PM Worker` in logs.

**Root Causes**:
- Missing API keys (`KALSHI_API_KEY`, `POLYMARKET_WALLET_KEY`)
- `pmxt` library not installed
- Worker exception causing silent loop exit

**Fix**:
```bash
# Check for PM worker logs
docker compose -f docker-compose.prod.yml logs pythia-backend | grep -E "PM Worker|PREDICTION"

# Verify pmxt is installed
docker compose -f docker-compose.prod.yml exec pythia-backend pip show pmxt

# Check API key env vars
docker compose -f docker-compose.prod.yml exec pythia-backend env | grep -E "KALSHI|POLYMARKET"
```

### 5. Prometheus Metrics Not Exporting

**Symptoms**: `curl localhost:9090/metrics` returns empty or connection refused.

**Root Causes**:
- Port conflict (another service on 9090)
- `start_http_server` failed silently

**Fix**:
```bash
# Check if port is in use
docker compose -f docker-compose.prod.yml exec pythia-backend netstat -tlnp | grep 9090

# Check exporter logs
docker compose -f docker-compose.prod.yml logs pythia-backend | grep Prometheus
```

### 6. Circuit Breaker Stuck in OPEN State

**Symptoms**: All prediction market operations fail fast with `CircuitBreakerOpenError`.

**Root Causes**:
- API endpoint down or rate-limited
- Network connectivity issue from container
- Failure threshold exceeded (default: 5 failures)

**Fix**:
```bash
# Check circuit breaker state via Prometheus
curl -s http://localhost:9090/metrics | grep circuit_breaker

# Manual reset via Streamlit UI: click "Reset Circuit Breaker" button

# Check recovery timeout (default: 60s)
# CB will auto-transition to HALF_OPEN after timeout
```

## Diagnostic Commands

```bash
# Full service status
docker compose -f docker-compose.prod.yml ps

# Backend health (last 100 lines)
docker compose -f docker-compose.prod.yml logs --tail=100 pythia-backend

# Resource usage
docker stats --no-stream

# Network connectivity between containers
docker compose -f docker-compose.prod.yml exec pythia-backend curl -s http://pythia-prometheus:9090/targets
```
