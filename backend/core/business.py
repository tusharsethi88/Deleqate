"""
core.business — VERBATIM business logic extracted from app.py.
Pricing constants, PayU hashing, reel/prompt engines, file helpers.
Do not edit logic here without mirroring the original app.py behavior.
(Secret-key startup check lives in config/settings.py.)
"""
import os, re, sys, hashlib, hmac
from werkzeug.utils import secure_filename

# ── HEIC/HEIF support (iPhone photos) ──────────────────────
# Register the decoder once at import so Pillow can open .heic/.heif. Uploads
# are converted to browser-renderable JPEG on save (see orders.py / pilot.py).
# If the package is unavailable, HEIC stays disabled (kept out of the
# allow-list below) rather than accepted-but-broken.
HEIC_ENABLED = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_ENABLED = True
except Exception:
    pass
ADMIN_EMAIL    = 'support@deleqate.com'
ADMIN_PASSWORD = os.environ.get('DELEQATE_ADMIN_PASSWORD', 'deleqate2026')
IS_PRODUCTION = (os.environ.get('FLASK_ENV') == 'production'
                 or os.environ.get('DJANGO_ENV') == 'production')
if ADMIN_PASSWORD == 'deleqate2026':
    if IS_PRODUCTION:
        raise SystemExit('FATAL: DELEQATE_ADMIN_PASSWORD not set. Refusing to start in production with the default admin password.')
    print('⚠ WARNING: DELEQATE_ADMIN_PASSWORD not set — using insecure default. Add to .env before deploying.', file=sys.stderr)
# ── Filename hygiene helpers (S21) ────────────────────────
# Standardise uploaded reference photos and deliverables to human-readable,
# collision-safe names like "Living Room POV A.jpg" so pilots and clients
# never see raw hashes or risky original filenames.
def _file_ext(filename, default='jpg'):
    """Return a safe lowercase extension from an arbitrary uploaded name."""
    fn = secure_filename(filename or '')
    return fn.rsplit('.', 1)[-1].lower() if '.' in fn else default

def _clean_label(label):
    """Human-readable label safe for use in a filename (no path chars)."""
    s = re.sub(r'[^\w\s-]', '', (label or '').strip())
    s = re.sub(r'\s+', ' ', s).strip()
    return s or 'File'

# ── M-3: Central upload validation — one whitelist, every upload route ──
ALLOWED_UPLOAD_EXTS = {
    'jpg','jpeg','png','gif','webp','avif',
    'pdf','docx','doc','txt','csv',   # no html/htm — stored-XSS risk when served back
    'mp3','wav','m4a','aac','ogg',
    'mp4','mov','avi','mkv','webm',
    'zip','rar',
}
# Only accept HEIC/HEIF when the decoder is installed — we convert to JPEG on
# save, so the stored asset is always browser-renderable. Without the decoder
# we must NOT whitelist them (they'd show as broken images everywhere).
if HEIC_ENABLED:
    ALLOWED_UPLOAD_EXTS |= {'heic', 'heif'}
_IMAGE_EXTS = {'jpg','jpeg','png','gif','webp'}

def is_allowed_upload(filename, allowed=None):
    """Uniform extension check for every upload endpoint. Pass `allowed`
    to narrow (never widen) the global whitelist for a specific route."""
    fn = filename or ''
    ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
    return bool(ext) and ext in (allowed if allowed is not None else ALLOWED_UPLOAD_EXTS)

# NOTE: The Flask-era verify_image_content(file_storage) lived here and used
# `file_storage.stream` (a Werkzeug FileStorage attribute). On Django this
# AttributeErrors and rejects every image upload. The live Django check is
# api.views.pilot.verify_image_content (operates on UploadedFile.file). This
# stub stays only to fail loudly if any old import path is resurrected.
def verify_image_content(*_args, **_kwargs):  # pragma: no cover
    raise NotImplementedError(
        'core.business.verify_image_content was the Flask/Werkzeug version and '
        'does not work on Django uploads. Use api.views.pilot.verify_image_content.')

def _unique_named_path(folder, base, ext):
    """Return (filename, fullpath) that does not collide inside `folder`.
    Appends _1, _2 … instead of overwriting an existing file."""
    candidate = f'{base}.{ext}'
    path = os.path.join(folder, candidate)
    i = 1
    while os.path.exists(path):
        candidate = f'{base}_{i}.{ext}'
        path = os.path.join(folder, candidate)
        i += 1
    return candidate, path

def maybe_convert_heic(path, rel):
    """If `path` is a freshly-saved HEIC/HEIF file, convert it to a JPEG
    alongside, delete the original, and return the JPEG's (path, rel). For any
    other type (or if conversion fails / HEIC disabled) return (path, rel)
    unchanged. `rel` is the DB-stored relative path (e.g. 'order_5_ts/foo.heic').
    """
    ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
    if ext not in ('heic', 'heif') or not HEIC_ENABLED:
        return path, rel
    try:
        from PIL import Image
        jpg_path = os.path.splitext(path)[0] + '.jpg'
        Image.open(path).convert('RGB').save(jpg_path, 'JPEG', quality=90)
        os.remove(path)
        new_rel = rel.rsplit('.', 1)[0] + '.jpg' if '.' in rel else rel + '.jpg'
        return jpg_path, new_rel
    except Exception:
        # Leave the original in place rather than losing the upload.
        return path, rel
