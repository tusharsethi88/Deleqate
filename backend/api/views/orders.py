"""
api.views.orders — port of app.py order wizard + submission
(lines 1996-2013 /order, 2015-2505 /submit-order).
All SKU intake parsing, pricing, file naming (S21), upload whitelist (M-3),
Free-Pass and first-order/pay-upfront logic is identical to the Flask app.
"""
import os, json
from datetime import datetime

from django.conf import settings
from django.views.decorators.http import require_POST
from werkzeug.utils import secure_filename

from core.database import get_db, log_status, get_setting, get_option_price
from core.auth import load_user, login_required, dashboard_for, get_csrf_token
from core.business import (
    is_allowed_upload, _file_ext, _clean_label, _unique_named_path, maybe_convert_heic,
    SPACE_TYPE_RENDER_DEFAULTS, TEST_CLIENT_PHONE, INITIAL_FREE_CREDITS,
    PRICE_VIRTUAL_STAGING, PRICE_VIRTUAL_STAGING_STARTER, PRICE_VIRTUAL_STAGING_EXTRA_ROOM,
    PRICE_PROPERTY_REEL_HOOK, PRICE_PROPERTY_REEL_STANDARD, PRICE_PROPERTY_REEL_SHOWCASE,
    PRICE_PROPERTY_SOCIAL_CARD, PRICE_BG_CLEANUP, PRICE_PRODUCT_LISTING, PRICE_PRODUCT_MOCKUP,
    PRICE_INSTAGRAM_CAROUSEL, PRICE_BRAND_DEMO_VIDEO, PRICE_ANNOUNCEMENT_PACK,
    PRICE_BRAND_STARTER_KIT, PRICE_MENU_DESIGN, PRICE_PODCAST_REEL, PRICE_EQUITY_RESEARCH,
    PRICE_PER_RENDER, PRICE_PER_STAGING, PRICE_PER_PRODUCT, PRICE_AUDIO_FIXED,
)
from api.helpers import ok, err


_LISTED_COMPANIES = None


