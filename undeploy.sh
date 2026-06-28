#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# StreamParty — Undo Deployment Script
# ============================================================
#
# This script undoes the actions performed by deploy.sh:
#   - Stops and disables the systemd services
#   - Removes the systemd service files
#   - Deletes the 'streamparty' user
#   - Reverts ownership of the app directory back to your current user
#   - Removes the backend virtual environment and .env file
#
# Usage: sudo bash undeploy.sh
# ============================================================

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="${APP_USER:-streamparty}"
ORIGINAL_USER="${SUDO_USER:-$USER}"

# --- Colors ---
GREEN='\033[0;32m'
NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo bash undeploy.sh"
  exit 1
fi

log "Stopping systemd services..."
systemctl stop streamparty || true
systemctl stop streamparty-frontend || true

log "Disabling systemd services..."
systemctl disable streamparty || true
systemctl disable streamparty-frontend || true

log "Removing systemd service files..."
rm -f /etc/systemd/system/streamparty.service
rm -f /etc/systemd/system/streamparty-frontend.service
systemctl daemon-reload

log "Removing the app user ($APP_USER)..."
if id "$APP_USER" &>/dev/null; then
  userdel -f "$APP_USER" || true
fi

log "Reverting ownership of $APP_DIR to $ORIGINAL_USER..."
chown -R "$ORIGINAL_USER:$ORIGINAL_USER" "$APP_DIR"

log "Cleaning up backend files..."
rm -rf "$APP_DIR/backend/venv"
rm -f "$APP_DIR/backend/.env"

# Optional: Stop Redis (uncomment if you want to completely disable Redis)
# log "Stopping Redis..."
# systemctl stop redis-server || true
# systemctl disable redis-server || true

log "========================================="
log "  Cleanup complete! All services removed."
log "========================================="