# ── SUPPORT / PAYMENT CONFIG ──────────────────────────────
SUPPORT_WHATSAPP = os.environ.get('SUPPORT_WHATSAPP', '917011989292')

# ── TEST ACCOUNTS (dev only — remove test pilot before public launch) ──
TEST_CLIENT_PHONE  = '9871722766'   # Free Pass client — phone+PIN login
TEST_CLIENT_PIN    = '1234'
TEST_PILOT_EMAIL   = 'opuluxe24@gmail.com'
TEST_PILOT_PASS    = '1234'

# ── EDIT CREDIT PACKAGES ─────────────────────────────
PRICE_EDIT_CREDIT_1 = 30000   # ₹300 — buy 1 edit
PRICE_EDIT_CREDIT_3 = 50000   # ₹500 — buy 3 edits (best value)
INITIAL_FREE_CREDITS = 3      # granted on first payment  # e.g. 919871722766
SUPPORT_UPI      = os.environ.get('SUPPORT_UPI', 'deleqate@upi')

# ── PAYU PAYMENT GATEWAY ──────────────────────────────────
# C-2: No hard-coded credentials. Dev falls back to the PayU *test* sandbox
# pair; production must supply real key+salt via env or the app won't start.
# NOTE: the previous key/salt were committed to this repo — rotate them in the
# PayU dashboard before going live.
PAYU_KEY      = os.environ.get('PAYU_KEY', '')
PAYU_SALT     = os.environ.get('PAYU_SALT', '')
if not PAYU_KEY or not PAYU_SALT:
    if IS_PRODUCTION:
        raise SystemExit('FATAL: PAYU_KEY / PAYU_SALT not set. Refusing to start in production without payment credentials.')
    # Dev-only fallback: PayU TEST-sandbox pair (matches test.payu.in below).
    PAYU_KEY, PAYU_SALT = 'aU4FrK', 'MPFFcqVnyqHRmybACMu87haMGq5KCaGp'
    print('⚠ WARNING: PAYU_KEY / PAYU_SALT not set — using test-sandbox credentials. Add real ones to .env before launch.', file=sys.stderr)
PAYU_URL      = os.environ.get('PAYU_URL', 'https://test.payu.in/_payment')
FRONTEND_URL  = os.environ.get('FRONTEND_URL', 'http://localhost:8061')

def payu_generate_hash(txnid, amount, productinfo, firstname, email,
                        udf1='', udf2='', udf3='', udf4='', udf5=''):
    """Generate PayU payment hash (SHA-512).
    hash_string = key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt
    """
    hash_str = (f'{PAYU_KEY}|{txnid}|{amount}|{productinfo}|{firstname}|{email}'
                f'|{udf1}|{udf2}|{udf3}|{udf4}|{udf5}||||||{PAYU_SALT}')
    return hashlib.sha512(hash_str.encode('utf-8')).hexdigest()

def payu_verify_hash(posted):
    """Verify PayU's reverse hash on success/failure callback.
    Reverse hash = sha512(SALT|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|KEY)
    Returns True if hash matches.
    """
    status      = posted.get('status', '')
    txnid       = posted.get('txnid', '')
    amount      = posted.get('amount', '')
    productinfo = posted.get('productinfo', '')
    firstname   = posted.get('firstname', '')
    email       = posted.get('email', '')
    udf1 = posted.get('udf1', '')
    udf2 = posted.get('udf2', '')
    udf3 = posted.get('udf3', '')
    udf4 = posted.get('udf4', '')
    udf5 = posted.get('udf5', '')
    received_hash = posted.get('hash', '')
    retro_str = (f'{PAYU_SALT}|{status}||||||{udf5}|{udf4}|{udf3}|{udf2}|{udf1}'
                 f'|{email}|{firstname}|{productinfo}|{amount}|{txnid}|{PAYU_KEY}')
    computed = hashlib.sha512(retro_str.encode('utf-8')).hexdigest()
    return hmac.compare_digest(computed, received_hash)

