"""
core.auth — Django port of the Flask-Login layer in app.py (lines 1204-1318).
Session-based auth against the users table in deleqate_v2.db, including the
M-2 session_version check (password reset invalidates older sessions) and
the B-07 CSRF token helpers.
"""
import secrets
from functools import wraps

from django.http import JsonResponse

from .database import get_db


class User:
    is_authenticated = True

    def __init__(self, id, email, name, role, phone=''):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.phone = phone


class AnonymousUser:
    is_authenticated = False
    id = None
    email = name = role = phone = ''


def load_user(request):
    """Port of @login_manager.user_loader — resolves the session to a User,
    enforcing the per-user session_version (M-2)."""
    user_id = request.session.get('_user_id')
    if not user_id:
        return AnonymousUser()
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if row:
        try:
            db_sv = row['session_version'] or 0
        except (IndexError, KeyError):
            db_sv = 0
        if request.session.get('_sv', 0) != db_sv:
            return AnonymousUser()
        return User(row['id'], row['email'], row['name'], row['role'], row['phone'])
    return AnonymousUser()


def do_login(request, row):
    """Port of _do_login — logs the user in and pins the session to the
    user's current session_version."""
    request.session.cycle_key()          # session fixation protection
    request.session['_user_id'] = row['id']
    try:
        request.session['_sv'] = row['session_version'] or 0
    except (IndexError, KeyError):
        request.session['_sv'] = 0


def do_logout(request):
    request.session.flush()


def login_required(f):
    @wraps(f)
    def wrapped(request, *args, **kwargs):
        request.user = load_user(request)
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'login_required', 'login_url': '/login'}, status=401)
        return f(request, *args, **kwargs)
    return wrapped


def role_required(*roles):
    """Port of role_required — 403 JSON instead of flash+redirect (React
    frontend handles the redirect)."""
    def decorator(f):
        @wraps(f)
        def wrapped(request, *args, **kwargs):
            request.user = load_user(request)
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'login_required', 'login_url': '/login'}, status=401)
            if request.user.role not in roles:
                return JsonResponse({'error': 'Access denied.'}, status=403)
            return f(request, *args, **kwargs)
        return wrapped
    return decorator


def dashboard_for(role):
    """Port of dashboard_for — returns the frontend path for each role."""
    return {'admin': '/admin/dashboard', 'pilot': '/pilot/dashboard',
            'client': '/client/orders'}.get(role, '/')


# ── B-07: CSRF token ──────────────────────────────────────
def get_csrf_token(request):
    if '_csrf_token' not in request.session:
        request.session['_csrf_token'] = secrets.token_hex(32)
    return request.session['_csrf_token']
