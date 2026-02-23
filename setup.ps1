#!/usr/bin/env pwsh
# SetupScript for AI Trading Bot
# Auto-install and configure all dependencies

Write-Host "🚀 AI Trading Bot - Automated Setup" -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

# Check Python
Write-Host "✓ Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python not found! Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Install Backend Dependencies
Write-Host "`n✓ Installing backend dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Backend dependencies installed" -ForegroundColor Green

# Setup Database
Write-Host "`n✓ Setting up database..." -ForegroundColor Yellow
if (Test-Path "alembic/versions/add_auth_and_new_models.py") {
    alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Database migrations applied" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Database migration failed (may already be applied)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ No migrations found, skipping" -ForegroundColor Yellow
}

# Check .env file
Set-Location ..
if (-not (Test-Path ".env")) {
    Write-Host "`n⚠ Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  ✓ .env file created - please update API keys!" -ForegroundColor Green
} else {
    Write-Host "`n✓ .env file exists" -ForegroundColor Green
}

# Check Node.js (optional for frontend)
Write-Host "`n✓ Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  Found: $nodeVersion" -ForegroundColor Green
    
    # Install frontend dependencies
    Write-Host "`n✓ Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Frontend installation failed" -ForegroundColor Red
    }
    Set-Location ..
} catch {
    Write-Host "  ⚠ Node.js not found - frontend setup skipped" -ForegroundColor Yellow
    Write-Host "  Install Node.js from: https://nodejs.org/" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your API keys" -ForegroundColor White
Write-Host "2. Start backend: cd backend && python main.py" -ForegroundColor White
Write-Host "3. Start frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host "4. Visit: http://localhost:5173" -ForegroundColor White
Write-Host "`n📚 Documentation: See README.md" -ForegroundColor Cyan