# ── PRICING (paise) ───────────────────────────────────────
# Cluster 1 — Real Estate
PRICE_VIRTUAL_STAGING            = 79900   # ₹799 — Full Staging up to 4 rooms
PRICE_VIRTUAL_STAGING_STARTER   = 64900   # ₹649 — Starter (2 rooms)
PRICE_VIRTUAL_STAGING_EXTRA_ROOM = 10000  # ₹100 per extra room beyond 4 (Full tier)
PRICE_PROPERTY_REEL_HOOK     =  99900  # ₹999  — Hook Reel  (8s, 2 Frames)
PRICE_PROPERTY_REEL_STANDARD = 159900  # ₹1,599 — Standard Reel (30s, 12 clips)
PRICE_PROPERTY_REEL_SHOWCASE = 249900  # ₹2,499 — Showcase Reel (60s, 20 clips)
PRICE_PROPERTY_SOCIAL_CARD = 49900   # ₹499 flat — 2 social cards
PRICE_BG_CLEANUP        = 50000   # ₹500 flat (up to 10 images)
PRICE_PRODUCT_LISTING   = 19900   # ₹199/product
PRICE_PRODUCT_MOCKUP    = 29900   # ₹299/image
# Cluster 3 — SMB Visual Content
PRICE_INSTAGRAM_CAROUSEL= 64900   # ₹649/carousel
PRICE_BRAND_DEMO_VIDEO  = 124900  # ₹1249/video
PRICE_ANNOUNCEMENT_PACK = 49900   # ₹499/3-piece pack
# Cluster 4 — Personal & Brand
PRICE_BRAND_STARTER_KIT = 199900  # ₹1999/kit
PRICE_MENU_DESIGN       = 79900   # ₹799/menu
PRICE_PODCAST_REEL      = 64900   # ₹649/reel
PRICE_EQUITY_RESEARCH   = 49900   # ₹499/report
# Legacy (kept for backward compat)
PRICE_PER_RENDER        = 24900
PRICE_PER_STAGING       = 39900
PRICE_PER_PRODUCT       = 19900
PRICE_AUDIO_FIXED       = 24900

TASK_LABELS = {
    # Cluster 1 — Real Estate
    'virtual_staging':        'Virtual Staging',
    'property_reel':          'Property Marketing Reel',
    'property_social_card':   'Property Social Card Pack',
    # Cluster 2 — E-commerce
    'bg_cleanup':          'Background Cleanup',
    'product_listing':     'Product Listing Creation',
    'product_mockup':      'Product Lifestyle Mockup',
    # Cluster 3 — SMB Visual Content
    'instagram_carousel':  'Instagram Carousel Design',
    'brand_demo_video':    'Product / Brand Demo Video',
    'announcement_pack':   'Announcement Pack',
    # Cluster 4 — Personal & Brand
    'brand_starter_kit':   'Brand Starter Kit',
    'menu_design':         'Restaurant / Business Menu Design',
    'podcast_reel':        'Podcast Highlight Reel',
    # Cluster 5 — Research
    'equity_research':     'Equity Research Report',
    # Legacy
    'moodboard':              'Interior Rendering (Deferred)',
    'staging':                'Virtual Staging (Legacy)',
    'property_listing':       'Property Listing Copy (Retired)',
    'product':                'Product Visuals (Legacy)',
    'audio':                  'Audio / Video Cleanup (Legacy)',
}

TASK_CLUSTERS = {
    'Real Estate':          ['virtual_staging','property_reel','property_social_card'],
    'E-commerce':           ['bg_cleanup','product_listing','product_mockup'],
    'SMB Visual Content':   ['instagram_carousel','brand_demo_video','announcement_pack'],
    'Personal & Brand':     ['brand_starter_kit','menu_design','podcast_reel'],
    'Research':             ['equity_research'],
}
# ══════════════════════════════════════════════════════════
# PROPERTY REEL v3 — BHK-AWARE SELECTION + PROMPT ENGINE
# ══════════════════════════════════════════════════════════

# ── Room-type classifier ──────────────────────────────────
_RT_MAP = [
    # (canonical_type, [keywords...])  — checked top-to-bottom; SPECIFIC before GENERIC
    ('FACADE',       ['facade','exterior','elevation','front view','front of building','building front','outside','outer','gate']),
    ('TERRACE',      ['terrace','rooftop','roof top','roof','garden terrace','podium terrace']),
    ('BALCONY',      ['balcony','balcony 1','balcony 2','sit out','sitout','deck','verandah','veranda','sit-out']),
    ('AMENITY',      ['pool','swimming','clubhouse','gym','amenity','amenities','recreation','common area']),
    ('LOBBY',        ['lobby','reception','foyer','entrance lobby','main entrance']),
    ('LIVING_DINING',['ldk','living dining','living-dining','combined','open plan','open-plan']),
    ('LIVING',       ['living','hall','lounge','drawing room','drawing','sitting room','sitting','family room','great room','lr']),
    ('DINING',       ['dining room','dining area','dining','dr']),
    ('KITCHEN',      ['kitchen','modular kitchen','kitchenette','cook']),
    ('MASTER_BATH',  ['master bath','master bathroom','master toilet','ensuite','attached bath','master wc']),
    ('MASTER_BR',    ['master bedroom','master bed','master br','master room','mbr','primary bedroom','owner']),
    ('BATHROOM',     ['bathroom','bath','washroom','toilet','wc','lavatory','powder room','common bath','guest bath']),
    ('BEDROOM',      ['bedroom','bed room','br ','guest room','guest bedroom','kids room','children','spare room','room ']),
    ('STUDY',        ['study','office room','library','work room','home office']),
]

