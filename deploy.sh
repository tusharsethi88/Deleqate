#!/bin/bash
# ──────────────────────────────────────────────────────────────
#  Deleqate — Auto Deploy Script  (Django backend + React frontend)
#  Run ON THE SERVER:  bash deploy.sh
#  Pulls latest code from GitHub, rebuilds both halves, restarts.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/home/ubuntu/deleqate"   # repo root on the server
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

# 2. Check and prepare configuration files
echo ""
echo "▶ Checking configuration files..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
  echo "✗ Missing backend/.env. Generating a template..."
  cat <<EOT > "$APP_DIR/backend/.env"
DJANGO_ENV=production
DELEQATE_SECRET_KEY=$(head -c 32 /dev/urandom | base64 | tr -d '+/')
DELEQATE_ADMIN_PASSWORD=change-me-promptly
ALLOWED_HOSTS=api.deleqate.com
CORS_ORIGINS=https://deleqate.com,https://www.deleqate.com
FRONTEND_URL=https://deleqate.com
BREVO_API_KEY=
FROM_EMAIL=
PAYU_KEY=
PAYU_SALT=
PAYU_URL=https://secure.payu.in/_payment
SUPPORT_WHATSAPP=917011989292
SUPPORT_UPI=deleqate@upi
EOT
  echo "  → Created /home/ubuntu/deleqate/backend/.env template."
  echo "  → Please edit this file with your production keys/domains, then re-run deploy.sh."
  exit 1
fi

if [ ! -f "$APP_DIR/frontend/.env.production" ]; then
  echo "✗ Missing frontend/.env.production. Generating template..."
  echo "VITE_API_BASE=https://api.deleqate.com" > "$APP_DIR/frontend/.env.production"
  echo "  → Created /home/ubuntu/deleqate/frontend/.env.production template."
fi

# 3. Sync Systemd and Nginx Configurations
echo ""
echo "▶ Syncing systemd and Nginx configuration files..."
sudo cp "$APP_DIR/deploy/deleqate.service" /etc/systemd/system/deleqate.service
sudo systemctl daemon-reload
sudo systemctl enable deleqate

sudo cp "$APP_DIR/deploy/nginx-deleqate.conf" /etc/nginx/conf.d/deleqate.conf
if [ -f /etc/nginx/sites-enabled/default ]; then
  echo "Disabling default Nginx site configuration..."
  sudo rm -f /etc/nginx/sites-enabled/default
fi
echo "✓ System configurations synced."

# 4. Backend — Django (venv + deps + session migrations)
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

# 5. Frontend — React (install + production build into frontend/dist)
echo ""
echo "▶ Frontend: building production bundle..."
cd "$APP_DIR/frontend"
if command -v npm >/dev/null 2>&1; then
  npm ci 2>/dev/null || npm install
  npm run build
else
  echo "✗ npm not found. Install Node.js 18+ on the server first." >&2
  exit 1
fi
cd "$APP_DIR"
echo "✓ Frontend built → frontend/dist"

# 6. Restart services
echo ""
echo "▶ Restarting services..."
sudo systemctl restart "$BACKEND_SERVICE"
sudo systemctl reload nginx
sleep 2

# 7. Health check
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
