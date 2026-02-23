# PYTHIA Thread MVP: Quick Start Guide

This guide will deploy the zero-cost **Test Mode (Thread MVP)** architecture in 5 simple commands.

## Prerequisites
- Python 3.11+
- Binance Testnet Account ([Create one here](https://testnet.binance.vision/))
- Groq API Key ([Get one here](https://console.groq.com/keys))

## 5-Command Deployment

```bash
# 1. Enter the backend directory and copy environment template
cd backend/
cp .env.example .env

# EDIT .env NOW: Add your GROQ_API_KEY, BINANCE_TESTNET_API_KEY, and SECRET

# 2. Install dependencies (Test Mode requirements)
pip install -r requirements.txt freqtrade streamlit ta

# 3. Make the startup script executable
chmod +x pythia_test.sh

# 4. (Optional but recommended) Run the MVP validation tests to ensure your environment is clean
pytest tests/test_thread_mvp.py -v

# 5. Launch Test Mode! (Starts Freqtrade Bot + Streamlit UI)
./pythia_test.sh
```

## Accessing the Dashboard
Once the startup script completes, open your browser:
**➡️ http://localhost:8501**

You are now paper-trading with live market data using Groq Llama-3/Mixtral constraints!
