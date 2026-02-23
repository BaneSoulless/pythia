<#
.SYNOPSIS
    PYTHIA Test Mode Startup Script (Windows / PowerShell)
.DESCRIPTION
    Initializes the AI Trading platform in a safe, risk-free MVP test environment.
    Runs the SQLite database setup, initiates the Freqtrade background worker,
    and launches the Streamlit UI.
#>
$ErrorActionPreference = "Stop"

Write-Host "🤖 PYTHIA Test Mode Startup..." -ForegroundColor Cyan

# 1. Check environment
if (-Not (Test-Path -Path ".env")) {
    Write-Host "❌ .env not found. Please copy .env.example, configure it, and try again." -ForegroundColor Red
    exit 1
}

# 2. Install dependencies (assuming venv active)
Write-Host "📦 Installing dependencies from pyproject.toml..." -ForegroundColor Yellow
pip install -q -e .

# 3. Initialize SQLite DB
Write-Host "🗄️ Initializing SQLite Database (pythia_test.db)..." -ForegroundColor Yellow
python -c "import sqlite3; conn = sqlite3.connect('pythia_test.db'); conn.execute('CREATE TABLE IF NOT EXISTS trade_events (timestamp TEXT, pair TEXT, action TEXT, pnl REAL, confidence REAL)'); conn.close()"

# 4. Start Freqtrade (background)
Write-Host "📈 Starting Freqtrade Adapter in background..." -ForegroundColor Yellow
$freqtradeJob = Start-Job -Name "FreqtradeWorker" -ScriptBlock {
    # Set execution context if needed (requires same environment)
    Set-Location -Path $using:PWD
    python -c "from pythia.adapters.freqtrade_adapter import start_freqtrade_bot; start_freqtrade_bot()" 
}
Write-Host "Freqtrade started with Job ID: $($freqtradeJob.Id)"

# 5. Launch Streamlit UI
Write-Host "🚀 Launching Streamlit UI..." -ForegroundColor Green
try {
    streamlit run streamlit_app.py --server.port 8501
}
catch {
    Write-Host "❌ Error launching Streamlit: $_" -ForegroundColor Red
}
finally {
    # Cleanup on exit
    Write-Host "🧹 Cleaning up background jobs..." -ForegroundColor Yellow
    Stop-Job -Name "FreqtradeWorker" -PassThru | Remove-Job -Force
    Write-Host "Done." -ForegroundColor Green
}
