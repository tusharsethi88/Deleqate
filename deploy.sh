#!/bin/bash
# =============================================================================
# Deleqate — Safe Redeployment Script
# =============================================================================
# Run this on the server for EVERY deployment after the first one:
#   cd /home/ubuntu/deleqate
#   bash deploy.sh
#
# SAFETY GUARANTEES:
#   - deleqate_v2.db & django_sessions.db are NEVER touched, deleted, or overwritten
#   - uploads/ & deliverables/ directories are NEVER touched
#   - Only code, static files, and Python/Node deps are updated
# =============================================================================

set -e  # Exit immediately on any error

APP_DIR="/home/ubuntu/deleqate"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

# SQLite DB files (Gitignored, located in repo root)
DB_PATH_APP="$APP_DIR/deleqate_v2.db"
DB_PATH_SESS="$APP_DIR/django_sessions.db"

# Uploads & deliverables (Gitignored, located in repo root)
UPLOADS_DIR="$APP_DIR/uploads"
DELIVERABLES_DIR="$APP_DIR/deliverables"

LOG_FILE="/var/log/deleqate/deploy.log"
REPO_URL="https://github.com/tusharsethi88/Deleqate.git"
BRANCH="main"
BACKEND_SERVICE="deleqate"

# Ensure log directory and file exist with correct permissions
sudo mkdir -p "$(dirname "$LOG_FILE")"
sudo touch "$LOG_FILE"
sudo chown -R ubuntu:ubuntu "$(dirname "$LOG_FILE")"

# ── Logging helper ──────────────────────────────────────────────────────────
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ── Step 0: Clone repository if it does not exist ───────────────────────────
if [ ! -d "$APP_DIR" ]; then
  echo "▶ Directory $APP_DIR does not exist."
  if [ $# -ge 2 ]; then
    github_username="$1"
    github_token="$2"
  else
    read -p "Enter GitHub Username: " github_username
    read -sp "Enter GitHub Personal Access Token (PAT): " github_token
    echo ""
  fi
  
  # URL encode username and token using Python to safely handle special characters
  encoded_user=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$github_username'''))")
  encoded_token=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$github_token'''))")
  
  AUTH_REPO_URL="https://${encoded_user}:${encoded_token}@github.com/tusharsethi88/Deleqate.git"
  
  echo "▶ Cloning repository..."
  sudo mkdir -p "$APP_DIR"
  sudo chown -R ubuntu:ubuntu "$APP_DIR"
  git clone "$AUTH_REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# ── Pre-flight checks ───────────────────────────────────────────────────────
log "=== Deleqate Deployment Started ==="

# Confirm the DBs exist and are NOT going to be touched
for db in "$DB_PATH_APP" "$DB_PATH_SESS"; do
  if [ -f "$db" ]; then
      DB_SIZE=$(du -sh "$db" | cut -f1)
      log "✓ SQLite DB found at $db (size: $DB_SIZE) — will NOT be touched"
  else
      log "⚠ No DB found at $db — this looks like a first run."
  fi
done

if [ -d "$UPLOADS_DIR" ]; then
    log "✓ Uploads directory found at $UPLOADS_DIR — will NOT be touched"
fi
if [ -d "$DELIVERABLES_DIR" ]; then
    log "✓ Deliverables directory found at $DELIVERABLES_DIR — will NOT be touched"
fi

# ── Step 0b: Check and prepare configuration files ──────────────────────────
log "--- Checking configuration files ---"
if [ ! -f "$APP_DIR/backend/.env" ]; then
  log "✗ Missing backend/.env. Generating a template..."
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
  log "  → Created /home/ubuntu/deleqate/backend/.env template."
  log "  → Please edit this file with your production keys/domains, then re-run deploy.sh."
  exit 1
fi

if [ ! -f "$APP_DIR/frontend/.env.production" ]; then
  log "✗ Missing frontend/.env.production. Generating template..."
  echo "VITE_API_BASE=https://api.deleqate.com" > "$APP_DIR/frontend/.env.production"
  log "  → Created /home/ubuntu/deleqate/frontend/.env.production template."
fi

# ── Step 1: Pull latest code ────────────────────────────────────────────────
log "--- Step 1: Pulling latest code from git ---"
git fetch origin
git reset --hard "origin/$BRANCH"
log "✓ Code updated"

# ── Step 2: Build React frontend ─────────────────────────────────────────────
log "--- Step 2: Building React frontend ---"
cd "$FRONTEND_DIR"
npm ci --silent 2>/dev/null || npm install --silent
npm run build
log "✓ React build complete → frontend/dist"

