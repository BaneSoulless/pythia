# Enterprise Migration Checklist (Test → Production)

The PYTHIA **Thread MVP (Test Mode)** is designed to run until statistical confidence is achieved. Do not migrate to Production Mode (Enterprise Real Money) until all criteria below are met.

## Validation Criteria (Phase 1: Observation)

Run the bot continuously in Test Mode on Binance Testnet with a €50 virtual stake.

- [ ] **Data Volume**: 100+ trades executed entirely autonomously by the `freqtrade_adapter`.
- [ ] **Sharpe Ratio**: > 1.5 achieved over the 100+ trades.
- [ ] **Win Rate**: > 55% verified over a minimum of 14 continuous running days.
- [ ] **Max Drawdown**: Kept completely < 10% during peak volatility triggers.
- [ ] **API Resilience**: 0 complete crashes due to unexpected Groq rate limits (Circuit Breaker verified).
- [ ] **Signal Accuracy**: AI Confidence ratings > 0.8 correctly correlated with actual short-term asset appreciation.

## Migration Steps (Phase 2: Hot Swap)

Zero code rewriting is required. Transition is handled purely via configuration.

### 1. Provision Infrastructure
- [ ] Deploy **PostgreSQL** (EventStore replacement for SQLite)
- [ ] Deploy **Redis** (Idempotency replacement for In-Memory dict)
- [ ] Provision **Weaviate Cloud Free Tier** (ChromaDB replacement)
- [ ] Register **Puter.com API Key** for the 7-Model Ensemble (Groq replacement)

### 2. Update Environment (`.env`)
Map the production URLs and keys:
```bash
POSTGRES_URL=postgresql+psycopg2://user:pass@host:5432/pythia
REDIS_URL=redis://host:6379/1
WEAVIATE_URL=https://cluster.weaviate.cloud
WEAVIATE_API_KEY=your_key
PUTER_API_KEY=your_key
BINANCE_API_KEY=REAL_TRADING_KEY
BINANCE_SECRET=REAL_TRADING_SECRET
```

### 3. Switch Mode
Edit `backend/app/core/risk_params.yaml`:
```diff
- execution_mode: "test"
+ execution_mode: "production"

- dry_run: true
+ dry_run: false
```

### 4. Restart System
The FastAPI / ZeroMQ production architecture will now invoke the Enterprise stack.
```bash
docker-compose up -d --build
```
