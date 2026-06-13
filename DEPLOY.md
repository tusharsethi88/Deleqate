# Deleqate — Deployment Guide

Stack: **Django** backend (gunicorn, port 5051) + **React/Vite** frontend (static build, served by nginx). SQLite database. Hosted on an Oracle Cloud VM (user `opc`).

> Frontend and backend run on **two hostnames** (`deleqate.com` and `api.deleqate.com`) because they share route names (`/order`, `/login`, `/admin`). HTTPS is required (production uses a secure `__Host-` session cookie).

---

## A. One-time: push code to GitHub (from your PC)

```bash
cd D:\Deleqate
git init                       # only if not already a repo
git add .
git commit -m "Deleqate: Django + React migration"
git branch -M main
git remote add origin https://github.com/<you>/deleqate.git
git push -u origin main
```

`node_modules/`, `*.db`, `.env`, `uploads/`, `deliverables/`, and `frontend/dist/` are gitignored — they are **not** pushed.

For later updates, just:

```bash
git add . && git commit -m "..." && git push
```

---

## B. One-time: server setup

```bash
ssh opc@<server-ip>

# 1. System deps
sudo dnf install -y git nginx python3 python3-pip
# Node 18+ (for the frontend build)
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs

# 2. Clone the repo
sudo mkdir -p /home/opc/deleqate && sudo chown opc:opc /home/opc/deleqate
git clone https://github.com/<you>/deleqate.git /home/opc/deleqate
cd /home/opc/deleqate

# 3. Create the backend .env  (secrets — never committed)
nano .env
```

Put your real values in `.env`:

```ini
DJANGO_ENV=production
DELEQATE_SECRET_KEY=<64-char-random>
DELEQATE_ADMIN_PASSWORD=<admin-password>
ALLOWED_HOSTS=api.deleqate.com
CORS_ORIGINS=https://deleqate.com,https://www.deleqate.com
FRONTEND_URL=https://deleqate.com          # PayU redirects back here
BREVO_API_KEY=<your-brevo-key>
FROM_EMAIL=noreply@deleqate.com            # verified sender in Brevo
PAYU_KEY=<payu-key>
PAYU_SALT=<payu-salt>
PAYU_URL=https://secure.payu.in/_payment   # live URL (test.payu.in for sandbox)
SUPPORT_WHATSAPP=917011989292
SUPPORT_UPI=deleqate@upi
```

```bash
# 4. Frontend build target (which API host the browser calls)
echo "VITE_API_BASE=https://api.deleqate.com" > /home/opc/deleqate/frontend/.env.production

# 5. Install the systemd service (gunicorn) and nginx config
sudo cp deploy/deleqate.service /etc/systemd/system/deleqate.service
sudo cp deploy/nginx-deleqate.conf /etc/nginx/conf.d/deleqate.conf
sudo systemctl daemon-reload
sudo systemctl enable deleqate
```

---

## C. First build + start

```bash
cd /home/opc/deleqate
bash deploy.sh        # builds backend + frontend, starts the service
sudo nginx -t && sudo systemctl restart nginx
```

### HTTPS (run once)

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d deleqate.com -d www.deleqate.com -d api.deleqate.com
```

Point DNS `A` records for `deleqate.com`, `www`, and `api` at the server IP, and open ports 80/443 in the Oracle security list + `firewall-cmd`.

---

## D. Every future deploy

After `git push` from your PC:

```bash
ssh opc@<server-ip>
cd /home/opc/deleqate
bash deploy.sh
```

`deploy.sh` pulls the latest code, reinstalls backend deps + runs session migrations, rebuilds the frontend, and restarts gunicorn + reloads nginx. Your `.env`, database, and uploaded files are left untouched.

---

## Troubleshooting

```bash
sudo journalctl -u deleqate -n 50 --no-pager   # backend logs
sudo tail -n 50 /var/log/nginx/error.log        # nginx logs
systemctl is-active deleqate                     # should print "active"
```

- **Login works but session drops** → ensure HTTPS is live (the `__Host-` cookie needs `Secure`) and `CORS_ORIGINS` matches the exact frontend URL.
- **OTP email not arriving** → `BREVO_API_KEY` set and `FROM_EMAIL` verified in Brevo.
- **Uploads fail** → raise `client_max_body_size` in nginx.
