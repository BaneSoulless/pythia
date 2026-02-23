#!/bin/bash
# Pythia Production Health Verification Script

echo "🔍 Starting Pythia Production Health Check..."

# 1. Container Status
echo -e "\n📦 Container Status:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# 2. Streamlit UI
echo -e "\n🤖 Streamlit UI (Port 8501):"
curl -I -s http://localhost:8501 | grep "HTTP/1.1" || echo "❌ Streamlit DOWN"

# 3. Prometheus Metrics Endpoint
echo -e "\n📈 Prometheus Metrics (Port 9090 - Internal):"
docker-compose exec pythia-backend curl -s http://localhost:9090/metrics | grep "pythia_" | head -n 5 || echo "❌ Metrics API DOWN"

# 4. Prometheus Scrape Targets
echo -e "\n🎯 Prometheus Scrape Targets:"
curl -s http://localhost:9091/api/v1/targets | grep -o '"health":"up"' || echo "❌ Scrape Target DOWN"

# 5. Grafana UI
echo -e "\n🖼️ Grafana UI (Port 3000):"
curl -I -s http://localhost:3000/api/health | grep "HTTP/1.1" || echo "❌ Grafana DOWN"

# 6. Database Check
echo -e "\n🗄️ Database Event Count:"
docker-compose exec pythia-backend python -c "import sqlite3; conn=sqlite3.connect('/app/data/pythia_prod.db'); print('Total Events:', conn.execute('SELECT COUNT(*) FROM event_log').fetchone()[0]); conn.close()" || echo "❌ DB UNREACHABLE"

echo -e "\n✅ Health Check Complete."
