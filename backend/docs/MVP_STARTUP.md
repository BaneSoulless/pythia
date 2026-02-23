# PYTHIA MVP Startup Guide

Welcome to the Pythia Core MVP! This guide provides step-by-step instructions for executing a safe, risk-free test run of the AI Trading platform using the Dual-Mode Architecture (Freqtrade + Groq LLM).

## 1. Environment Preparation

Before launching, you must configure the environment variables:
1. Navigate to the `backend/` directory.
2. Copy the template: `cp .env.example .env`
3. Edit `.env` with your simulated API keys:
   - **GROQ_API_KEY**: Required for semantic AI signals (free tier is sufficient).
   - **BINANCE_TESTNET_API_KEY**: Required for paper trading. Generate one at [Binance Testnet](https://testnet.binance.vision/).

## 2. Verification of Test Constraints

Ensure `backend/freqtrade_config.json` retains its safety mechanisms:
- `"dry_run": true`
- `"stake_amount": 50`
- `exchange.name`: `"binance"` with the testnet URLs enabled.

*Do not change `dry_run` to `false` during the MVP phase.*

## 3. Launching the MVP

We have provided an automated bash script that initializes the database, starts the Freqtrade background worker, and launches the Streamlit UI dashboard.

Run the following command from the `backend/` directory:
```bash
bash pythia_test.sh
```

### Expected Output Sequence:
1. **Dependencies**: `pip install -e .` ensures the package structure is linked.
2. **Database**: A local `pythia_test.db` SQLite database is generated.
3. **Freqtrade Worker**: The adapter initializes `FreqtradeStrategy` asynchronously. You should see Freqtrade's standard startup logs indicating "Dry run is enabled".
4. **Streamlit UI**: A web browser will automatically open at `http://localhost:8501`.

## 4. Troubleshooting

- **Error: `ModuleNotFoundError: No module named 'pythia...'`** 
  Ensure your virtual environment is activated and you have executed `pip install -e .` inside the `backend` folder.
- **Error: `freqtrade config missing`**
  Ensure you are running the script strictly from the `backend/` directory so relative paths resolve correctly.
- **Error: Freqtrade fails to download data**
  If missing candlestick data causes startup failures, download it manually using Freqtrade:
  `freqtrade download-data --config freqtrade_config.json --days 5 -t 15m 1h`