def classify_room_type(label):
    """Maps any client label string → canonical room type string."""
    ll = label.lower().strip()
    for canon, kws in _RT_MAP:
        for kw in kws:
            if kw in ll:
                return canon
    return 'BEDROOM'  # safe default

# ── Priority matrix: (room_type) → priority for (hook, standard, showcase) ──
# 1 = always include, 2 = include if slots allow, 3 = low priority, 9 = skip
_PRIORITY = {
    'FACADE':       (1, 1, 1),
    'TERRACE':      (1, 1, 1),
    'BALCONY':      (1, 1, 1),
    'AMENITY':      (2, 2, 2),
    'LOBBY':        (3, 3, 2),
    'LIVING_DINING':(1, 1, 1),
    'LIVING':       (1, 1, 1),
    'DINING':       (3, 2, 2),
    'KITCHEN':      (2, 1, 1),
    'MASTER_BR':    (1, 1, 1),
    'MASTER_BATH':  (2, 2, 1),
    'BATHROOM':     (9, 3, 3),
    'BEDROOM':      (3, 2, 2),
    'STUDY':        (3, 3, 2),
}

# Narrative arc ordering: lower = earlier in reel
_ARC_ORDER = {
    'FACADE':1, 'AMENITY':1, 'LOBBY':2, 'LIVING_DINING':3, 'LIVING':3,
    'DINING':4, 'KITCHEN':5, 'MASTER_BR':6, 'MASTER_BATH':7,
    'BEDROOM':8, 'STUDY':8, 'BALCONY':9, 'TERRACE':10,
}

_TIER_LIMITS = {'hook': 5, 'standard': 12, 'showcase': 20}

def select_clips_for_reel(photo_labels, reel_tier='hook'):
    """
    Returns (selected, skipped).
    selected = [{label, room_type, slot_num, arc_stage}, ...]  ordered by narrative arc
    skipped  = [label, ...]
    """
    if not photo_labels:
        return [], []
    tier = reel_tier.lower()
    limit = _TIER_LIMITS.get(tier, 5)
    pri_idx = {'hook':0, 'standard':1, 'showcase':2}.get(tier, 0)

    pool = [(lbl, classify_room_type(lbl)) for lbl in photo_labels]

    # Sort by priority then arc order, then deduplicate room types (keep best)
    seen_types = {}
    for lbl, rt in pool:
        p = _PRIORITY.get(rt, (3,3,3))[pri_idx]
        if p == 9:
            continue
        if rt not in seen_types or p < seen_types[rt][0]:
            seen_types[rt] = (p, lbl)

    # Build candidates list sorted by (priority, arc_order)
    candidates = sorted(
        [(p, _ARC_ORDER.get(rt, 5), rt, lbl) for rt, (p, lbl) in seen_types.items()],
        key=lambda x: (x[0], x[1])
    )

    selected_raw = candidates[:limit]

    # Sort selected by arc order for narrative flow
    selected_raw.sort(key=lambda x: x[1])

    arc_labels = {
        'FACADE':'ARRIVE', 'LOBBY':'ARRIVE', 'AMENITY':'ARRIVE',
        'LIVING_DINING':'ENTER', 'LIVING':'ENTER', 'DINING':'ENTER',
        'KITCHEN':'INHABIT', 'BEDROOM':'INHABIT', 'STUDY':'INHABIT',
        'MASTER_BR':'RETREAT', 'MASTER_BATH':'RETREAT',
        'BALCONY':'ASPIRE', 'TERRACE':'ASPIRE',
    }

    selected = []
    for i, (p, ao, rt, lbl) in enumerate(selected_raw):
        selected.append({
            'slot_num':   i + 1,
            'label':      lbl,
            'room_type':  rt,
            'arc_stage':  arc_labels.get(rt, 'INHABIT'),
            'upload_num': i + 1,
        })

    selected_labels = {s['label'] for s in selected}
    skipped = [lbl for lbl, rt in pool if lbl not in selected_labels]
    return selected, skipped

