#!/usr/bin/env bash
# Provision an Ubuntu VPS for the Auto Job Tracker and install systemd units.
# Run FROM the repo root on the server. Idempotent.
#
#   bash deploy/deploy.sh                # installs to /opt/jobtracker
#   APP_DIR=/srv/jobtracker bash deploy/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/jobtracker}"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates apt-transport-https >/dev/null
if ! command -v google-chrome >/dev/null 2>&1; then
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
    echo "deb [signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list
    apt-get update -qq
    apt-get install -y -qq google-chrome-stable >/dev/null
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    apt-get install -y -qq nodejs npm >/dev/null
fi
if ! command -v pnpm >/dev/null 2>&1; then
    npm install -g pnpm >/dev/null 2>&1
fi

echo "==> Installing uv"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
export PATH="$HOME/.local/bin:$PATH"

echo "==> Copying repo to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete --exclude '.git' --exclude 'node_modules' --exclude '.venv' \
    "$SRC_DIR/" "$APP_DIR/"

echo "==> Backend deps"
cd "$APP_DIR/backend"
uv sync --group dev 2>&1 | tail -1 || uv sync 2>&1 | tail -1

echo "==> Frontend build"
cd "$APP_DIR/frontend"
if [ ! -d node_modules ]; then
    pnpm install --no-frozen-lockfile >/dev/null 2>&1 || pnpm install >/dev/null
fi
pnpm build >/dev/null

echo "==> Env file"
cd "$APP_DIR/backend"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "WARN: fill in $APP_DIR/backend/.env (SMTP/Telegram) then re-run: systemctl restart jobtracker-api"
fi

echo "==> Installing systemd units"
for unit in jobtracker-api.service jobtracker-scrape.service jobtracker-scrape.timer; do
    sed "s|__APP_DIR__|$APP_DIR|g" "$SRC_DIR/deploy/$unit" > "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --now jobtracker-api jobtracker-scrape.timer

echo "==> Done. Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
systemctl list-timers jobtracker-scrape.timer --no-pager
