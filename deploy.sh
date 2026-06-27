#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# StreamParty — Production Deployment Script (Ubuntu/Debian VM)
# ============================================================
#
# Usage:
#   1. Copy this repo to your VM
#   2. Run: sudo bash deploy.sh
#
# What this does:
#   - Installs system dependencies (Node 20, Python 3, Redis)
#   - Builds the frontend
#   - Sets up the backend as a systemd service on port 8000
#   - Backend serves API + WebSocket on localhost:8000
#   - Frontend runs on its own dev server or is accessed separately
#
# Prerequisites:
#   - A VM running Ubuntu 22.04+ or Debian 12+
#   - Port 8000 open in your firewall/security group
# ============================================================

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="${APP_USER:-streamparty}"

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo bash deploy.sh"
  exit 1
fi

# ============================================================
# 1. System dependencies
# ============================================================
log "Updating system packages..."
apt-get update -y
apt-get install -y curl git python3 python3-pip python3-venv redis-server

# Install Node.js 20 via NodeSource
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  log "Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

log "Node $(node -v) | npm $(npm -v) | Python $(python3 --version)"

# ============================================================
# 2. Create app user
# ============================================================
if ! id "$APP_USER" &>/dev/null; then
  log "Creating user $APP_USER..."
  useradd -r -m -s /bin/bash "$APP_USER"
fi

# ============================================================
# 3. Enable and start Redis
# ============================================================
log "Starting Redis..."
systemctl enable redis-server
systemctl start redis-server

# ============================================================
# 4. Backend setup
# ============================================================
log "Setting up backend..."

# Create .env for production Redis
cat > "$APP_DIR/backend/.env" << ENVEOF
REDIS_URL=redis://localhost:6379
ENVEOF

# Create Python venv and install dependencies
cd "$APP_DIR/backend"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install fastapi uvicorn[standard] redis httpx pydantic websockets python-dotenv fakeredis

# ============================================================
# 5. Build frontend
# ============================================================
log "Building frontend..."
cd "$APP_DIR/frontend"
npm install
npm run build

# ============================================================
# 6. Systemd service for the backend
# ============================================================
log "Creating systemd service..."

cat > /etc/systemd/system/streamparty.service << EOF
[Unit]
Description=StreamParty Backend
After=network.target redis-server.service
Wants=redis-server.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin:/usr/bin"
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app \\
    --host 0.0.0.0 \\
    --port 8000 \\
    --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ============================================================
# 7. Systemd service for the frontend
# ============================================================
log "Creating frontend systemd service..."

# Install serve globally for the streamparty user
sudo -u "$APP_USER" bash -c "cd $APP_DIR/frontend && npm install -g serve"

cat > /etc/systemd/system/streamparty-frontend.service << EOF
[Unit]
Description=StreamParty Frontend
After=network.target streamparty.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/frontend
Environment="PATH=$APP_DIR/frontend/node_modules/.bin:/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/npx serve -s dist -l 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

systemctl daemon-reload
systemctl enable streamparty
systemctl enable streamparty-frontend
systemctl restart streamparty
systemctl restart streamparty-frontend

# ============================================================
# Done
# ============================================================
echo ""
log "========================================="
log "  StreamParty deployed successfully!"
log "========================================="
log ""
log "  Backend:   http://localhost:8000"
log "  Frontend:  http://localhost:3000"
log ""
log "  Status:"
log "    systemctl status streamparty            # backend"
log "    systemctl status streamparty-frontend   # frontend"
log ""
log "  Logs:"
log "    journalctl -u streamparty -f            # backend logs"
log "    journalctl -u streamparty-frontend -f   # frontend logs"
log ""
log "  Useful commands:"
log "    sudo systemctl restart streamparty            # restart backend"
log "    sudo systemctl restart streamparty-frontend   # restart frontend"
log "    sudo systemctl status redis-server            # check redis"
log ""
