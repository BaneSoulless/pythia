# 🚀 PYTHIA PRODUCTION DEPLOYMENT GUIDE

This guide provides the final instructions for deploying the production-ready Pythia AI Trading Bot (SOTA 2026).

## STEP 1: SYNC REPOSITORY
```bash
cd E:\Programmazione\Progetti Google Antigravity\AI-Trading-Bot
git pull origin main
# Verify commit: git log -1 --oneline
# Expected: 8c43a09 feat: Finalize production environment with Monitoring, Docker, and CI/CD
```

## STEP 2: CONFIGURE API KEYS
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```ini
# Required
GROQ_API_KEY=gsk_your_actual_groq_api_key_here

# Optional (for Binance Testnet dry-run mode)
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_SECRET=your_testnet_secret

# Execution Mode
EXECUTION_MODE=production
DATABASE_URL=sqlite:///./data/pythia_prod.db
```

## STEP 3: DEPLOY PRODUCTION STACK
```bash
# Build and launch 3-tier stack (Backend + Prometheus + Grafana)
docker-compose up --build -d
```

## STEP 4: ACCESS SERVICES
- **Streamlit Dashboard**: http://localhost:8501
- **Grafana Monitoring**: http://localhost:3000 (admin / pythia_admin)
- **Prometheus Metrics**: http://localhost:9091

## STEP 5: VERIFICATION CHECKLIST
- [ ] Containers running (`docker-compose ps`)
- [ ] Backend logs show Groq Signals (`docker-compose logs -f pythia-backend`)
- [ ] Grafana dashboard imported from `/monitoring/grafana_dashboard.json`
- [ ] Prometheus target `pythia-backend:9090` is UP
