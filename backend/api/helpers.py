"""
api.helpers — shared plumbing for the ported views.
The Flask app rendered templates and used flash+redirect; the React
frontend instead receives JSON:  {ok, flash:[{cat,msg}], redirect, ...}.
All business behavior (validation order, messages, status codes) is kept
identical to app.py.
"""
import json

from django.http import JsonResponse


def body(request):
    """request JSON body (or empty dict) — port of request.get_json()."""
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body or b'{}') or {}
        except Exception:
            return {}
    return {}


def form(request, key, default=''):
    """Form field from either multipart/urlencoded POST or JSON body."""
    if key in request.POST:
        return request.POST.get(key, default)
    return body(request).get(key, default)


def ok(payload=None, flash=None, redirect=None, status=200):
    d = dict(payload or {})
    d.setdefault('ok', True)
    if flash:
        d['flash'] = [{'category': c, 'message': m} for c, m in flash]
    if redirect:
        d['redirect'] = redirect
    return JsonResponse(d, status=status)


def err(message, status=400, category='error', redirect=None, **extra):
    d = {'ok': False, 'error': message,
         'flash': [{'category': category, 'message': message}]}
    if redirect:
        d['redirect'] = redirect
    d.update(extra)
    return JsonResponse(d, status=status)
