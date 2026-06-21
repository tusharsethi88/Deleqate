"""
core.middleware — Django middleware ports of:
  • security.apply_security_headers  (every response)
  • app.py _global_csrf_check (H-1)  (every state-changing request)
  • SPAMiddleware — serve React index.html for browser GET navigation
"""
import hmac
import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse

from .security import apply_security_headers

# ── SPA shell (read once at startup) ─────────────────────────────────────────
_SPA_INDEX = (Path(settings.PROJECT_ROOT) / 'frontend' / 'dist' / 'index.html').read_text(encoding='utf-8')

# Prefixes that should NEVER be intercepted — served as-is by their own handlers
_PASSTHROUGH_PREFIXES = (
    '/api/', '/static/', '/assets/', '/css/', '/img/',
    '/uploads/', '/deliverables/', '/robots.txt', '/sitemap.xml',
    '/.well-known/', '/payment/', '/pilot/', '/logo-showroom',
)


class SPAMiddleware:
    """Serve the React SPA shell for all browser GET navigation.

    A direct browser visit to any page route (e.g. /login, /dq-control-7x9k)
    sends Accept: text/html. We intercept those GETs and return index.html so
    React Router takes over. POST/PUT/DELETE requests and asset paths pass
    through unchanged.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method == 'GET'
                and 'text/html' in request.META.get('HTTP_ACCEPT', '')
                and not any(request.path.startswith(p) for p in _PASSTHROUGH_PREFIXES)):
            return HttpResponse(_SPA_INDEX, content_type='text/html')
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return apply_security_headers(request, response)


# Paths exempt from CSRF — parity with CSRF_EXEMPT_ENDPOINTS in app.py.
# PayU browser callbacks are authenticated by reverse hash; AutoPilot
# endpoints authenticate via X-AutoPilot-Token header.
CSRF_EXEMPT_PREFIXES = (
    '/payment/success', '/payment/failure',
    '/api/autopilot/deliver/', '/api/autopilot/qc_pass/', '/api/autopilot/qc_fail/',
    '/api/autopilot/heartbeat', '/api/autopilot/spatial/',
)


class CsrfTokenMiddleware:
    """Port of @app.before_request _global_csrf_check (H-1):
    every POST/PUT/PATCH/DELETE must carry the session CSRF token via
    X-CSRFToken header, csrf_token form field, or JSON body key."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            path = request.path
            if not any(path.startswith(p) or path == p.rstrip('/') for p in CSRF_EXEMPT_PREFIXES):
                token = request.headers.get('X-CSRFToken') or request.POST.get('csrf_token')
                if not token and request.content_type == 'application/json':
                    try:
                        token = (json.loads(request.body or b'{}') or {}).get('csrf_token')
                    except Exception:
                        token = None
                expected = request.session.get('_csrf_token', '')
                if not token or not expected or not hmac.compare_digest(str(token), str(expected)):
                    return JsonResponse({'error': 'CSRF validation failed'}, status=403)
        return self.get_response(request)