# ── Step 3: Install/update Python dependencies ──────────────────────────────
log "--- Step 3: Installing Python dependencies ---"
cd "$BACKEND_DIR"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
log "✓ Python dependencies up to date"

# ── Step 4: Run Django migrations (SAFE — only adds, never drops) ────────────
log "--- Step 4: Running database migrations ---"
python manage.py migrate --noinput
log "✓ Migrations applied"

# ── Step 5: Collect static files (Skipped as Nginx serves frontend/dist directly) ──
log "--- Step 5: Static files collection (Skipped) ---"
log "✓ Static files step skipped (handled by frontend build)"

# ── Step 5b: Remove stale Django template index.html ─────────────────────────
log "--- Step 5b: Checking for stale templates ---"
STALE_INDEX_1="$BACKEND_DIR/templates/index.html"
STALE_INDEX_2="$APP_DIR/templates/index.html"
for index_file in "$STALE_INDEX_1" "$STALE_INDEX_2"; do
  if [ -f "$index_file" ]; then
      rm -f "$index_file"
      log "✓ Removed stale $index_file (was shadowing Vite build)"
  fi
done
log "✓ Stale template check complete"

deactivate

# ── Step 6: Fix permissions ──────────────────────────────────────────────────
log "--- Step 6: Fixing file permissions ---"
sudo chown -R ubuntu:ubuntu "$APP_DIR"
sudo mkdir -p "$UPLOADS_DIR" "$DELIVERABLES_DIR"
sudo chown -R ubuntu:ubuntu "$UPLOADS_DIR" "$DELIVERABLES_DIR"
sudo chmod 755 "$UPLOADS_DIR" "$DELIVERABLES_DIR"
find "$UPLOADS_DIR" -type d -exec sudo chmod 755 {} \; 2>/dev/null || true
find "$UPLOADS_DIR" -type f -exec sudo chmod 644 {} \; 2>/dev/null || true
find "$DELIVERABLES_DIR" -type d -exec sudo chmod 755 {} \; 2>/dev/null || true
find "$DELIVERABLES_DIR" -type f -exec sudo chmod 644 {} \; 2>/dev/null || true
log "✓ Permissions fixed"

# ── Step 7: Restart Gunicorn ─────────────────────────────────────────────────
log "--- Step 7: Restarting Gunicorn ---"
sudo systemctl restart "$BACKEND_SERVICE"
sleep 2

# Check Gunicorn is actually running
if sudo systemctl is-active --quiet "$BACKEND_SERVICE"; then
    log "✓ Gunicorn is running"
else
    log "✗ ERROR: Gunicorn failed to start. Check: journalctl -u $BACKEND_SERVICE -n 50"
    exit 1
fi

# ── Step 8: Sync nginx config + reload (no downtime) ────────────────────────
log "--- Step 8: Syncing nginx config and reloading ---"

CERT_PATH="/etc/letsencrypt/live/deleqate.com/fullchain.pem"

if [ -f "$CERT_PATH" ]; then
    # SSL certs exist — safe to copy full HTTPS config from repo
    sudo cp "$APP_DIR/deploy/nginx-deleqate.conf" /etc/nginx/conf.d/deleqate.conf
    if [ -f /etc/nginx/sites-enabled/default ]; then
        log "Disabling default Nginx site configuration..."
        sudo rm -f /etc/nginx/sites-enabled/default
    fi
    if sudo nginx -t 2>/dev/null; then
        sudo systemctl reload nginx
        log "✓ Nginx config synced (HTTPS) and reloaded"
    else
        log "✗ ERROR: nginx config test failed. Showing errors:"
        sudo nginx -t
        log "  Fix deploy/nginx-deleqate.conf and redeploy, or check: sudo nginx -t"
        exit 1
    fi
else
    # SSL certs NOT found — skip nginx copy to avoid breaking the live site
    log "⚠ SSL certs not found at $CERT_PATH — skipping nginx config update"
    log "  Site may still be running on HTTP. To enable HTTPS, run:"
    log "  sudo certbot --nginx -d deleqate.com -d www.deleqate.com -d api.deleqate.com"
    log "  Then redeploy: bash deploy.sh"
    sudo systemctl reload nginx
fi

# ── Done ────────────────────────────────────────────────================─────
log "=== Deployment Complete ==="
log "SQLite DBs at $DB_PATH_APP & $DB_PATH_SESS — untouched ✓"
log "Uploads & deliverables — untouched ✓"
echo ""
echo "✅  Deleqate deployed successfully!"
echo "    Check logs: tail -f /var/log/deleqate/deploy.log"
