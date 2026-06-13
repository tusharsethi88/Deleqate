"""
Minimal Jinja2 renderer for reusing the original Flask templates verbatim
(e.g. pilot_sku_workflow.html — the full pilot execution workflow).

The templates only need a handful of Flask globals: csrf_token(), url_for()
for 'logout'/'static', current_user, and get_flashed_messages(). We provide
those here so the rich workflow renders identically to the old app without a
React rewrite.
"""
import jinja2
from django.conf import settings

from core.auth import get_csrf_token
from core.business import FRONTEND_URL

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(settings.PROJECT_ROOT / 'templates')),
    autoescape=jinja2.select_autoescape(['html', 'xml']),
)


def _url_for(endpoint, **kw):
    if endpoint == 'logout':
        # send the pilot back to the React app to log out (clears session there)
        return (FRONTEND_URL or '').rstrip('/') + '/logout'
    if endpoint == 'static':
        return '/static/' + kw.get('filename', '')
    if endpoint == 'pilot_execute':
        return f"/pilot/execute/{kw.get('order_id', '')}"
    if endpoint == 'pilot_job':
        return f"/pilot/job/{kw.get('order_id', '')}"
    return '/'


def render_flask_template(template_name, request, **context):
    """Render a legacy Flask/Jinja template to an HTML string."""
    tmpl = _env.get_template(template_name)
    context.setdefault('url_for', _url_for)
    context.setdefault('csrf_token', lambda: get_csrf_token(request))
    context.setdefault('get_flashed_messages', lambda *a, **k: [])
    context.setdefault('current_user', getattr(request, 'user', None))
    # Frontend base (React app) for links/redirects that must leave the API host
    context.setdefault('frontend_url', (FRONTEND_URL or '').rstrip('/'))
    return tmpl.render(**context)
