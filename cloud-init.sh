#!/bin/bash
# ============================================
# AI Trading Bot - Oracle Cloud Bootstrap
# Auto-configures Docker & deploys the bot
# ============================================

set -e

LOG_FILE="/var/log/trading-bot-setup.log"
exec > >(tee -a $LOG_FILE) 2>&1

echo ">>> [$(date)] INITIATING TRADING BOT DEPLOYMENT <<<"

# 1. Update System
echo "[1/6] Updating system packages..."
dnf update -y
dnf install -y git docker python3 python3-pip firewalld

# 2. Enable and Start Docker
echo "[2/6] Configuring Docker..."
systemctl enable docker
systemctl start docker

# 3. Add opc user to docker group
echo "[3/6] Setting permissions..."
usermod -aG docker opc

# 4. Configure Firewall
echo "[4/6] Opening firewall ports..."
systemctl enable firewalld
systemctl start firewalld
firewall-cmd --permanent --add-port=8000/tcp    # API
firewall-cmd --permanent --add-port=5173/tcp    # Frontend
firewall-cmd --permanent --add-port=3000/tcp    # Grafana
firewall-cmd --permanent --add-port=6379/tcp    # Redis
firewall-cmd --permanent --add-port=9090/tcp    # Prometheus
firewall-cmd --reload

# 5. Clone Repository (Replace with your repo URL)
echo "[5/6] Cloning trading bot repository..."
cd /home/opc
if [ ! -d "AI-Trading-Bot" ]; then
    # IMPORTANT: Replace this URL with your actual repository
    git clone https://github.com/YOUR_USERNAME/AI-Trading-Bot.git || echo "Clone failed - manual setup required"
fi

# 6. Create startup service
echo "[6/6] Creating systemd service..."
cat > /etc/systemd/system/trading-bot.service << 'EOF'
[Unit]
Description=AI Trading Bot Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/opc/AI-Trading-Bot
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
User=opc

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-bot

echo ">>> [$(date)] BOOTSTRAP COMPLETE <<<"
echo ">>> Manual steps remaining:"
echo ">>>   1. SSH into instance: ssh -i key opc@<PUBLIC_IP>"
echo ">>>   2. cd AI-Trading-Bot"
echo ">>>   3. Edit .env with your secrets"
echo ">>>   4. docker compose up -d --build"
