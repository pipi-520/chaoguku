#!/usr/bin/env bash
# Install chaogu monitor as a systemd service.
# Usage: sudo bash scripts/install_service.sh [APP_DIR]
set -euo pipefail

APP_DIR="${1:-/opt/chaogu}"
SERVICE_NAME="chaogu-monitor"

echo "[1/4] app dir: $APP_DIR"
mkdir -p "$APP_DIR"

if [ ! -d "$APP_DIR/.venv" ]; then
  echo "[2/4] creating venv"
  python3 -m venv "$APP_DIR/.venv"
fi

echo "[3/4] installing deps"
"$APP_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[4/4] installing systemd unit"
sed "s|/opt/chaogu|$APP_DIR|g" "$APP_DIR/deploy/chaogu-monitor.service" \
  > "/etc/systemd/system/$SERVICE_NAME.service"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
echo "done. status: systemctl status $SERVICE_NAME"
