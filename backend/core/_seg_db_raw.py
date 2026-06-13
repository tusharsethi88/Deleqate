# ── DATABASE ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deleqate_v2.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('admin','pilot','client')),
            account_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            edit_credits INTEGER DEFAULT 0,
            session_version INTEGER DEFAULT 0,
            UNIQUE(email, role)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            client_phone TEXT,
            client_email TEXT,
            name TEXT,
            phone TEXT,
            email TEXT,
            task_type TEXT,
            task TEXT,
            intake_data TEXT,
            render_count INTEGER DEFAULT 2,
            price_per_unit INTEGER DEFAULT 24900,
            total_price INTEGER DEFAULT 49800,
            pilot_payout INTEGER DEFAULT 0,
            brief_text TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            assigned_pilot_id INTEGER,
            qc_notes TEXT,
            delivered_at TIMESTAMP,
            completed_at TIMESTAMP,
            prompt_a_output TEXT,
            wall_inventory_output TEXT,
            moodboard_output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users(id),
            FOREIGN KEY (assigned_pilot_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            attachment_type TEXT DEFAULT 'general',
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS pilot_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            pov TEXT NOT NULL,
            spatial_facts TEXT,
            generated_prompt TEXT,
            flow_prompt TEXT,
            qc_result TEXT,
            qc_data TEXT,
            render_filename TEXT,
            step_status TEXT DEFAULT 'pending',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS deliverables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            pilot_id INTEGER NOT NULL,
            pov TEXT DEFAULT 'A',
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_size INTEGER,
            notes TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (pilot_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_by INTEGER,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS otp_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            otp TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    existing = conn.execute('SELECT id FROM users WHERE email=? AND role=?', (ADMIN_EMAIL, 'admin')).fetchone()
    if not existing:
        conn.execute(
            'INSERT INTO users (email, password_hash, name, phone, role) VALUES (?,?,?,?,?)',
            (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), 'Abhimanyu Dabas', '9871722766', 'admin')
        )

    # ── Seed test pilot (dev only — remove before public launch) ──────
    if not conn.execute('SELECT id FROM users WHERE email=? AND role=?', (TEST_PILOT_EMAIL, 'pilot')).fetchone():
        conn.execute(
            'INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)',
            (TEST_PILOT_EMAIL, generate_password_hash(TEST_PILOT_PASS), 'Test Pilot', '9000000001', 'pilot', 'active')
        )

    # ── Seed test client (phone+PIN, dev only) ─────────────────────────
    _tc_email = f'{TEST_CLIENT_PHONE}@client.deleqate'
    if not conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (TEST_CLIENT_PHONE, 'client')).fetchone():
        conn.execute(
            'INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)',
            (_tc_email, generate_password_hash(TEST_CLIENT_PIN), 'Test Client', TEST_CLIENT_PHONE, 'client', 'active')
        )

    conn.commit()
    # Migration: add missing columns to existing DBs
    cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
    migrations = [
        ("pilot_payout",     "ALTER TABLE orders ADD COLUMN pilot_payout INTEGER DEFAULT 0"),
        ("client_name",      "ALTER TABLE orders ADD COLUMN client_name TEXT"),
        ("client_phone",     "ALTER TABLE orders ADD COLUMN client_phone TEXT"),
        ("client_email",     "ALTER TABLE orders ADD COLUMN client_email TEXT"),
        ("task_type",        "ALTER TABLE orders ADD COLUMN task_type TEXT"),
        ("brief_text",       "ALTER TABLE orders ADD COLUMN brief_text TEXT"),
        ("deadline",         "ALTER TABLE orders ADD COLUMN deadline TEXT"),
        ("completed_at",     "ALTER TABLE orders ADD COLUMN completed_at TIMESTAMP"),
        ("assigned_at",      "ALTER TABLE orders ADD COLUMN assigned_at TIMESTAMP"),
        ("prompt_a_output",  "ALTER TABLE orders ADD COLUMN prompt_a_output TEXT"),
        ("wall_inventory_output", "ALTER TABLE orders ADD COLUMN wall_inventory_output TEXT"),
        ("moodboard_output", "ALTER TABLE orders ADD COLUMN moodboard_output TEXT"),
    ]
    for col, sql in migrations:
        if col not in cols:
            try:
                conn.execute(sql)
            except Exception:
                pass
                
    step_cols = [r[1] for r in conn.execute("PRAGMA table_info(pilot_steps)").fetchall()]
    step_migrations = [
        ("flow_prompt", "ALTER TABLE pilot_steps ADD COLUMN flow_prompt TEXT"),
        ("labeled_plan_filename", "ALTER TABLE pilot_steps ADD COLUMN labeled_plan_filename TEXT")
    ]
    for col, sql in step_migrations:
        if col not in step_cols:
            try:
                conn.execute(sql)
            except Exception:
                pass

    # ── users: edit credit balance ────────────────────────
    user_cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
    if 'edit_credits' not in user_cols:
        try: conn.execute('ALTER TABLE users ADD COLUMN edit_credits INTEGER DEFAULT 0')
        except Exception: pass
    # M-2: per-user session version — bumped on password reset to kill old sessions
    if 'session_version' not in user_cols:
        try: conn.execute('ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 0')
        except Exception: pass

    # H-2: ledger of processed PayU transactions — makes payment_success idempotent
    conn.execute('''CREATE TABLE IF NOT EXISTS payments (
        txnid TEXT PRIMARY KEY,
        mihpayid TEXT,
        order_id INTEGER,
        client_action TEXT,
        amount TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # ── users: migrate UNIQUE(email) → UNIQUE(email, role) ─
    # Allows same email to register independently as customer, pilot, and admin.
    # Robust: handles a dangling users_old left by a previously failed migration run.

    # Step 1 — rebuild any table whose FK constraints point to users_old
    # Root cause: SQLite 3.26+ auto-rewrites FK refs when a table is renamed.
    # After "ALTER TABLE users RENAME TO users_old", orders/deliverables/etc end up
    # with "REFERENCES users_old(id)" baked into their schema. After users_old is
    # later dropped, every INSERT into those tables fails with
    # "no such table: main.users_old".  Fix by physically rebuilding each table:
    # rename → recreate with corrected FK → copy all columns → drop old.
    affected_fk = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%REFERENCES users_old%'"
    ).fetchall()
    if affected_fk:
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            for row in affected_fk:
                tbl      = row['name']
                orig_sql = row['sql'] or ''
                # Get ALL current columns (including any added by ALTER TABLE ADD COLUMN)
                cols     = [r[1] for r in conn.execute(f"PRAGMA table_info('{tbl}')").fetchall()]
                col_list = ', '.join(f'"{c}"' for c in cols)
                tmp      = f"_{tbl}_fk_repair"
                # Build CREATE for temp table: fix FK text + add any missing migrated columns
                fixed_create = orig_sql.replace('REFERENCES users_old', 'REFERENCES users')
                # Replace table name in CREATE statement
                fixed_create = fixed_create.replace(
                    f'CREATE TABLE {tbl}', f'CREATE TABLE "{tmp}"', 1
                ).replace(
                    f'CREATE TABLE "{tbl}"', f'CREATE TABLE "{tmp}"', 1
                ).replace(
                    f'CREATE TABLE [{tbl}]', f'CREATE TABLE "{tmp}"', 1
                )
                # Add columns present in current table but missing from original CREATE sql
                extra_cols = []
                for c in cols:
                    if f'"{c}"' not in fixed_create and f' {c} ' not in fixed_create and f'({c}' not in fixed_create:
                        col_info = conn.execute(f"PRAGMA table_info('{tbl}')").fetchall()
                        for ci in col_info:
                            if ci[1] == c:
                                col_type = ci[2] or 'TEXT'
                                dflt = f" DEFAULT {ci[4]}" if ci[4] is not None else ''
                                extra_cols.append(f'    "{c}" {col_type}{dflt}')
                                break
                if extra_cols:
                    fixed_create = fixed_create.rstrip().rstrip(')')
                    fixed_create += ',\n' + ',\n'.join(extra_cols) + '\n)'
                conn.execute(fixed_create)
                conn.execute(f'INSERT INTO "{tmp}" ({col_list}) SELECT {col_list} FROM "{tbl}"')
                conn.execute(f'DROP TABLE "{tbl}"')
                conn.execute(f'ALTER TABLE "{tmp}" RENAME TO "{tbl}"')
                print(f"[MIGRATION] Rebuilt {tbl}: FK users_old → users")
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception as e:
            conn.execute("PRAGMA foreign_keys = ON")
            print(f"[MIGRATION] FK rebuild failed: {e}")

    # Step 2 — clean up any dangling users_old table left by a prior crashed migration
    # NOTE: use individual execute() calls (not executescript) so PRAGMA foreign_keys = OFF
    # is applied on the live connection object — executescript doesn't reliably override
    # a connection-level PRAGMA already set to ON.
    users_old_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users_old'"
    ).fetchone()
    if users_old_exists:
        users_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            if users_exists:
                conn.execute("DROP TABLE IF EXISTS users_old")
            else:
                conn.execute("ALTER TABLE users_old RENAME TO users")
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")
            print("[MIGRATION] Cleaned up dangling users_old table.")
        except Exception as e:
            conn.execute("PRAGMA foreign_keys = ON")
            print(f"[MIGRATION] Could not clean up users_old: {e}")

    # Step 3 — run the schema migration if the old UNIQUE(email) constraint is still in place
    users_schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if users_schema and 'email TEXT UNIQUE' in (users_schema['sql'] or ''):
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("ALTER TABLE users RENAME TO users_old")
            conn.execute("""
                CREATE TABLE users (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    email          TEXT NOT NULL,
                    password_hash  TEXT NOT NULL,
                    name           TEXT NOT NULL,
                    phone          TEXT DEFAULT '',
                    role           TEXT NOT NULL CHECK(role IN ('admin','pilot','client')),
                    account_status TEXT DEFAULT 'active',
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    edit_credits   INTEGER DEFAULT 0,
                    UNIQUE(email, role)
                )
            """)
            conn.execute("""
                INSERT INTO users (id,email,password_hash,name,phone,role,account_status,created_at,edit_credits)
                    SELECT id,email,password_hash,name,phone,role,account_status,created_at,
                           COALESCE(edit_credits,0) FROM users_old
            """)
            conn.execute("DROP TABLE IF EXISTS users_old")
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")
            print("[MIGRATION] users UNIQUE(email) → UNIQUE(email, role) applied successfully.")
        except Exception as e:
            conn.execute("PRAGMA foreign_keys = ON")
            print(f"[MIGRATION] users migration failed: {e}")

    # ── orders: payment tracking fields ────────────────────
    for col, sql in [
        ("payment_ref",       "ALTER TABLE orders ADD COLUMN payment_ref TEXT"),
        ("payment_method",    "ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'whatsapp_upi'"),
        ("client_action",     "ALTER TABLE orders ADD COLUMN client_action TEXT"),
        ("rejection_remark",  "ALTER TABLE orders ADD COLUMN rejection_remark TEXT"),
    ]:
        if col not in cols:
            try: conn.execute(sql)
            except Exception: pass

    # ── edit_requests: per-deliverable client edit remarks ─
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS edit_requests (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id              INTEGER NOT NULL,
            deliverable_id        INTEGER,
            remark                TEXT,
            attachment_filename   TEXT,
            attachment_original_name TEXT,
            attachment_size       INTEGER,
            created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );
    ''')

    # ── order_attachments: room/area label ─────────────────
    att_cols = [r[1] for r in conn.execute("PRAGMA table_info(order_attachments)").fetchall()]
    for col, sql in [("file_label", "ALTER TABLE order_attachments ADD COLUMN file_label TEXT")]:
        if col not in att_cols:
            try: conn.execute(sql)
            except Exception: pass

    # ── deliverables: room label + per-image QC state ──────
    del_cols = [r[1] for r in conn.execute("PRAGMA table_info(deliverables)").fetchall()]
    for col, sql in [
        ("file_label",  "ALTER TABLE deliverables ADD COLUMN file_label TEXT"),
        ("img_status",  "ALTER TABLE deliverables ADD COLUMN img_status TEXT DEFAULT 'pending'"),
        ("img_remark",  "ALTER TABLE deliverables ADD COLUMN img_remark TEXT"),
    ]:
        if col not in del_cols:
            try: conn.execute(sql)
            except Exception: pass

    # ── orders: QC annotation image ────────────────────────
    ord_cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
    if 'qc_annotation_filename' not in ord_cols:
        try: conn.execute("ALTER TABLE orders ADD COLUMN qc_annotation_filename TEXT")
        except Exception: pass

    # ── skus: SKU catalogue (admin-editable) ───────────────
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS skus (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_key    TEXT UNIQUE NOT NULL,
            label       TEXT NOT NULL,
            cluster     TEXT NOT NULL,
            price_paisa INTEGER NOT NULL,
            price_type  TEXT NOT NULL DEFAULT 'fixed',
            price_label TEXT DEFAULT '',
            is_active   INTEGER NOT NULL DEFAULT 1,
            sort_order  INTEGER DEFAULT 0,
            note        TEXT DEFAULT ''
        );
    ''')

    # Seed SKUs if table is empty
    if not conn.execute('SELECT 1 FROM skus LIMIT 1').fetchone():
        _seed = [
            ('virtual_staging',    'Virtual Staging',             'Real Estate',       PRICE_VIRTUAL_STAGING,      'fixed',   '4-room staging pack',    1,  1),
            ('property_reel',      'Property Marketing Reel',     'Real Estate',       PRICE_PROPERTY_REEL_HOOK,   'fixed',   'reel (base price)',       1,  2),
            ('property_social_card','Property Social Card Pack',  'Real Estate',       PRICE_PROPERTY_SOCIAL_CARD, 'fixed',   '2 social cards',          1,  3),
            ('bg_cleanup',         'Background Cleanup',          'E-commerce',        PRICE_BG_CLEANUP,           'image',   'per image',               1,  4),
            ('product_listing',    'Product Listing Creation',    'E-commerce',        PRICE_PRODUCT_LISTING,      'product', 'per product',             1,  5),
            ('product_mockup',     'Product Lifestyle Mockup',    'E-commerce',        PRICE_PRODUCT_MOCKUP,       'image',   'per mockup',              1,  6),
            ('instagram_carousel', 'Instagram Carousel Design',   'SMB Visual Content',PRICE_INSTAGRAM_CAROUSEL,   'fixed',   'carousel',                1,  7),
            ('brand_demo_video',   'Brand Demo Video',            'SMB Visual Content',PRICE_BRAND_DEMO_VIDEO,     'fixed',   'video',                   1,  8),
            ('announcement_pack',  'Announcement Pack',           'SMB Visual Content',PRICE_ANNOUNCEMENT_PACK,    'fixed',   '3-piece pack',            1,  9),
            ('brand_starter_kit',  'Brand Starter Kit',           'Personal & Brand',  PRICE_BRAND_STARTER_KIT,    'fixed',   'brand kit',               1, 10),
            ('menu_design',        'Menu Design',                 'Personal & Brand',  PRICE_MENU_DESIGN,          'fixed',   'menu',                    1, 11),
            ('podcast_reel',       'Podcast Highlight Reel',      'Personal & Brand',  PRICE_PODCAST_REEL,         'fixed',   'highlight reel',          1, 12),
        ]
        conn.executemany(
            'INSERT INTO skus (task_key, label, cluster, price_paisa, price_type, price_label, is_active, sort_order) VALUES (?,?,?,?,?,?,?,?)',
            _seed
        )

    # ── AutoPilot: status heartbeat table ─────────────────────
    conn.execute('''CREATE TABLE IF NOT EXISTS autopilot_status (
        id          INTEGER PRIMARY KEY,
        status      TEXT DEFAULT 'offline',
        last_beat   TIMESTAMP,
        agent_email TEXT,
        tasks_done  INTEGER DEFAULT 0
    )''')

    # ── AutoPilot: seed pilot account ─────────────────────────
    _ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
    _ap_pass  = os.environ.get('AUTOPILOT_PILOT_PASSWORD', 'Deleqate@2026')
    if not conn.execute("SELECT id FROM users WHERE email=? AND role='pilot'", (_ap_email,)).fetchone():
        conn.execute(
            'INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)',
            (_ap_email, generate_password_hash(_ap_pass), 'AutoPilot', '0000000000', 'pilot', 'active')
        )

    conn.commit()
    conn.close()

def sync_pricing_from_db():
    """Load admin-edited SKU prices/labels from DB into in-memory maps (called at startup + after edits)."""
    conn = get_db()
    rows = conn.execute('SELECT task_key, price_paisa, price_type, price_label, label FROM skus').fetchall()
    conn.close()
    for s in rows:
        PRICING_MAP[s['task_key']] = (s['price_paisa'], s['price_type'], s['price_label'])
        TASK_LABELS[s['task_key']] = s['label']

init_db()
# sync_pricing_from_db() is called after PRICING_MAP is defined (see below)

# ── AutoPilot: 10-minute auto-assign background thread ────────────────────────
def _autopilot_auto_assign_worker():
    """
    Runs forever in a daemon thread.
    Every 60 s: find orders that have been sitting unassigned for 10+ minutes
    and auto-assign them to the AutoPilot pilot account.
    Configurable via AUTO_ASSIGN_MINUTES env var (default 10).
    """
    import time as _time
    delay_minutes = int(os.environ.get('AUTO_ASSIGN_MINUTES', '10'))
    delay_seconds = delay_minutes * 60

    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.row_factory = sqlite3.Row

            ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
            pilot = conn.execute(
                "SELECT id FROM users WHERE email=? AND role='pilot' AND account_status='active'",
                (ap_email,)
            ).fetchone()

            if pilot:
                pilot_id = pilot['id']
                # Orders that are still unassigned after delay_seconds
                unassigned = conn.execute("""
                    SELECT id, status, task FROM orders
                    WHERE assigned_pilot_id IS NULL
                      AND status = 'pending'
                      AND created_at <= datetime('now', ?, 'localtime')
                """, (f'-{delay_seconds} seconds',)).fetchall()

                for row in unassigned:
                    conn.execute(
                        """UPDATE orders
                           SET assigned_pilot_id=?, status='assigned',
                               assigned_at=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (pilot_id, row['id'])
                    )
                    conn.execute(
                        """INSERT INTO status_log (order_id, old_status, new_status, note)
                           VALUES (?,?,?,?)""",
                        (row['id'], row['status'], 'assigned',
                         f'Auto-assigned to AutoPilot — unassigned for {delay_minutes}+ minutes')
                    )
                    print(f'[AutoPilot] Auto-assigned Order #{row["id"]} → AutoPilot', flush=True)

                conn.commit()
            conn.close()
        except Exception as _e:
            print(f'[AutoPilot] Auto-assign error: {_e}', flush=True)

        _time.sleep(60)

_ap_thread = threading.Thread(target=_autopilot_auto_assign_worker, daemon=True, name='autopilot-autoassign')
_ap_thread.start()

# ── FLASK-LOGIN ───────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, name, role, phone=''):
        self.id = id; self.email = email; self.name = name
        self.role = role; self.phone = phone

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if row:
        # M-2: sessions carry the session_version captured at login. A password
        # reset bumps the DB value, instantly invalidating every older session.
        try:
            db_sv = row['session_version'] or 0
        except (IndexError, KeyError):
            db_sv = 0
        if session.get('_sv', 0) != db_sv:
            return None
        return User(row['id'], row['email'], row['name'], row['role'], row['phone'])

def _do_login(row):
    """Single login path: logs the user in and pins the session to the
    user's current session_version (see load_user / M-2)."""
    user = User(row['id'], row['email'], row['name'], row['role'], row['phone'])
    login_user(user)
    try:
        session['_sv'] = row['session_version'] or 0
    except (IndexError, KeyError):
        session['_sv'] = 0

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def dashboard_for(role):
    return {'admin':'admin_home','pilot':'pilot_dashboard_v2','client':'client_orders'}.get(role,'index')

# ── B-07: CSRF protection ─────────────────────────────────
def get_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=get_csrf_token)

def csrf_protect(f):
    """Validate CSRF token on all state-changing requests."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = (
                request.headers.get('X-CSRFToken') or
                request.form.get('csrf_token') or
                (request.get_json(silent=True) or {}).get('csrf_token')
            )
            expected = session.get('_csrf_token', '')
            if not token or not expected or not hmac.compare_digest(str(token), str(expected)):
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'CSRF validation failed'}), 403
                flash('Session expired. Please try again.', 'error')
                return redirect(request.referrer or url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── H-1: GLOBAL CSRF ENFORCEMENT ──────────────────────────
# Every state-changing request is validated here, so no route can be
# forgotten. The per-route @csrf_protect decorators remain as harmless
# defence-in-depth. External payment-gateway callbacks (PayU POSTs from
# the user's browser after a cross-site redirect, authenticated by the
# reverse hash instead) are exempt.
CSRF_EXEMPT_ENDPOINTS = {
    'payment_success', 'payment_failure',
    # AutoPilot endpoints authenticate via X-AutoPilot-Token header, not session/CSRF
    'api_autopilot_deliver', 'api_autopilot_qc_pass', 'api_autopilot_qc_fail',
    'api_autopilot_heartbeat', 'api_autopilot_spatial',
}

@app.before_request
def _global_csrf_check():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS or request.endpoint == 'static':
        return None
    token = (
        request.headers.get('X-CSRFToken') or
        request.form.get('csrf_token') or
        (request.get_json(silent=True) or {}).get('csrf_token')
    )
    expected = session.get('_csrf_token', '')
    if not token or not expected or not hmac.compare_digest(str(token), str(expected)):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({'error': 'CSRF validation failed'}), 403
        flash('Session expired. Please try again.', 'error')
        return redirect(request.referrer or url_for('login'))
    return None

def log_status(conn, order_id, old, new, by=None, note=''):
    conn.execute('INSERT INTO status_log (order_id,old_status,new_status,changed_by,note) VALUES (?,?,?,?,?)',
                 (order_id, old, new, by, note))

# ═══════════════════════════════════════════════════════════
# FILE SERVING ROUTES
# ═══════════════════════════════════════════════════════════
# Unauthenticated file routes removed — authenticated versions at bottom of file

# ═══════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════

def get_hero_video_url():
    """Return the URL of the uploaded hero video, or None if none exists."""
    upload_dir = app.config['UPLOAD_FOLDER']
    for ext in ('mp4', 'webm', 'mov', 'ogg'):
        fname = f'hero_video.{ext}'
        if os.path.exists(os.path.join(upload_dir, fname)):
            return f'/uploads/{fname}'
    return None

def get_hero_images():
    """Return (before_url, after_url) from a real delivered/approved order, or (None, None)."""
    try:
        conn = get_db()
        # Find the most recently delivered/approved order that has at least one deliverable
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
        # After image: first deliverable (image)
        after_row = conn.execute(
            "SELECT filename FROM deliverables WHERE order_id=? AND filename NOT LIKE '%.mp4' AND filename NOT LIKE '%.webm' ORDER BY id ASC LIMIT 1",
            (oid,)
        ).fetchone()
        # Before image: first client input photo (room_photo, property_photo, or any attachment)
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
        after_url  = f'/api/hero-img/after/{after_row["filename"]}'  if after_row  else None
        before_url = f'/api/hero-img/before/{before_row["filename"]}' if before_row else None
        return before_url, after_url
    except Exception:
        return None, None

@app.route('/api/hero-img/<string:which>/<path:filename>')
@rate_limit(limit=60, window=60)
def hero_img(which, filename):
    """Public (no login) route for serving hero showcase images on the homepage.
    Upscales small images to TARGET_W×TARGET_H using Lanczos so they look crisp full-bleed."""
    from PIL import Image as _PILImage
    import io as _io

    folder = app.config['DELIVERABLES_FOLDER'] if which == 'after' else app.config['UPLOAD_FOLDER']

    # M-1: PIL.open is not traversal-safe like send_from_directory — resolve the
    # path and refuse anything outside the intended folder ('..' segments etc.)
    # on this unauthenticated route.
    real_folder = os.path.realpath(folder)
    src_path    = os.path.realpath(os.path.join(folder, filename))
    if not src_path.startswith(real_folder + os.sep):
        abort(404)

    TARGET_W, TARGET_H = 1920, 1080  # full HD — covers any laptop/desktop viewport

    # Cache resized image in uploads/hero_cache/ to avoid re-processing every request
    cache_dir  = os.path.join(app.config['UPLOAD_FOLDER'], 'hero_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_name = which + '_' + hashlib.md5(filename.encode()).hexdigest() + '.jpg'
    cache_path = os.path.join(cache_dir, cache_name)

    if not os.path.exists(cache_path):
        try:
            img = _PILImage.open(src_path).convert('RGB')
            src_w, src_h = img.size

            # Scale so the image *covers* 1920×1080 (same logic as object-fit:cover)
            scale = max(TARGET_W / src_w, TARGET_H / src_h)
            new_w = int(src_w * scale)
            new_h = int(src_h * scale)

            # Lanczos = highest quality resampling
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)

            # Centre-crop to exactly 1920×1080
            left = (new_w - TARGET_W) // 2
            top  = max(0, int((new_h - TARGET_H) * 0.30))  # 30% from top (same as object-position:center 30%)
            img  = img.crop((left, top, left + TARGET_W, top + TARGET_H))

            img.save(cache_path, 'JPEG', quality=88, optimize=True, progressive=True)
        except Exception:
            # Fall back to serving the original if PIL fails
            resp = make_response(send_from_directory(folder, filename))
            resp.headers['Cache-Control'] = 'public, max-age=3600'
            return resp

    resp = make_response(send_from_directory(cache_dir, cache_name))
    resp.headers['Cache-Control'] = 'public, max-age=86400'  # 24h — images don't change
    resp.headers['Content-Type']  = 'image/jpeg'
    return resp
