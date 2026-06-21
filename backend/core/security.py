"""
core.security — Django port of security.py (Deleqate Security Layer).
Same logic: sliding-window rate limiting, brute-force login tracker,
input sanitizers, path-traversal-safe file serving, honeypot, safe redirect.
Only the Flask request/response plumbing was swapped for Django's.
"""
import os, re, time, threading, unicodedata
from collections import defaultdict
from functools import wraps

from django.http import JsonResponse, FileResponse, Http404, HttpResponse


# ── 1. IN-MEMORY RATE LIMITER (verbatim logic) ─────────────
class _RateLimitStore:
    """Sliding-window hit counter keyed by (ip, endpoint)."""
    def __init__(self):
        self._lock = threading.Lock()
        self._hits = defaultdict(list)
        self._banned = {}

    def _key(self, ip, scope):
        return f"{ip}:{scope}"

    def is_banned(self, ip, scope):
        k = self._key(ip, scope)
        with self._lock:
            until = self._banned.get(k)
            if until and time.time() < until:
                return True
            if until:
                del self._banned[k]
        return False

    def hit(self, ip, scope, limit, window_secs, ban_secs=0):
        k = self._key(ip, scope)
        now = time.time()
        with self._lock:
            self._hits[k] = [t for t in self._hits[k] if now - t < window_secs]
            count = len(self._hits[k])
            if count >= limit:
                if ban_secs > 0:
                    self._banned[k] = now + ban_secs
                remaining_reset = window_secs - (now - self._hits[k][0]) if self._hits[k] else window_secs
                return False, 0, int(remaining_reset)
            self._hits[k].append(now)
            return True, limit - count - 1, window_secs

    def clear(self, ip, scope):
        k = self._key(ip, scope)
        with self._lock:
            self._hits.pop(k, None)
            self._banned.pop(k, None)


_store = _RateLimitStore()

# H-4: X-Forwarded-For only trusted from configured proxies
_TRUSTED_PROXY_IPS = {
    ip.strip() for ip in os.environ.get('TRUSTED_PROXY_IPS', '').split(',') if ip.strip()
}


def get_client_ip(request):
    """Real client IP. Honours X-Forwarded-For ONLY when the direct peer
    is a trusted proxy; otherwise the header is ignored as spoofable."""
    remote = request.META.get('REMOTE_ADDR') or '0.0.0.0'
    if _TRUSTED_PROXY_IPS and remote in _TRUSTED_PROXY_IPS:
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            ip = xff.split(',')[-1].strip()
            if re.match(r'^[\d\.:a-fA-F]+$', ip):
                return ip
    return remote


def rate_limit(limit, window, ban_secs=0, scope=None, json_response=False):
    """Decorator for Django views: def view(request, ...)."""
    def decorator(f):
        @wraps(f)
        def wrapped(request, *args, **kwargs):
            ip = get_client_ip(request)
            key = scope or f.__name__

            if _store.is_banned(ip, key):
                return JsonResponse({'error': 'Too many requests. Try again later.'}, status=429)

            allowed, remaining, reset_in = _store.hit(ip, key, limit, window, ban_secs)
            if not allowed:
                resp = JsonResponse({'error': 'Rate limit exceeded. Try again later.'}, status=429)
                resp['Retry-After'] = str(reset_in)
                return resp
            return f(request, *args, **kwargs)
        return wrapped
    return decorator


def clear_rate_limit(ip, scope):
    _store.clear(ip, scope)


# ── 2. SECURITY HEADERS (used by core.middleware) ─────────
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

PERMISSIONS_POLICY = (
    "geolocation=(), microphone=(), camera=(), payment=(), usb=(), fullscreen=(self)"
)


def apply_security_headers(request, response):
    h = response
    h['X-Content-Type-Options'] = 'nosniff'
    h['X-Frame-Options'] = 'DENY'
    h['X-XSS-Protection'] = '1; mode=block'
    h['Content-Security-Policy'] = CSP
    h['Permissions-Policy'] = PERMISSIONS_POLICY
    h['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    h['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    if response.status_code in (200, 201) and not (
        request.path.startswith('/static/') or
        request.path.startswith('/uploads/') or
        request.path.startswith('/deliverables/') or
        request.path == '/'
    ):
        h['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        h['Pragma'] = 'no-cache'
    if 'Server' in response:
        del response['Server']
    return response


# ── 3. INPUT SANITIZER (verbatim) ──────────────────────────
_DANGEROUS_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_text(value, max_length=2000, allow_newlines=True):
    if value is None:
        return ''
    value = str(value)
    value = unicodedata.normalize('NFC', value)
    value = _DANGEROUS_CHARS.sub('', value)
    if not allow_newlines:
        value = value.replace('\n', ' ').replace('\r', ' ')
    value = value[:max_length]
    return value.strip()


def sanitize_email(value):
    if not value:
        return ''
    v = value.strip().lower()[:254]
    if re.match(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$', v):
        return v
    return ''


def sanitize_phone(value):
    if not value:
        return ''
    v = re.sub(r'\D', '', str(value))
    if v.startswith('91') and len(v) == 12:
        v = v[2:]
    if re.match(r'^[6-9]\d{9}$', v):
        return v
    return ''


def sanitize_filename_input(value):
    from werkzeug.utils import secure_filename
    return secure_filename(str(value or ''))[:200]


# ── 4. PATH TRAVERSAL GUARD ────────────────────────────────
def safe_serve_file(folder, filename, as_attachment=False):
    """Serve `filename` from `folder` with strict path-traversal check."""
    real_folder = os.path.realpath(folder)
    candidate = os.path.realpath(os.path.join(folder, filename))
    if not candidate.startswith(real_folder + os.sep) and candidate != real_folder:
        raise Http404
    if not os.path.isfile(candidate):
        raise Http404
    return FileResponse(open(candidate, 'rb'), as_attachment=as_attachment,
                        filename=os.path.basename(candidate))


# ── 5. BRUTE-FORCE LOGIN TRACKER (verbatim) ────────────────
_login_failures = defaultdict(list)
_login_lock = threading.Lock()
_LOGIN_WINDOW = 600
_LOGIN_LIMIT = 10
_LOGIN_BAN = 1800


def record_login_failure(ip):
    now = time.time()
    with _login_lock:
        _login_failures[ip] = [t for t in _login_failures[ip] if now - t < _LOGIN_WINDOW]
        _login_failures[ip].append(now)
        if len(_login_failures[ip]) >= _LOGIN_LIMIT:
            _store._banned[f"{ip}:login"] = now + _LOGIN_BAN
            _login_failures[ip] = []


def clear_login_failures(ip):
    with _login_lock:
        _login_failures.pop(ip, None)
    _store.clear(ip, 'login')


def is_login_banned(ip):
    return _store.is_banned(ip, 'login')


# ── 6. HONEYPOT FIELD HELPER ───────────────────────────────
def honeypot_triggered(request):
    return bool(request.POST.get('website', '').strip())


# ── 7. SAFE REDIRECT ───────────────────────────────────────
def safe_redirect_url(request, target, fallback='/'):
    from urllib.parse import urlparse, urljoin
    if not target:
        return fallback
    host_url = request.build_absolute_uri('/')
    joined = urljoin(host_url, target)
    parsed = urlparse(joined)
    req_host = urlparse(host_url).netloc
    if parsed.netloc and parsed.netloc != req_host:
        return fallback
    return joined