# ── Per-room camera mechanics ─────────────────────────────
_ROOM_CAMERA_V3 = {
    # Format: camera instruction only. Scene-static clause appended by build_kling_narrative_v3.
    'FACADE':       'slow steady camera push from street level toward the entrance, camera rises at midpoint to reveal full building height. Architecture completely still. No people, no moving vehicles',
    'TERRACE':      'slow camera crane rise from terrace floor level, the city view unfurling as camera ascends. All furniture on terrace completely stationary. No wind, no fabric movement',
    'BALCONY':      'camera starts inside the room and makes a slow push toward the balcony door, then drifts to the railing edge revealing the view. Balcony furniture completely stationary. No wind effects',
    'AMENITY':      'slow camera pan across the amenity — pool surface calm and mirror-like, no ripples. All loungers and furniture completely stationary. No people',
    'LOBBY':        'slow camera dolly-in through the entrance, marble and surfaces completely still, reflections sharp and static. No people',
    'LIVING_DINING':'slow camera dolly-in from the entrance toward the far windows. All sofas, cushions, decor items and furniture completely stationary — not a single object moves. Camera movement only',
    'LIVING':       'slow camera push from doorway toward the far windows or feature wall. All furniture, cushions, plants, and decor completely stationary throughout. Camera movement only — nothing in the scene moves',
    'DINING':       'slow smooth camera arc 30 degrees around the dining table. All chairs, crockery, and table items perfectly still. No movement of any object. Camera movement only',
    'KITCHEN':      'slow camera lateral pan left to right along the full counter at counter height, then gently pulls back to wide. All appliances, utensils, and surfaces completely stationary. Camera movement only',
    'MASTER_BR':    'slow camera float from doorway toward the bed and window wall. All bedding, pillows, lamps, and furniture perfectly still — not a single object moves. Soft ambient light, camera movement only',
    'MASTER_BATH':  'slow camera pivot from doorway across the vanity to the shower or tub. All fixtures, towels, and fittings completely stationary. Reflections on tile are sharp and static. Camera movement only',
    'BEDROOM':      'slow camera push from doorway toward the bed and window. All bedding, pillows, and furniture completely stationary. Soft warm light, camera movement only',
    'STUDY':        'slow camera dolly-in toward the desk and shelves. All books, objects on desk, and furniture perfectly still. Warm lamp light, camera movement only',
}

# ── Transitions between rooms ─────────────────────────────
_TRANSITIONS_V3 = {
    ('FACADE','LOBBY'):          'Camera descends from the facade, pushing through the grand entrance',
    ('FACADE','LIVING'):         'Camera crosses the entrance threshold, the living space unfolding ahead',
    ('FACADE','LIVING_DINING'):  'Camera crosses the entrance threshold, the open-plan interior revealing itself',
    ('LOBBY','LIVING'):          'Camera continues forward through the lobby, the living space opening up',
    ('LIVING_DINING','KITCHEN'): 'Camera moves from the social zone toward the kitchen, the counter coming into view',
    ('LIVING_DINING','MASTER_BR'):'A corridor door opens, camera pushes through into the master suite',
    ('LIVING','DINING'):         'Camera flows naturally toward the dining area, the table sweeping into view',
    ('LIVING','KITCHEN'):        'Camera passes through the open arch, kitchen gleaming ahead',
    ('LIVING','MASTER_BR'):      'A corridor door opens, camera pushes through into the master suite',
    ('LIVING','BEDROOM'):        'Camera moves down the corridor, a door opening to the bedroom',
    ('DINING','KITCHEN'):        'Camera turns toward the kitchen beyond the dining space',
    ('KITCHEN','MASTER_BR'):     'Camera exits the kitchen, moving through the corridor to the master suite',
    ('KITCHEN','BEDROOM'):       'Camera moves through the corridor, a bedroom door opening ahead',
    ('MASTER_BR','MASTER_BATH'): 'Camera drifts toward the ensuite door, crossing into the private spa within',
    ('MASTER_BR','BALCONY'):     'Camera is drawn toward the glass door, the balcony glowing beyond',
    ('MASTER_BR','TERRACE'):     'Camera rises toward the terrace level, sky opening above',
    ('MASTER_BATH','BALCONY'):   'Camera moves from the spa-like bath toward the open air of the balcony',
    ('BEDROOM','BALCONY'):       'Camera floats toward the glass door, stepping into open sky',
    ('BEDROOM','TERRACE'):       'Camera moves toward the terrace access, the view opening ahead',
    ('AMENITY','FACADE'):        'Camera pulls back from the development, settling on the full building',
}

def _get_transition_v3(from_rt, to_rt):
    t = _TRANSITIONS_V3.get((from_rt, to_rt))
    if t:
        return t
    dest = {
        'FACADE':'the building exterior', 'TERRACE':'the open terrace above',
        'BALCONY':'the balcony', 'AMENITY':'the amenity spaces',
        'LOBBY':'the entrance lobby', 'LIVING_DINING':'the open-plan living and dining area',
        'LIVING':'the living room', 'DINING':'the dining area',
        'KITCHEN':'the kitchen', 'MASTER_BR':'the master suite',
        'MASTER_BATH':'the ensuite bathroom', 'BEDROOM':'the bedroom',
        'BATHROOM':'the bathroom', 'STUDY':'the study',
    }
    return f"Camera moves through to {dest.get(to_rt, 'the next space')}"

