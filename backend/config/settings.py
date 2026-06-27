"""
Deleqate backend — Django settings.
Faithful port of the Flask app's configuration (app.py lines 85-183).
The app keeps using the existing SQLite file (deleqate_v2.db) via raw
sqlite3 (core.database.get_db), exactly like the Flask version.
Django's own DATABASES entry is used only for sessions.
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
PROJECT_ROOT = BASE_DIR.parent                              # D:\Deleqate (where deleqate_v2.db, uploads/, deliverables/ live)
load_dotenv(PROJECT_ROOT / '.env')

IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('DJANGO_ENV') == 'production'

SECRET_KEY = os.environ.get('DELEQATE_SECRET_KEY', 'deleqate-v2-secret-2026')
if SECRET_KEY == 'deleqate-v2-secret-2026':
    if IS_PRODUCTION:
        raise SystemExit('FATAL: DELEQATE_SECRET_KEY not set. Refusing to start in production with the default secret key.')
    print('⚠ WARNING: DELEQATE_SECRET_KEY not set — using insecure default. Add to .env before deploying.', file=sys.stderr)

DEBUG = not IS_PRODUCTION
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.SPAMiddleware',               # serve React SPA for browser GET navigation
    'core.middleware.SecurityHeadersMiddleware',   # port of security.apply_security_headers
    'core.middleware.CsrfTokenMiddleware',         # port of Flask _global_csrf_check (H-1)
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = []

# Django DB — used ONLY for Django sessions; business data stays in
# deleqate_v2.db accessed through core.database.get_db (raw sqlite3).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': PROJECT_ROOT / 'django_sessions.db',
    }
}

# ── SESSION & COOKIE HARDENING (parity with Flask config) ──
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_AGE = 3600          # 1-hour idle timeout
SESSION_SAVE_EVERY_REQUEST = True  # idle timeout behaviour like Flask
SESSION_COOKIE_NAME = '__Host-session' if IS_PRODUCTION else 'session'

# ── FILE / REQUEST LIMITS ──
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024   # 100 MB hard cap
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
UPLOAD_FOLDER       = str(PROJECT_ROOT / 'uploads')
DELIVERABLES_FOLDER = str(PROJECT_ROOT / 'deliverables')

# ── CORS: allow the React dev server ──
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get(
    'CORS_ORIGINS', 'http://localhost:5183,http://127.0.0.1:5183,http://localhost:8061,http://127.0.0.1:8061').split(',') if o]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['accept', 'content-type', 'x-csrftoken', 'x-requested-with', 'x-autopilot-token']

STATIC_URL = '/static/'
STATICFILES_DIRS = [PROJECT_ROOT / 'static']

USE_TZ = False
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
APPEND_SLASH = False
X_FRAME_OPTIONS = 'SAMEORIGIN'
