#!/bin/bash
set -e

echo "🤖 PYTHIA Test Mode Startup..."

# 1. Check environment
if [ ! -f .env ]; then
    echo "❌ .env not found. Copy .env.example and configure."
    exit 1
fi

# 2. Install dependencies (assuming venv active or containerized)
pip install -q -r requirements.txt

# 3. Initialize SQLite DB
python -c "import sqlite3; conn = sqlite3.connect('pythia_test.db'); conn.execute('CREATE TABLE IF NOT EXISTS trade_events (timestamp TEXT, pair TEXT, action TEXT, pnl REAL, confidence REAL)'); conn.close()"

# 4. Start Freqtrade (background)
python -c "from app.adapters.freqtrade_adapter import start_freqtrade_bot; start_freqtrade_bot()" &
FREQTRADE_PID=$!

# 5. Launch Streamlit UI
streamlit run streamlit_app.py --server.port 8501

# Cleanup on exit
trap "kill $FREQTRADE_PID" EXIT