def build_kling_narrative_v3(selected, prop_name='', location='', prop_type='Residential', tone='Luxury', bhk_size=''):
    """Build the full Kling Custom Multi-Shot narrative prompt from selected clips."""
    if not selected:
        return ''
    prop_desc = ' · '.join(filter(None, [bhk_size, prop_type, prop_name, location]))
    opening = (
        f"Cinematic property reel. {prop_desc}. "
        "Camera moves through the property with smooth floating motion. "
        "Quiet luxury. No people. Natural warm lighting throughout. No text overlays."
    )
    blocks = [opening, '']
    for i, slot in enumerate(selected):
        rt  = slot['room_type']
        lbl = slot['label']
        img = f"@image{slot['upload_num']}"
        cam = _ROOM_CAMERA_V3.get(rt, 'slow gentle drift across the space')
        if i == 0:
            line = f"Open on the {lbl.lower()} — {cam} {img}."
        else:
            prev_rt = selected[i-1]['room_type']
            trans   = _get_transition_v3(prev_rt, rt)
            line    = f"{trans} — {cam} {img}."
        blocks.append(line)
    blocks.append(f"\n{tone}, 9:16, cinematic, warm lighting throughout. Hold final frame 1.5 seconds.")
    return '\n'.join(blocks)

# ── Google Flow Veo 3.1 prompt builder ──────────────────────────────────────
# Each room_type has (camera_path, static_constraint) — two separate strings
# so the final prompt can be assembled with full context from all form fields.
_FLOW_CAMERA_V4 = {
    'FACADE': (
        'slow steady push from street level toward the main entrance, camera rising from 1m to 2m height at midpoint to reveal the full building facade and scale',
        'Architecture, landscaping, and all surfaces completely stationary. No people, no moving vehicles, no flags or banners moving'
    ),
    'TERRACE': (
        'slow crane-style rise from terrace floor level, city skyline unfurling as camera ascends from 1m to 2.5m, panning 10 degrees left to right at peak to survey the panoramic view',
        'All terrace furniture, planters, and objects completely stationary. No wind, no fabric movement, no ripples in any water features'
    ),
    'BALCONY': (
        'camera begins inside the room 2m from the balcony door, slow deliberate push forward through the doorway, settling at the railing edge as the view is fully revealed',
        'All balcony furniture and objects completely stationary. No wind effects whatsoever. No curtain or fabric movement of any kind'
    ),
    'AMENITY': (
        'slow camera pan at 0.8m height sweeping left to right across the full length of the pool and amenity space, then gently pulling back to reveal the complete facility',
        'Pool surface glassy and mirror-still with absolutely no ripples. All loungers, umbrellas, and furniture stationary. No people anywhere'
    ),
    'LOBBY': (
        'slow cinematic dolly-in starting from the entrance threshold, advancing 3m at 1.5m height, marble and stone surfaces gleaming, reflections crisp and undisturbed',
        'All lobby surfaces, furnishings, and decor completely stationary. Reflections sharp and perfectly static. No people'
    ),
    'LIVING_DINING': (
        'smooth dolly push from the entrance threshold toward the far windows, camera at 1.2m height advancing 4m over 8 seconds while rising gently to 1.5m at midpoint, revealing the full depth and breadth of the open-plan space',
        'Every sofa, cushion, dining chair, table item, vase, lamp, rug, and plant — 100% stationary, zero object motion throughout the entire clip. Only the camera moves'
    ),
    'LIVING': (
        'slow cinema-grade dolly from the doorway toward the feature wall or floor-to-ceiling windows, camera at 1.2m advancing 3m and rising 15cm at midpoint to frame the room symmetrically against the light',
        'Every sofa cushion, lamp, vase, plant, rug, throw pillow, and decorative object — absolutely stationary throughout all 8 seconds. Camera movement only — nothing in the scene moves'
    ),
    'DINING': (
        'slow smooth arc 25 degrees clockwise around the dining table at 1.3m height, table and chairs perfectly centered in frame throughout the arc, ending on the hero side of the table',
        'All chairs, crockery, centrepiece, and every table item perfectly still. Zero object movement. Camera arc only'
    ),
    'KITCHEN': (
        'lateral pan from left to right along the full kitchen counter at 1.1m height, slow and deliberate capturing every appliance and surface, then a gentle 0.5m pullback at the end to reveal the full kitchen in wide',
        'All appliances, cabinetry doors, countertop items, and every surface completely stationary. Camera lateral movement only'
    ),
    'MASTER_BR': (
        'slow floating push from the doorway toward the bed headboard and window wall, camera at 1.3m height advancing 3.5m over 8 seconds with a subtle rightward drift to frame the bed against the window as the hero composition',
        'All bedding, pillows, throws, bedside lamps, artwork, wardrobe doors, and every single room object — perfectly still, zero movement throughout. Soft warm ambient light. Camera movement only'
    ),
    'MASTER_BATH': (
        'slow pivot starting at the doorway, camera sweeping 40 degrees from the vanity sink across to the shower or freestanding tub, ending with the premium hero fixture filling one-third of the frame',
        'All fixtures, fittings, towels, accessories, and tile reflections completely stationary. No steam, no water movement of any kind. Camera pivot only'
    ),
    'BEDROOM': (
        'slow push from doorway toward the bed headboard and window, camera at 1.2m advancing 2.5m, framing the bed with the window providing backlight and depth',
        'All bedding, pillows, side tables, lamps, and furniture completely stationary. Soft warm ambient light. Camera movement only'
    ),
    'BATHROOM': (
        'slow arc from the doorway sweeping 30 degrees across the vanity, mirror, and primary fixture at 1.1m height',
        'All fixtures, fittings, towels, and surfaces completely stationary. Mirror reflection crisp and static. Camera arc only'
    ),
    'STUDY': (
        'slow dolly-in from the door toward the desk surface and shelving wall, camera at 1.2m advancing 2m, warm desk lamp creating depth and the shelves providing visual texture in background',
        'All books, desk objects, shelving items, lamp, chair, and furniture perfectly still. Camera movement only'
    ),
}

