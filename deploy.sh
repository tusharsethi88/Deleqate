#!/bin/bash
# ──────────────────────────────────────────────────────────────
#  Deleqate — Auto Deploy Script  (Django backend + React frontend)
#  Run ON THE SERVER:  bash deploy.sh
#  Pulls latest code from GitHub, rebuilds both halves, restarts.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/home/opc/deleqate"      # repo root on the server
BRANCH="main"                     # GitHub branch to deploy
BACKEND_SERVICE="deleqate"        # systemd unit running gunicorn (Django)

cd "$APP_DIR"

echo ""
echo "=========================================="
echo "  Deleqate Deploy — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. Pull latest code (keeps .env, *.db, uploads/, deliverables/ — all gitignored)
echo ""
echo "▶ Pulling latest code from GitHub ($BRANCH)..."
git fetch origin
git reset --hard "origin/$BRANCH"
echo "✓ Code updated."

# 2. Backend — Django (venv + deps + session migrations)
echo ""
echo "▶ Backend: installing dependencies & migrating..."
cd "$APP_DIR/backend"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
python manage.py migrate --noinput          # creates the Django session table
deactivate
cd "$APP_DIR"
echo "✓ Backend ready."

# 3. Frontend — React (install + production build into frontend/dist)
echo ""
echo "▶ Frontend: building production bundle..."
cd "$APP_DIR/frontend"
if [ ! -f .env.production ]; then
  echo "✗ Missing frontend/.env.production (must set VITE_API_BASE=https://api.<your-domain>)" >&2
  exit 1
fi
if command -v npm >/dev/null 2>&1; then
  npm ci 2>/dev/null || npm install
  npm run build
else
  echo "✗ npm not found. Install Node.js 18+ on the server first." >&2
  exit 1
fi
cd "$APP_DIR"
echo "✓ Frontend built → frontend/dist"

# 4. Restart services
echo ""
echo "▶ Restarting services..."
sudo systemctl restart "$BACKEND_SERVICE"
sudo systemctl reload nginx
sleep 2

# 5. Health check
STATUS=$(systemctl is-active "$BACKEND_SERVICE" || true)
if [ "$STATUS" = "active" ]; then
  echo "✓ Backend ($BACKEND_SERVICE) is running."
else
  echo "✗ Backend failed to start. Logs:"
  echo "  sudo journalctl -u $BACKEND_SERVICE -n 40 --no-pager"
  exit 1
fi

echo ""
echo "=========================================="
echo "  Deploy complete! ✓"
echo "=========================================="
