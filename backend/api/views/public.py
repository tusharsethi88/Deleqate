"""
api.views.public — port of app.py public routes (lines 1329-1536, 1376-1430,
1980-1993): homepage data, robots.txt, sitemap.xml, policy pages,
security.txt, hero image server, pricing API.
"""
import os, hashlib

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.views.decorators.http import require_POST

from core.database import get_db, PRICING_MAP
from core.security import rate_limit
from core.business import SUPPORT_WHATSAPP, SPACE_TYPE_RENDER_DEFAULTS
from api.helpers import body, ok, err


def get_hero_video_url():
    """Return the URL of the uploaded hero video, or None if none exists."""
    upload_dir = settings.UPLOAD_FOLDER
    for ext in ('mp4', 'webm', 'mov', 'ogg'):
        fname = f'hero_video.{ext}'
        if os.path.exists(os.path.join(upload_dir, fname)):
            return f'/uploads/{fname}'
    return None


def get_hero_images():
    """Return (before_url, after_url) from a real delivered/approved order."""
    try:
        conn = get_db()
        order = conn.execute(
            """SELECT o.id FROM orders o
               INNER JOIN deliverables d ON d.order_id = o.id
               WHERE o.status IN ('delivered','approved','submitted')
               ORDER BY o.id DESC LIMIT 1"""
        ).fetchone()
        if not order:
            conn.close()
            return None, None
        oid = order['id']
        after_row = conn.execute(
            "SELECT filename FROM deliverables WHERE order_id=? AND filename NOT LIKE '%.mp4' AND filename NOT LIKE '%.webm' ORDER BY id ASC LIMIT 1",
            (oid,)
        ).fetchone()
        before_row = conn.execute(
            """SELECT filename FROM order_attachments
               WHERE order_id=?
               AND (attachment_type IN ('room_photo','property_photo','general')
                    OR attachment_type NOT LIKE '%moodboard%')
               AND filename NOT LIKE '%.mp4' AND filename NOT LIKE '%.webm'
               AND filename NOT LIKE '%.pdf'
               ORDER BY id ASC LIMIT 1""",
            (oid,)
        ).fetchone()
        conn.close()
        after_url = f'/api/hero-img/after/{after_row["filename"]}' if after_row else None
        before_url = f'/api/hero-img/before/{before_row["filename"]}' if before_row else None
        return before_url, after_url
    except Exception:
        return None, None


# ── / homepage data (app.py 1432-1441) ─────────────────────
def index_data(request):
    conn = get_db()
    inactive_tasks = [r['task_key'] for r in conn.execute('SELECT task_key FROM skus WHERE is_active=0').fetchall()]
    conn.close()
    # curated static hero — bypasses DB-driven get_hero_images() (parity)
    return ok({'inactive_tasks': inactive_tasks,
               'hero_video_url': get_hero_video_url(),
               'hero_before_url': None, 'hero_after_url': None})


