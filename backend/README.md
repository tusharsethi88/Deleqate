# Deleqate — Django Backend (port of app.py)

This is a faithful port of the Flask app (`app.py`, `security.py`,
`autopilot_routes.py`) to Django, restructured for readability:

```
backend/
  manage.py
  config/          Django settings, URL map (all 90+ original routes), WSGI
  core/
    business.py    VERBATIM business logic: pricing, PayU hashing, reel/prompt engines
    database.py    VERBATIM raw-sqlite3 DB layer: get_db, init_db + all migrations,
                   SKU seeding, AutoPilot auto-assign worker  (same deleqate_v2.db file)
    vs_prompts.py  VERBATIM virtual-staging prompt engine (Gemini + Google Flow)
    security.py    Security layer port: rate limiting, brute-force bans, sanitizers,
                   path-traversal-safe file serving
    auth.py        Session auth (roles, session_version invalidation, CSRF token)
    middleware.py  Security headers + global CSRF enforcement (H-1)
  api/
    helpers.py     JSON response helpers ({ok, flash, redirect})
    views/         auth, public, orders, pilot, pilot_extra, client, admin,
                   payments, autopilot — one module per feature area
```

**The business data stays in the existing `../deleqate_v2.db`** (raw SQL,
unchanged schema). Django's own DB (`django_sessions.db`) holds sessions only.

## What changed for the frontend

Routes are identical, but page routes now return **JSON** (the data the old
Jinja template received) instead of HTML — built for a React frontend.
POST flows return `{ok, flash:[...], redirect:'/path'}` instead of
flash+redirect. All `/api/*` endpoints behave exactly as before
(PayU callbacks, AutoPilot token endpoints, pilot/admin JSON APIs).

Frontend contract notes:
- `GET /api/session` → `{authenticated, user, csrf_token}` — call once at app load.
- Send the CSRF token on every POST as `X-CSRFToken` header (or `csrf_token` field).
- Send cookies (`credentials: 'include'`) — auth is session-based, same as before.
- `/payment/initiate?order_id=N` returns the PayU form fields; the React page
  renders a hidden form and auto-submits it to `payu_url` (same as the old
  `payment_initiate.html`).

## Run locally (Windows / VS Code)

```powershell
cd D:\Deleqate\backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate          # creates django_sessions.db (sessions only)
python manage.py runserver 0.0.0.0:5051
```

API now at http://localhost:5051 (same port the Flask app used).

## Oracle VM deployment notes (your original problem)

The network/database errors you hit are almost always these — check each:

1. **Bind address**: run gunicorn with `-b 0.0.0.0:5051`, not 127.0.0.1.
2. **Oracle Cloud Security List**: add an ingress rule for TCP 5051 (or 80/443)
   in the VCN subnet's security list — the OS firewall is not enough.
3. **OS firewall**: `sudo iptables -I INPUT -p tcp --dport 5051 -j ACCEPT`
   (Oracle's Ubuntu images ship restrictive iptables rules by default).
4. **SQLite locking**: keep `gunicorn --workers 1` (or move to PostgreSQL later) —
   multiple workers writing to SQLite over a slow disk causes "database is locked".
   WAL mode is already enabled by `get_db()`.
5. **File ownership**: the user running gunicorn must own `deleqate_v2.db`,
   `uploads/`, and `deliverables/` (a `.db` owned by root after a sudo run is a
   classic cause of "unable to open database file").

Production start:

```bash
export FLASK_ENV=production DELEQATE_SECRET_KEY=... DELEQATE_ADMIN_PASSWORD=... \
       PAYU_KEY=... PAYU_SALT=... FRONTEND_URL=https://yourdomain.com
gunicorn config.wsgi:application -b 0.0.0.0:5051 --workers 1 --timeout 120
```

## Status

- ✅ Backend: all routes ported (auth, OTP, signup, password reset, order wizard
  submission for all 16 SKUs, pilot workflow, admin QC/SKU/payments, PayU
  initiate/success/failure with H-2 idempotency, AutoPilot API, file serving
  with C-4 access rules, rate limiting, CSRF, security headers).
- ⬜ React frontend: not yet built (next phase — the 23 templates,
  ~13,700 lines, will be converted page by page; the old Flask app remains
  fully usable meanwhile).
