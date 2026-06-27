# ── SUPPORT / PAYMENT CONFIG ──────────────────────────────
SUPPORT_WHATSAPP = os.environ.get('SUPPORT_WHATSAPP', '919999999999')

# ── TEST ACCOUNTS (dev only — remove test pilot before public launch) ──
TEST_CLIENT_PHONE  = '9876543210'   # Free Pass client — phone+PIN login
TEST_CLIENT_PIN    = '1234'
TEST_PILOT_EMAIL   = 'opuluxe24@gmail.com'
TEST_PILOT_PASS    = '1234'

# ── EDIT CREDIT PACKAGES ─────────────────────────────
PRICE_EDIT_CREDIT_1 = 30000   # ₹300 — buy 1 edit
PRICE_EDIT_CREDIT_3 = 50000   # ₹500 — buy 3 edits (best value)
INITIAL_FREE_CREDITS = 3      # granted on first payment  # e.g. 919876543210
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
FRONTEND_URL  = os.environ.get('FRONTEND_URL', 'http://localhost:5051')

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
# Cluster 2 — E-commerce
PRICE_BG_CLEANUP        = 7900    # ₹79/image
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