# ── /robots.txt (app.py 1444-1462) ─────────────────────────
def robots_txt(request):
    host_url = request.build_absolute_uri('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /pilot/\n"
        "Disallow: /order/\n"
        "Disallow: /uploads/\n"
        "Disallow: /deliverables/\n"
        "Disallow: /verify-otp\n"
        "Disallow: /signup\n"
        "Disallow: /api/\n"
        "Crawl-delay: 2\n\n"
        f"Sitemap: {host_url}sitemap.xml\n"
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


# ── /sitemap.xml (app.py 1465-1487) ────────────────────────
def sitemap_xml(request):
    base = request.build_absolute_uri('/').rstrip('/')
    pages = [
        ('/', '1.0', 'weekly'),
        ('/login', '0.5', 'monthly'),
        ('/about', '0.7', 'monthly'),
        ('/terms', '0.4', 'yearly'),
        ('/privacy', '0.4', 'yearly'),
        ('/refund-policy', '0.4', 'yearly'),
        ('/shipping-policy', '0.4', 'yearly'),
    ]
    urls = '\n'.join(
        f'  <url><loc>{base}{path}</loc><priority>{pri}</priority><changefreq>{freq}</changefreq></url>'
        for path, pri, freq in pages
    )
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>'''
    return HttpResponse(xml, content_type='application/xml')


# ── POLICY PAGES (app.py 1492-1524) ────────────────────────
_POLICY_PAGES = {
    'about':    ('About Us', 'About Deleqate — an AI-powered services platform. Fixed-price virtual staging, product visuals, brand kits and more, delivered by vetted specialists.', '/about'),
    'terms':    ('Terms and Conditions', 'Terms and Conditions for using Deleqate — orders, pricing, payments, revisions and intellectual property.', '/terms'),
    'privacy':  ('Privacy Policy', 'How Deleqate collects, uses and protects your data. Essential cookies only, no data selling.', '/privacy'),
    'refund':   ('Refund & Cancellation Policy', 'Deleqate refund and cancellation policy — preview-first protection, full refund conditions, 5–7 business day processing via PayU.', '/refund-policy'),
    'shipping': ('Shipping & Delivery Policy', 'Deleqate delivers digital services only — all files delivered to your secure dashboard, typically within 1–6 hours.', '/shipping-policy'),
}


def policy_data(request, page):
    if page not in _POLICY_PAGES:
        raise Http404
    title, desc, path = _POLICY_PAGES[page]
    return ok({'page': page, 'page_title': title, 'page_desc': desc,
               'canonical_path': path, 'support_whatsapp': SUPPORT_WHATSAPP})


# ── /.well-known/security.txt (app.py 1527-1536) ───────────
def security_txt(request):
    content = (
        "Contact: mailto:security@deleqate.com\n"
        "Preferred-Languages: en\n"
        "Policy: https://deleqate.com/security-policy\n"
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


# ── /api/hero-img/<which>/<filename> (app.py 1376-1430) ────
@rate_limit(limit=60, window=60)
def hero_img(request, which, filename):
    """Public route for serving hero showcase images, upscaled to 1920x1080."""
    from PIL import Image as _PILImage

    folder = settings.DELIVERABLES_FOLDER if which == 'after' else settings.UPLOAD_FOLDER

    # M-1: traversal-safe path resolution
    real_folder = os.path.realpath(folder)
    src_path = os.path.realpath(os.path.join(folder, filename))
    if not src_path.startswith(real_folder + os.sep):
        raise Http404

    TARGET_W, TARGET_H = 1920, 1080

    cache_dir = os.path.join(settings.UPLOAD_FOLDER, 'hero_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_name = which + '_' + hashlib.md5(filename.encode()).hexdigest() + '.jpg'
    cache_path = os.path.join(cache_dir, cache_name)

    if not os.path.exists(cache_path):
        try:
            img = _PILImage.open(src_path).convert('RGB')
            src_w, src_h = img.size
            scale = max(TARGET_W / src_w, TARGET_H / src_h)
            new_w = int(src_w * scale)
            new_h = int(src_h * scale)
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)
            left = (new_w - TARGET_W) // 2
            top = max(0, int((new_h - TARGET_H) * 0.30))
            img = img.crop((left, top, left + TARGET_W, top + TARGET_H))
            img.save(cache_path, 'JPEG', quality=88, optimize=True, progressive=True)
        except Exception:
            if not os.path.isfile(src_path):
                raise Http404
            resp = FileResponse(open(src_path, 'rb'))
            resp['Cache-Control'] = 'public, max-age=3600'
            return resp

    resp = FileResponse(open(cache_path, 'rb'))
    resp['Cache-Control'] = 'public, max-age=86400'
    resp['Content-Type'] = 'image/jpeg'
    return resp


# ── /api/pricing (app.py 1980-1993) ────────────────────────
@require_POST
@rate_limit(limit=60, window=60, json_response=True)  # M-5: public endpoint
def api_pricing(request):
    data = body(request)
    task = data.get('task')
    count = max(1, int(data.get('count', 1)))
    if task not in PRICING_MAP:
        return err('Invalid task')
    unit, per, unit_label = PRICING_MAP[task]
    total = unit if per == 'fixed' else unit * count
    disp_count = '' if per == 'fixed' else f'₹{unit//100} × {count} {unit_label}'
    label = disp_count if disp_count else f'₹{total//100} flat'
    return ok({'unit': unit, 'total': total,
               'total_display': f"₹{total//100}", 'label': label})