def _is_listed_company(name):
    """True if `name` exactly matches a company name or ticker in
    new_companies.csv (case-insensitive). Enforces list-only equity-research
    selection server-side. Fails open only if the CSV can't be read."""
    global _LISTED_COMPANIES
    if _LISTED_COMPANIES is None:
        import csv
        names = set()
        try:
            path = os.path.join(str(settings.PROJECT_ROOT), 'new_companies.csv')
            with open(path, newline='', encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    n = (r.get('name') or '').strip().lower()
                    t = (r.get('ticker') or '').strip().lower()
                    if n:
                        names.add(n)
                    if t and t != 'id':
                        names.add(t)
        except Exception:
            names = set()
        _LISTED_COMPANIES = names
    if not _LISTED_COMPANIES:
        return True   # CSV unreadable → don't block orders
    return (name or '').strip().lower() in _LISTED_COMPANIES


def _save_django_file(f, path):
    with open(path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)


# ── /order — wizard page data (app.py 1996-2013) ───────────
def order_wizard_data(request):
    user = load_user(request)
    if not user.is_authenticated:
        request.session['next_url'] = request.build_absolute_uri()
        return err('Please log in to place an order.', category='info',
                   redirect='/login', status=401)
    if user.role != 'client':
        return err(f"You are signed in as {user.role}. Log out and sign in with "
                   f"the client's WhatsApp number to place an order.",
                   redirect=dashboard_for(user.role), status=403)
    task = request.GET.get('task', '')
    conn = get_db()
    inactive_tasks = [r['task_key'] for r in conn.execute('SELECT task_key FROM skus WHERE is_active=0').fetchall()]
    conn.close()
    return ok({'task': task, 'space_defaults': SPACE_TYPE_RENDER_DEFAULTS,
               'inactive_tasks': inactive_tasks,
               'voice_brief_enabled': get_setting('voice_brief_enabled', '1') == '1',
               'csrf_token': get_csrf_token(request)})


# ── /submit-order (app.py 2015-2505) ───────────────────────
@require_POST
@login_required
def submit_order(request):
    try:
        F = request.POST
        task = (F.get('task_type') or F.get('task') or '').strip()
        if not task:
            return err('Task required.', success=False)

        current_user = request.user
        if current_user.role != 'client':
            return err(
                f"You are logged in as {current_user.role}. Orders can only be placed "
                f"from a client account. Log out and log in with the client's WhatsApp "
                f"number before placing the order.", status=403, success=False)

        # P2-B: feature-flag off legacy/retired SKUs. These are not offered on the
        # homepage; block new orders so no paid order is created on a dead flow.
        # (TASK_LABELS still maps them so historical orders display correctly.)
        LEGACY_TASKS = {'moodboard', 'staging', 'product', 'audio', 'property_listing'}
        if task in LEGACY_TASKS:
            return err('This service is no longer available. Please choose one of our '
                       'current services.', success=False)

        client_id_resolved = current_user.id
        name = current_user.name
        email = current_user.email
        phone = (current_user.phone or '').strip()

        intake_data = {}
        render_count = 1
        if task == 'virtual_staging':
            room_labels = F.getlist('room_labels[]')
            rooms = [{'label': lbl.strip()} for lbl in room_labels if lbl.strip()]
            vs_tier = F.get('vs_tier', 'full').lower()
            if vs_tier not in ('starter', 'full'):
                vs_tier = 'full'
            room_count = len(rooms) or 1
            # Tier price is admin-controlled via sku_price_options (fallback to constants).
            if vs_tier == 'starter':
                price_unit = get_option_price('virtual_staging', 'vs_tier', 'starter') or PRICE_VIRTUAL_STAGING_STARTER
                extra_rooms = 0
            else:
                extra_rooms = max(0, room_count - 4)
                base = get_option_price('virtual_staging', 'vs_tier', 'full') or PRICE_VIRTUAL_STAGING
                price_unit = base + extra_rooms * PRICE_VIRTUAL_STAGING_EXTRA_ROOM
            intake_data = {
                'property_type':  F.get('property_type', 'Residential'),
                'property_stage': F.get('property_stage', 'Finished'),
                'style':          F.get('style', '').strip(),
                'buyer_profile':  F.get('buyer_profile', '').strip(),
                'special_notes':  F.get('special_notes', '').strip(),
                'rooms':          rooms,
                'vs_tier':        vs_tier,
                'extra_rooms':    extra_rooms,
            }
        elif task == 'property_reel':
            reel_tier = F.get('reel_tier', 'hook').lower()
            intake_data = {
                'property_name':   F.get('property_name', '').strip(),
                'property_type':   F.get('property_type', 'Residential'),
                'bhk_size':        F.get('bhk_size', '').strip(),
                'location':        F.get('location', '').strip(),
                'selling_points':  F.get('selling_points', '').strip(),
                'contact_name':    F.get('contact_name', '').strip(),
                'contact_number':  F.get('contact_number', '').strip(),
                'reel_tier':       reel_tier,
                'platform':        F.get('platform', 'kling').lower(),
                'tone':            F.get('tone', '').strip(),
                'voiceover':       F.get('voiceover', 'no'),
                'voiceover_lang':  F.get('voiceover_lang', 'English'),
                'music':           F.get('music', 'soft'),
                'photo_labels':    F.getlist('property_photos_label[]'),
                'furnished_status': F.get('furnished_status', 'Fully Furnished'),
                'interior_style':  F.get('interior_style', 'Modern/Contemporary'),
                'price_bracket':   F.get('price_bracket', '').strip(),
                'special_note':    F.get('special_note', '').strip(),
            }
            _tier_prices = {
                'hook':     PRICE_PROPERTY_REEL_HOOK,
                'standard': PRICE_PROPERTY_REEL_STANDARD,
                'showcase': PRICE_PROPERTY_REEL_SHOWCASE,
            }
            price_unit = (get_option_price('property_reel', 'reel_tier', reel_tier)
                          or _tier_prices.get(reel_tier, PRICE_PROPERTY_REEL_HOOK))
        elif task == 'property_social_card':
            intake_data = {
                'property_name':  F.get('property_name', '').strip(),
                'location':       F.get('location', '').strip(),
                'highlights':     F.get('highlights', '').strip(),
                'asking_price':   F.get('asking_price', '').strip(),
                'contact_name':   F.get('contact_name', '').strip(),
                'contact_number': F.get('contact_number', '').strip(),
                'brand_colors':   F.get('brand_colors', '').strip(),
                'card_style':     F.get('card_style', 'Modern'),
            }
            price_unit = PRICE_PROPERTY_SOCIAL_CARD
        elif task == 'bg_cleanup':
            image_count = int(F.get('image_count', 0))
            if image_count < 1:
                return err('Please enter the number of images.', success=False)
            if image_count > 10:
                image_count = 10
            render_count = 1  # Bill flat rate
            final_use = F.get('final_use', 'Amazon / Flipkart').strip()
            background = F.get('background_type', 'white').strip()
            shadow = F.get('shadow', 'natural').strip()
            output_format = F.get('output_format', 'PNG').strip()
            background_custom = F.get('background_custom', '').strip()
            # Smart branch — never trust the client: marketplace compliance forced server-side.
            if final_use in ('Amazon / Flipkart', 'Amazon', 'Flipkart'):
                background, shadow, output_format, background_custom = 'white', 'none', 'JPG', ''
            intake_data = {
                'image_count':          image_count,
                'final_use':            final_use,
                'background_type':      background,
                'background_custom':    background_custom,
                'shadow':               shadow,
                'output_format':        output_format,
                'special_instructions': F.get('special_instructions', '').strip(),
            }
            price_unit = PRICE_BG_CLEANUP
        elif task == 'product_listing':
            render_count = max(1, int(F.get('product_count', 1)))
            intake_data = {
                'product_name':    F.get('product_name', '').strip(),
                'brand_name':      F.get('brand_name', '').strip(),
                'category':        F.get('category', '').strip(),
                'key_features':    F.get('key_features', '').strip(),
                'specifications':  F.get('specifications', '').strip(),
                'target_buyer':    F.get('target_buyer', '').strip(),
                'price_point':     F.get('price_point', '').strip(),
                'platforms':       F.getlist('platform[]') or F.getlist('platform') or ['Amazon'],
                'd2c_website_url': F.get('d2c_website_url', '').strip(),
                'primary_keyword': F.get('primary_keyword', '').strip(),
                'listing_type':    F.get('listing_type', 'new'),
                'competitor_url':  F.get('competitor_url', '').strip(),
            }
            price_unit = PRICE_PRODUCT_LISTING
        elif task == 'product_mockup':
            render_count = max(1, int(F.get('mockup_count', 1)))
            intake_data = {
                'product_name':       F.get('product_name', '').strip(),
                'product_desc':       F.get('product_desc', '').strip(),
                'scene_setting':      F.get('scene_setting', '').strip(),
                'mood':               F.get('mood', '').strip(),
                'target_audience':    F.get('target_audience', '').strip(),
                'avoid_elements':     F.get('avoid_elements', '').strip(),
                'product_material':   F.get('product_material', '').strip(),
                'brand_colours':      F.get('brand_colours', '').strip(),
                'output_ratio':       F.get('output_ratio', '1:1'),
                'lighting_direction': F.get('lighting_direction', '').strip(),
                'scale_reference':    F.get('scale_reference', '').strip(),
                'product_category':   F.get('product_category', '').strip(),
                'product_url':        F.get('product_url', '').strip(),
                'product_dimensions': F.get('product_dimensions', '').strip(),
            }
            price_unit = PRICE_PRODUCT_MOCKUP
        elif task == 'instagram_carousel':
            # SKU 7 redesign — 9 essential fields. Each key point becomes one slide.
            key_points = [p.strip() for p in F.getlist('key_points[]') if p.strip()][:5]
            # Multi-URL: client may drop website + Instagram + product page. AI researches all.
            brand_urls = [u.strip() for u in F.getlist('brand_urls[]') if u.strip()][:5]
            if not brand_urls and F.get('brand_url', '').strip():
                brand_urls = [F.get('brand_url', '').strip()]
            # Target audience: multi-select personas (audience[]) + optional free-text note.
            # NOTE: the form historically posted `target_audience` while this code read
            # `audience` → audience always defaulted to "General". Now we read the personas.
            _AUDIENCE_DESC = {
                'Quiet Luxury':         'UHNI / inherited wealth; discreet premium — craftsmanship, heritage, wellness, fine materials; rejects loud logos',
                'Aspirational Premium': 'high-earning urban professionals & founders; brand as a social status badge; loud, aspirational premium spending',
                'Convenience-First':    'time-poor dual-income urban households; treat time as currency — quick commerce, instant gratification, home services',
                'Gen Z Trendsetter':    'college & early-career online natives; aesthetic-led impulse buyers cycling through micro-trends',
                'Value-Seeking Family': 'middle-class family anchors (Gen X / older millennials); planned, risk-averse, value-for-money, family-first',
                'Smart Researcher':     'Tier 1-2 deal hunters; research offline, buy online stacking cashbacks, coupons & seasonal sales',
                'Wellness-Conscious':   'health-led families & fitness buyers; read labels, pay 20-30% more for clean, transparent, preservative-free products',
                'Rurban Aspirer':       'Tier 3-4 & rural youth; high internet, low retail access; want the Tier-1 lifestyle at affordable entry-level prices',
                'Local Value Buyer':    'mass urban-migrant & rural; transactional, loyal to local/unbranded products on a fixed monthly budget',
                'Daily Essentials':     'daily-wage & lowest-income; survival-based spend on sachets & small single-use packs for single-day needs',
            }
            audience_segments = [a.strip() for a in F.getlist('audience[]') if a.strip()]
            # Back-compat: old free-text field still accepted if posted
            audience_note = (F.get('audience_note', '') or F.get('target_audience', '')).strip()
            audience_str = ', '.join(audience_segments) if audience_segments else 'General'
            if audience_note:
                audience_str = f'{audience_str} ({audience_note})' if audience_segments else audience_note
            audience_detail = '; '.join(
                (f'{seg} — {_AUDIENCE_DESC[seg]}' if seg in _AUDIENCE_DESC else seg)
                for seg in audience_segments)
            if audience_note:
                audience_detail = (f'{audience_detail}; client note: {audience_note}' if audience_detail
                                   else f'client note: {audience_note}')
            intake_data = {
                'brand_name':     F.get('brand_name', '').strip(),
                'brand_colors':   F.get('brand_colours', '').strip(),
                'goal':           F.get('goal', 'Educate / Tips').strip(),
                'carousel_topic': F.get('carousel_topic', '').strip(),
                'key_points':     key_points,
                'cta_text':       F.get('cta_text', '').strip(),
                'audience':          audience_str,
                'audience_segments': audience_segments,
                'audience_detail':   audience_detail,
                'audience_note':     audience_note,
                'num_slides':     F.get('num_slides', '7').strip(),
                'visual_style':   F.get('visual_style', 'Bold Typography').strip(),
                'notes':          F.get('special_notes', '').strip(),
                'brand_url':      (brand_urls[0] if brand_urls else ''),
                'brand_urls':     brand_urls,
                'carousel_format': F.get('carousel_format', 'Image + Text').strip(),
                'infographic_data': F.get('infographic_data', '').strip(),
            }
            # Format-driven price (admin-controlled); fallback keeps old behavior.
            _fmt = F.get('carousel_format', '').strip()
            price_unit = (get_option_price('instagram_carousel', 'carousel_format', _fmt)
                          or (89900 if _fmt == 'Infographic' else PRICE_INSTAGRAM_CAROUSEL))
        elif task == 'brand_demo_video':
            intake_data = {
                'brand_name':      F.get('brand_name', '').strip(),
                'usps':            F.get('usps', '').strip(),
                'target_audience': F.get('target_audience', '').strip(),
                'duration':        F.get('duration', '30s'),
                'tone':            F.get('tone', '').strip(),
                'platform':        F.get('platform', 'Instagram Reel'),
                'brand_contact':   F.get('brand_contact', '').strip(),
                'music':           F.get('music', 'soft'),
                'reference_video': F.get('reference_video', '').strip(),
            }
            # Duration-driven price (admin-controlled); fallback to flat rate.
            price_unit = (get_option_price('brand_demo_video', 'duration', F.get('duration', '30s'))
                          or PRICE_BRAND_DEMO_VIDEO)
        elif task == 'announcement_pack':
            intake_data = {
                'brand_name':        F.get('brand_name', '').strip(),
                'announcement_type': F.get('announcement_type', 'Special Offer'),
                'headline':          F.get('headline', '').strip(),
                'sub_points':        F.get('sub_points', '').strip(),
                'cta_text':          F.get('cta_text', '').strip(),
                'contact':           F.get('contact', '').strip(),
                'tone':              F.get('tone', 'Exciting'),
                'brand_colors':      F.get('brand_colors', '').strip(),
                'visual_direction':  F.get('visual_direction', '').strip(),
            }
            price_unit = PRICE_ANNOUNCEMENT_PACK
        elif task == 'brand_starter_kit':
            intake_data = {
                'business_name':    F.get('business_name', '').strip(),
                'industry':         F.get('industry', '').strip(),
                'personality':      F.get('personality', '').strip(),
                'target_customer':  F.get('target_customer', '').strip(),
                'color_preference': F.get('color_preference', '').strip(),
                'style_direction':  F.get('style_direction', '').strip(),
                'tagline':          F.get('tagline', '').strip(),
                'deliverables':     F.getlist('deliverables'),
                'reference_brands': F.get('reference_brands', '').strip(),
            }
            price_unit = PRICE_BRAND_STARTER_KIT
        elif task == 'menu_design':
            intake_data = {
                'business_name':    F.get('business_name', '').strip(),
                'brand_colors':     F.get('brand_colors', '').strip(),
                'menu_format':      F.get('menu_format', 'A4 single page'),
                'output_format':    F.getlist('output_format'),
                'dietary_icons':    F.get('dietary_icons', 'no'),
                'menu_style':       F.get('menu_style', 'modern'),
                'special_callouts': F.get('special_callouts', '').strip(),
                'menu_items_text':  F.get('menu_items_text', '').strip(),
                'business_urls':    F.get('business_urls', '').strip(),
                'create_logo':      F.get('create_logo', 'no'),
            }
            price_unit = PRICE_MENU_DESIGN
        elif task == 'podcast_reel':
            intake_data = {
                'recording_duration': F.get('recording_duration', '').strip(),
                'episode_topic':      F.get('episode_topic', '').strip(),
                'guest_name':         F.get('guest_name', '').strip(),
                'host_name':          F.get('host_name', '').strip(),
                'preferred_moments':  F.get('preferred_moments', '').strip(),
                'output_format':      F.get('output_format', 'audiogram'),
                'show_name':          F.get('show_name', '').strip(),
                'brand_colors':       F.get('brand_colors', '').strip(),
                'target_platform':    F.get('target_platform', 'Instagram'),
                'caption_style':      F.get('caption_style', 'full'),
            }
            price_unit = PRICE_PODCAST_REEL
        elif task == 'equity_research':
            sname = F.get('stock_name', '').strip()
            if not _is_listed_company(sname):
                return err('Please select a company from the list. Custom company names are not allowed.')
            intake_data = {
                'stock_name': sname,
                'research_focus': F.get('research_focus', '').strip(),
                'report_type': F.get('report_type', 'Single-Stock Deep-Dive').strip(),
            }
            price_unit = PRICE_EQUITY_RESEARCH
        # ── Legacy SKUs ──
        elif task == 'moodboard':
            intake_data = {
                'space_name':      F.get('space_name', '').strip(),
                'space_type':      F.get('space_type', 'other'),
                'has_moodboard':   F.get('has_moodboard') == 'yes',
                'style_direction': F.get('style_direction', '').strip(),
                'hero_element':    F.get('hero_element', '').strip(),
                'special_notes':   F.get('special_notes', '').strip(),
            }
            render_count = int(F.get('render_count', 2))
            price_unit = PRICE_PER_RENDER
        elif task == 'staging':
            intake_data = {'style_direction': F.get('style_direction', '').strip()}
            render_count = int(F.get('photo_count', 1))
            price_unit = PRICE_PER_STAGING
        elif task == 'product':
            intake_data = {'product_type': F.get('product_type', '').strip()}
            render_count = int(F.get('image_count', 3))
            price_unit = PRICE_PER_PRODUCT
        elif task == 'audio':
            intake_data = {'cleanup_types': F.getlist('cleanup_type')}
            render_count = 1
            price_unit = PRICE_AUDIO_FIXED
        else:
            return err('Unknown task type.', success=False)

        total_price = price_unit * render_count

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        conn = get_db()
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()

        client_id = client_id_resolved

        existing_order_count = conn.execute(
            'SELECT COUNT(*) FROM orders WHERE client_id=?', (client_id,)).fetchone()[0]
        is_first_order = existing_order_count == 0

        initial_status = 'in_progress' if task == 'equity_research' else 'pending'

        cur.execute('''INSERT INTO orders
            (client_id,name,phone,email,task,intake_data,render_count,price_per_unit,total_price,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (client_id, name, phone, email, task, json.dumps(intake_data),
             render_count, price_unit, total_price, initial_status))
        order_id = cur.lastrowid
        log_status(conn, order_id, None, initial_status, client_id, 'Order submitted via wizard')

        folder = os.path.join(settings.UPLOAD_FOLDER, f'order_{order_id}_{ts}')
        os.makedirs(folder, exist_ok=True)

        # Collect names of files we had to reject (unsupported type) so we can
        # tell the client instead of silently dropping them.
        skipped_files = []

        def _ext_ok(filename):
            return is_allowed_upload(filename)

        def save_file(field_name, atype):
            f = request.FILES.get(field_name)
            if f and f.name:
                if not _ext_ok(f.name):
                    skipped_files.append(f.name)
                    return None  # skip disallowed types (surfaced to client below)
                sfn = secure_filename(f.name) or f'file.{_file_ext(f.name)}'
                stem = sfn.rsplit('.', 1)[0] if '.' in sfn else sfn
                safe, path = _unique_named_path(folder, f'{order_id}_{stem}', _file_ext(f.name))
                _save_django_file(f, path)
                rel = f'order_{order_id}_{ts}/{safe}'
                path, rel = maybe_convert_heic(path, rel)
                cur.execute('INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size) VALUES (?,?,?,?,?)',
                            (order_id, atype, rel, f.name, os.path.getsize(path)))
                return rel
            return None

        def save_files(field_name, atype):
            for f in request.FILES.getlist(field_name):
                if f and f.name:
                    if not _ext_ok(f.name):
                        skipped_files.append(f.name)
                        continue
                    sfn = secure_filename(f.name) or f'file.{_file_ext(f.name)}'
                    stem = sfn.rsplit('.', 1)[0] if '.' in sfn else sfn
                    safe, path = _unique_named_path(folder, f'{order_id}_{stem}', _file_ext(f.name))
                    _save_django_file(f, path)
                    rel = f'order_{order_id}_{ts}/{safe}'
                    path, rel = maybe_convert_heic(path, rel)
                    cur.execute('INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size) VALUES (?,?,?,?,?)',
                                (order_id, atype, rel, f.name, os.path.getsize(path)))

        # ── Virtual Staging: POV A + optional POV B + optional Moodboard per room ──
        if task == 'virtual_staging':
            vs_photos_a = request.FILES.getlist('room_photos[]')
            vs_photos_b = request.FILES.getlist('room_photos_b[]')
            vs_moodboards = request.FILES.getlist('room_moodboards[]')
            vs_labels = F.getlist('room_labels[]')
            for idx, f in enumerate(vs_photos_a):
                if f and f.name and _ext_ok(f.name):
                    lbl = vs_labels[idx].strip() if idx < len(vs_labels) else f'Room {idx+1}'
                    safe, path = _unique_named_path(folder, f'{_clean_label(lbl)} POV A', _file_ext(f.name))
                    _save_django_file(f, path)
                    rel = f'order_{order_id}_{ts}/{safe}'
                    path, rel = maybe_convert_heic(path, rel)
                    cur.execute(
                        'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                        (order_id, 'room_photo', rel, f.name, os.path.getsize(path), lbl))
                    fb = vs_photos_b[idx] if idx < len(vs_photos_b) else None
                    if fb and fb.name and _ext_ok(fb.name):
                        safe_b, path_b = _unique_named_path(folder, f'{_clean_label(lbl)} POV B', _file_ext(fb.name))
                        _save_django_file(fb, path_b)
                        rel_b = f'order_{order_id}_{ts}/{safe_b}'
                        path_b, rel_b = maybe_convert_heic(path_b, rel_b)
                        cur.execute(
                            'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                            (order_id, 'room_photo_b', rel_b, fb.name, os.path.getsize(path_b), lbl))
                    fm = vs_moodboards[idx] if idx < len(vs_moodboards) else None
                    if fm and fm.name and _ext_ok(fm.name):
                        safe_m, path_m = _unique_named_path(folder, f'{_clean_label(lbl)} Moodboard', _file_ext(fm.name))
                        _save_django_file(fm, path_m)
                        rel_m = f'order_{order_id}_{ts}/{safe_m}'
                        path_m, rel_m = maybe_convert_heic(path_m, rel_m)
                        cur.execute(
                            'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                            (order_id, 'moodboard', rel_m, fm.name, os.path.getsize(path_m), lbl))

        # ── Property Reel: POV A + optional POV B + optional Moodboard per area ──
        if task == 'property_reel':
            pr_photos_a = request.FILES.getlist('property_photos')
            pr_photos_b = request.FILES.getlist('property_photos_b')
            pr_moodboards = request.FILES.getlist('property_moodboards')
            pr_labels = F.getlist('property_photos_label[]')
            for idx, f in enumerate(pr_photos_a):
                if f and f.name and _ext_ok(f.name):
                    lbl = pr_labels[idx].strip() if idx < len(pr_labels) else f'Area {idx+1}'
                    safe, path = _unique_named_path(folder, f'{_clean_label(lbl)} POV A', _file_ext(f.name))
                    _save_django_file(f, path)
                    rel = f'order_{order_id}_{ts}/{safe}'
                    path, rel = maybe_convert_heic(path, rel)
                    cur.execute(
                        'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                        (order_id, 'property_photo', rel, f.name, os.path.getsize(path), lbl))
                    fb = pr_photos_b[idx] if idx < len(pr_photos_b) else None
                    if fb and fb.name and _ext_ok(fb.name):
                        safe_b, path_b = _unique_named_path(folder, f'{_clean_label(lbl)} POV B', _file_ext(fb.name))
                        _save_django_file(fb, path_b)
                        rel_b = f'order_{order_id}_{ts}/{safe_b}'
                        path_b, rel_b = maybe_convert_heic(path_b, rel_b)
                        cur.execute(
                            'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                            (order_id, 'property_photo_b', rel_b, fb.name, os.path.getsize(path_b), lbl))
                    fm = pr_moodboards[idx] if idx < len(pr_moodboards) else None
                    if fm and fm.name and _ext_ok(fm.name):
                        safe_m, path_m = _unique_named_path(folder, f'{_clean_label(lbl)} Moodboard', _file_ext(fm.name))
                        _save_django_file(fm, path_m)
                        rel_m = f'order_{order_id}_{ts}/{safe_m}'
                        path_m, rel_m = maybe_convert_heic(path_m, rel_m)
                        cur.execute(
                            'INSERT INTO order_attachments (order_id,attachment_type,filename,original_name,file_size,file_label) VALUES (?,?,?,?,?,?)',
                            (order_id, 'moodboard', rel_m, fm.name, os.path.getsize(path_m), lbl))

        # File uploads — map SKU to field name(s) (verbatim FILE_MAP)
        FILE_MAP = {
            'virtual_staging':    [('moodboard_file', 'moodboard', True),
                                   ('voice_note', 'voice_note', False)],
            'property_reel':      [('voice_note', 'voice_note', False)],
            'property_social_card': [('property_photo', 'property_photo', True),
                                     ('logo_file', 'logo', True),
                                     ('voice_note', 'voice_note', False)],
            'property_listing':   [('floor_plan_file', 'floor_plan', True),
                                   ('voice_note', 'voice_note', False)],
            'bg_cleanup':         [('product_photos', 'product_photo', True),
                                   ('voice_note', 'voice_note', False)],
            'product_listing':    [('product_photo', 'product_photo', True),
                                   ('voice_note', 'voice_note', False)],
            'product_mockup':     [('product_photos', 'product_photo', True),
                                   ('voice_note', 'voice_note', False)],
            'instagram_carousel': [('logo_file', 'logo', True),
                                   ('carousel_product_photos', 'carousel_product', True),
                                   ('voice_note', 'voice_note', False)],
            'brand_demo_video':   [('product_photos', 'product_photo', True),
                                   ('voice_note', 'voice_note', False)],
            'announcement_pack':  [('logo_file', 'logo', True),
                                   ('reference_image', 'reference', True),
                                   ('voice_note', 'voice_note', False)],
            'brand_starter_kit':  [('logo_file', 'logo', True),
                                   ('voice_note', 'voice_note', False)],
            'menu_design':        [('logo_file', 'logo', True),
                                   ('menu_file', 'menu_items', False),
                                   ('existing_menu', 'existing_menu', True),
                                   ('voice_note', 'voice_note', False)],
            'podcast_reel':       [('audio_file', 'audio', False),
                                   ('logo_file', 'logo', True),
                                   ('voice_note', 'voice_note', False)],
            'equity_research':    [('voice_note', 'voice_note', False)],
            'moodboard':          [('floorplan_file', 'floor_plan', False),
                                   ('moodboard_file', 'moodboard', True)],
            'staging':            [('room_photos', 'room_photo', True)],
            'product':            [('product_photos', 'product_photo', True)],
            'audio':              [('media_file', 'media', False)],
        }
        for field, atype, multi in FILE_MAP.get(task, []):
            if multi:
                save_files(field, atype)
            else:
                save_file(field, atype)

        # Create pilot_steps for per-unit render tasks (legacy moodboard/staging only)
        if task in ('moodboard', 'staging'):
            pov_labels = [chr(65 + i) for i in range(render_count)]
            for pov in pov_labels:
                cur.execute('INSERT INTO pilot_steps (order_id, pov, step_status) VALUES (?,?,?)',
                            (order_id, pov, 'pending'))

        # ── Centralized required-asset gate (replaces the bg_cleanup-only check) ──
        # Map every ACTIVE SKU. Use None to declare "no asset strictly required"
        # as a *conscious* decision, not an omission. Attachment-type strings
        # match exactly what the insert statements above write.
        REQUIRED_ATTACHMENTS = {
            'virtual_staging':      ('room_photo',     'Please upload at least one room photo.'),
            'property_reel':        ('property_photo',  'Please upload at least one property photo.'),
            'property_social_card': ('property_photo',  'Please upload a property photo.'),
            'bg_cleanup':           ('product_photo',   'Please upload at least one product photo.'),
            'product_listing':      ('product_photo',   'Please upload a product photo.'),
            'product_mockup':       ('product_photo',   'Please upload at least one product photo.'),
            'brand_demo_video':     ('product_photo',   'Please upload at least one product photo.'),
            'podcast_reel':         ('audio',           'Please upload your audio file.'),
            # Conscious decisions — core asset is optional for these:
            'instagram_carousel':   None,   # logo optional (decided with product)
            'announcement_pack':    None,   # logo optional (decided with product)
            'brand_starter_kit':    None,   # logo optional (many buyers have no logo yet)
            'menu_design':          None,   # existing-menu optional
            'property_listing':     None,
            'equity_research':      None,
            # Legacy SKUs (no strict requirement)
            'moodboard':            None,
            'staging':              None,
            'product':              None,
            'audio':                None,
        }
        _req = REQUIRED_ATTACHMENTS.get(task)
        if _req is not None:
            _atype, _msg = _req
            _have = cur.execute(
                "SELECT COUNT(*) FROM order_attachments WHERE order_id=? AND attachment_type=?",
                (order_id, _atype)).fetchone()[0]
            if _have == 0:
                conn.rollback()
                conn.close()
                # Clean up any files already written for this rolled-back order.
                import shutil
                shutil.rmtree(folder, ignore_errors=True)
                return err(_msg, success=False)

        # Property reel: POV B (second angle) is mandatory for every area.
        if task == 'property_reel':
            n_a = cur.execute("SELECT COUNT(*) FROM order_attachments WHERE order_id=? AND attachment_type='property_photo'", (order_id,)).fetchone()[0]
            n_b = cur.execute("SELECT COUNT(*) FROM order_attachments WHERE order_id=? AND attachment_type='property_photo_b'", (order_id,)).fetchone()[0]
            if n_a == 0 or n_b < n_a:
                conn.rollback()
                conn.close()
                import shutil
                shutil.rmtree(folder, ignore_errors=True)
                return err('Please upload both POV A and POV B (second angle) for every area.', success=False)

        conn.commit()

        # Warn (don't fail) if non-required files were rejected for type.
        _warn = ''
        if skipped_files:
            _warn = (' Note: we could not accept these files (unsupported type): '
                     + ', '.join(skipped_files[:5])
                     + ('…' if len(skipped_files) > 5 else '') + '.')

        # ── Free Pass: test client bypasses all payment ────
        _is_test_client = (current_user.phone or '') == TEST_CLIENT_PHONE
        _wants_free_pass = F.get('use_free_pass') == '1'
        if _is_test_client and _wants_free_pass:
            conn.execute(
                "UPDATE orders SET payment_method='free_pass', client_action='paid_upfront' WHERE id=?",
                (order_id,))
            prev = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE client_id=? AND payment_method IN ('payu','free_pass') AND id!=?",
                (client_id, order_id)).fetchone()[0]
            if prev == 0:
                conn.execute('UPDATE users SET edit_credits = edit_credits + ? WHERE id=?',
                             (INITIAL_FREE_CREDITS, client_id))
            conn.commit(); conn.close()
            return ok({'success': True, 'order_id': order_id,
                       'total': f'₹{total_price//100}', 'free_pass_used': True,
                       'message': f'Free Pass used! Order #{order_id} confirmed.' + _warn})

        if not is_first_order:
            conn.execute("UPDATE orders SET client_action='pay_upfront' WHERE id=?", (order_id,))
            conn.commit(); conn.close()
            payment_url = f'/payment/initiate?order_id={order_id}'
            return ok({'success': True, 'order_id': order_id,
                       'total': f'₹{total_price//100}',
                       'requires_upfront_payment': True,
                       'payment_url': payment_url,
                       'message': f'Order #{order_id} created! Complete payment to confirm your order.' + _warn})
        # First order — pay after delivery
        conn.close()
        return ok({'success': True, 'order_id': order_id,
                   'total': f'₹{total_price//100}',
                   'message': f'Order #{order_id} placed! Your AI Pilot will be assigned within 15 minutes.' + _warn})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return err(str(e), status=500, success=False)