_FLOW_TONE_ATMOSPHERE = {
    'Luxury':     'quiet luxury, premium aspirational, golden warm tones, soft shadow depth',
    'Family':     'warm and welcoming, bright natural daylight, comfortable and liveable',
    'Affordable': 'clean and bright, aspirational yet honest, natural daylight, value-forward',
    'Investment': 'clean professional lines, strong rental-yield impression, well-maintained finish',
}

_FLOW_STYLE_LIGHTING = {
    'Modern/Contemporary': 'cool-warm balanced interior lighting, crisp clean reflections, no clutter',
    'Minimalist':          'diffused soft ambient light, high contrast whites, clean lines emphasized',
    'Traditional/Classic': 'warm amber interior tones, rich material textures and moulding detail visible',
    'Industrial':          'directional warm spotlighting, exposed material texture and patina emphasis',
}

_FLOW_FURNISHED_ANCHOR = {
    'Fully Furnished':          'exactly as furnished and staged in the photograph — preserve every piece of furniture, every decorative object, every finish exactly as shown',
    'Semi-Furnished':           'exactly as shown in the photograph — preserve all present furniture; do not add or hallucinate any furniture that is not visible',
    'Unfurnished':               'as an empty architectural space exactly as photographed — clean bare floors and walls, no furniture added whatsoever, pure architectural and spatial quality',
    'Shell/Under Construction':  'at raw construction stage exactly as photographed — bare concrete or brick surfaces, structural elements only, absolutely no finishes or furniture added',
}

_FLOW_PRICE_GRADE = {
    '₹3Cr+':      'Ultra-premium grade — every surface and detail must read as high-end luxury.',
    '₹1–3Cr':     'Premium residential grade — polished, aspirational finish.',
    '₹50L–1Cr':   'Mid-market aspirational — clean, bright, and well-presented.',
    'Under ₹50L': 'Clean and bright value presentation.',
    'Commercial':  'Professional commercial grade — clean, precise, business-quality.',
}

def build_flow_prompt_v4(room_type, label, tone='Family', prop_type='Residential',
                          location='', bhk_size='', interior_style='Modern/Contemporary',
                          furnished_status='Fully Furnished', price_bracket='',
                          special_note=''):
    """
    Build a detailed ~110-word structured Veo 3.1 Fast prompt for Google Flow.
    Components: anchor + furnished_ctx + camera_path + static_constraint +
                people_rule + quality + lighting + price_grade + tone_location +
                special_note + audio_rule + format
    """
    cam_move, static_clause = _FLOW_CAMERA_V4.get(room_type, (
        'slow gentle drift across the space at 1.2m height, advancing 2m over 8 seconds',
        'All furniture and objects completely stationary. Camera movement only'
    ))
    furnished_ctx  = _FLOW_FURNISHED_ANCHOR.get(furnished_status,
        'exactly as furnished in the photograph — preserve all furniture and decor')
    atmosphere     = _FLOW_TONE_ATMOSPHERE.get(tone, 'aspirational residential quality')
    lighting_mod   = _FLOW_STYLE_LIGHTING.get(interior_style, 'warm natural interior lighting')
    price_str      = _FLOW_PRICE_GRADE.get(price_bracket, '')
    location_tag   = f'{location} {prop_type.lower()}' if location else prop_type.lower()
    bhk_tag        = f'{bhk_size} ' if bhk_size else ''
    note_str       = f' Note: {special_note}.' if special_note else ''

    prompt = (
        f"[STYLE & HARDWARE] Shot on ARRI Alexa Mini LF, 35mm spherical architectural lens, ultra-high-definition rendering. {lighting_mod}.{' ' + price_str if price_str else ''} {atmosphere} — {bhk_tag}{location_tag}.{note_str} Clean high-fidelity surface textures.\n"
        f"[SPATIAL CONTEXT — complete Step 0 checklist before copying]\n"
        f"[SUBJECT STABILITY] Animate this exact {label.lower()} {furnished_ctx}. {cam_move}. {static_clause}.\n"
        f"[COMPOSITION] 9:16 vertical portrait frame, 8 seconds, no people anywhere in frame, no ambient audio, no music — complete silence."
    )
    return prompt

def build_flow_prompts_for_order(selected, tone='Family', prop_type='Residential',
                                  location='', bhk_size='', interior_style='Modern/Contemporary',
                                  furnished_status='Fully Furnished', price_bracket='',
                                  special_note=''):
    """Returns {slot_num: prompt_string} for all selected clips."""
    return {
        c['slot_num']: build_flow_prompt_v4(
            room_type        = c['room_type'],
            label            = c['label'],
            tone             = tone,
            prop_type        = prop_type,
            location         = location,
            bhk_size         = bhk_size,
            interior_style   = interior_style,
            furnished_status = furnished_status,
            price_bracket    = price_bracket,
            special_note     = special_note,
        )
        for c in selected
    }

# Keep legacy wrappers so old orders still render without errors
def _classify_room(label):
    return classify_room_type(label).lower().replace('_br','_bedroom').replace('facade','exterior').replace('living_dining','living').replace('master_bath','bathroom').replace('master_br','master_bedroom').replace('balcony','terrace')

def compute_omni_slots(photo_labels):
    selected, skipped = select_clips_for_reel(photo_labels, 'hook')
    slots = [{
        'slot_num':   s['slot_num'],
        'slot_name':  s['arc_stage'],
        'arc':        s['arc_stage'],
        'label':      s['label'],
        'canonical':  s['room_type'].lower(),
        'upload_num': s['upload_num'],
    } for s in selected]
    return slots, skipped

def generate_omni_narrative(slots, prop_name='', location='', prop_type='Residential', tone='Luxury'):
    selected = [{
        'slot_num':   s['slot_num'],
        'label':      s['label'],
        'room_type':  s['canonical'].upper(),
        'arc_stage':  s['arc'],
        'upload_num': s['upload_num'],
    } for s in slots]
    return build_kling_narrative_v3(selected, prop_name=prop_name, location=location,
                                    prop_type=prop_type, tone=tone)

# ─────────────────────────────────────────────────────────

SPACE_TYPE_RENDER_DEFAULTS = {
    'bedroom': 2, 'living_room': 4, 'kitchen': 2,
    'dining': 2, 'bathroom': 2, 'office': 3,
    'restaurant': 6, 'retail': 4, 'lobby': 6, 'other': 2,
}

# ── PROMPT BUILDER ────────────────────────────────────────
WALL_OPPOSITES = {'north':'south','south':'north','east':'west','west':'east'}

def build_render_prompt(intake, spatial, pov='A'):
    space_name  = intake.get('space_name', 'Interior Space')
    space_type  = intake.get('space_type', 'room').replace('_', ' ')
    style       = intake.get('style_direction', 'warm minimalism — natural materials, matte finishes')
    hero        = intake.get('hero_element', '')
    notes       = intake.get('special_notes', '')

    entry_wall     = spatial.get('entry_door_wall', 'south').lower()
    furniture_wall = spatial.get('primary_furniture_wall', 'north').lower()
    openings_wall  = spatial.get('wall_openings', 'north').lower()
    far_wall       = WALL_OPPOSITES.get(entry_wall, 'north')

    if pov == 'A':
        cam_pos  = f"just inside the entry door on the {entry_wall} wall"
        cam_dir  = f"facing {far_wall} toward the far wall"
        fg_note  = f"Entry door visible at left edge of frame ({entry_wall} wall)"
        bg_note  = f"{far_wall.capitalize()} wall — {openings_wall} wall openings / glass / windows in far background"
    else:
        cam_pos  = f"at the {far_wall} wall, near the {openings_wall} wall openings"
        cam_dir  = f"facing {entry_wall} toward the entry door"
        fg_note  = f"Wall openings / glass doors behind camera ({openings_wall} wall)"
        bg_note  = f"{entry_wall.capitalize()} wall — entry door visible in far background"

    prompt = f"""Photorealistic architectural interior render, 16:9 wide-angle. High resolution. Warm natural lighting.

CAMERA POSITION: {cam_pos}
CAMERA DIRECTION: {cam_dir}

SPACE: {space_name} ({space_type})

SPATIAL LAYOUT — follow exactly, do not mirror:
- NEAR FOREGROUND: {fg_note}
- PRIMARY FURNITURE: against the {furniture_wall} wall (dominant furniture cluster)
- WALL OPENINGS: {openings_wall} wall (windows / glass doors / balcony)
- FAR BACKGROUND: {bg_note}

STYLE: {style}{chr(10) + "HERO ELEMENT: " + hero + " — make this the focal point of the render" if hero else ""}
{chr(10) + "SPECIAL NOTES: " + notes if notes else ""}

LIGHTING: Warm 2700K. Natural light from wall openings. Soft ambient fill. No harsh shadows.

QUALITY REQUIREMENTS:
- Photorealistic, not illustrated or stylised
- Correct architectural proportions
- Materials must appear natural — matte stone, warm wood, linen textures
- No over-saturation

FORBIDDEN — do not include any of these:
- No plants or indoor greenery
- No chrome or metallic hardware (unless specified in style)
- No high-gloss or lacquered surfaces
- No patterned rugs or colourful textiles (unless specified)
- No TV on wall (unless client specified)
- No modern pendant with exposed bulb
- No wallpaper or printed wall treatments
- No dark wood floors (unless specified)
- No staged accessories like books, candles, fruit bowls"""
    return prompt.strip()
