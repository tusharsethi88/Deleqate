"""
core.database — VERBATIM DB layer from app.py (lines 714-1320, 1957-1978).
Raw sqlite3 against the SAME deleqate_v2.db file the Flask app uses.
Includes init_db with all migrations, SKU seeding, pricing sync, the
AutoPilot auto-assign worker, and log_status.
"""
import os, sqlite3, threading
from werkzeug.security import generate_password_hash
from .business import (
    ADMIN_EMAIL, ADMIN_PASSWORD, IS_PRODUCTION, FRONTEND_URL,
    TEST_CLIENT_PHONE, TEST_CLIENT_PIN, TEST_PILOT_EMAIL, TEST_PILOT_PASS,
    TASK_LABELS,
    PRICE_VIRTUAL_STAGING, PRICE_VIRTUAL_STAGING_STARTER,
    PRICE_PROPERTY_REEL_HOOK, PRICE_PROPERTY_REEL_STANDARD, PRICE_PROPERTY_REEL_SHOWCASE,
    PRICE_PROPERTY_SOCIAL_CARD,
    PRICE_BG_CLEANUP, PRICE_PRODUCT_LISTING, PRICE_PRODUCT_MOCKUP,
    PRICE_INSTAGRAM_CAROUSEL, PRICE_BRAND_DEMO_VIDEO, PRICE_ANNOUNCEMENT_PACK,
    PRICE_BRAND_STARTER_KIT, PRICE_MENU_DESIGN, PRICE_PODCAST_REEL, PRICE_EQUITY_RESEARCH,
    PRICE_PER_RENDER, PRICE_PER_STAGING, PRICE_PER_PRODUCT, PRICE_AUDIO_FIXED,
)

# Same DB file as the Flask app (project root, one level above backend/)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'deleqate_v2.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def get_setting(key, default=None):
    """Read an admin-toggleable flag from app_settings."""
    try:
        conn = get_db()
        row = conn.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
        conn.close()
        return row['value'] if row else default
    except Exception:
        return default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        'INSERT INTO app_settings (key, value) VALUES (?, ?) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        (key, str(value)))
    conn.commit(); conn.close()


PRICING_MAP = {
    'virtual_staging':      (PRICE_VIRTUAL_STAGING,      'fixed', '4-room staging pack'),
    'property_reel':        (PRICE_PROPERTY_REEL_HOOK,   'fixed', 'reel'),  # base price; tier determines actual price
    'property_social_card': (PRICE_PROPERTY_SOCIAL_CARD, 'fixed', '2 social cards'),
    'bg_cleanup':         (PRICE_BG_CLEANUP,        'image',   'images cleaned'),
    'product_listing':    (PRICE_PRODUCT_LISTING,  'product',  'products'),
    'product_mockup':     (PRICE_PRODUCT_MOCKUP,   'image',    'mockups'),
    'instagram_carousel': (PRICE_INSTAGRAM_CAROUSEL,'fixed',   'carousel'),
    'brand_demo_video':   (PRICE_BRAND_DEMO_VIDEO, 'fixed',    'video'),
    'announcement_pack':  (PRICE_ANNOUNCEMENT_PACK,  'fixed',   '3-piece announcement pack'),
    'brand_starter_kit':  (PRICE_BRAND_STARTER_KIT,'fixed',    'brand kit'),
    'menu_design':        (PRICE_MENU_DESIGN,       'fixed',   'menu'),
    'podcast_reel':       (PRICE_PODCAST_REEL,      'fixed',   'highlight reel'),
    'equity_research':    (PRICE_EQUITY_RESEARCH,   'fixed',   'equity research report'),
    # Legacy
    'moodboard':          (PRICE_PER_RENDER,        'render',  'renders'),
    'staging':            (PRICE_PER_STAGING,       'photo',   'photos'),
    'product':            (PRICE_PER_PRODUCT,       'image',   'images'),
    'audio':              (PRICE_AUDIO_FIXED,       'fixed',   'file'),
}

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
            (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), 'Abhimanyu Dabas', '7011989292', 'admin')
        )

    # ── Seed test pilot + test client (DEV ONLY) ──────────────────────
    # Never create the test accounts in production — they have weak, public
    # credentials. Gated behind IS_PRODUCTION (P0-Secrets in launch guide).
    if not IS_PRODUCTION:
        if not conn.execute('SELECT id FROM users WHERE email=? AND role=?', (TEST_PILOT_EMAIL, 'pilot')).fetchone():
            conn.execute(
                'INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)',
                (TEST_PILOT_EMAIL, generate_password_hash(TEST_PILOT_PASS), 'Test Pilot', '9000000001', 'pilot', 'active')
            )

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
        ("brand_dna",        "ALTER TABLE orders ADD COLUMN brand_dna TEXT"),
        ("carousel_plan",    "ALTER TABLE orders ADD COLUMN carousel_plan TEXT"),
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
            ('bg_cleanup',         'Background Cleanup',          'E-commerce',        PRICE_BG_CLEANUP,           'fixed',   'up to 10 images',         1,  4),
            ('product_listing',    'Product Listing Creation',    'E-commerce',        PRICE_PRODUCT_LISTING,      'product', 'per product',             1,  5),
            ('product_mockup',     'Product Lifestyle Mockup',    'E-commerce',        PRICE_PRODUCT_MOCKUP,       'image',   'per mockup',              1,  6),
            ('instagram_carousel', 'Instagram Carousel Design',   'SMB Visual Content',PRICE_INSTAGRAM_CAROUSEL,   'fixed',   'carousel',                1,  7),
            ('brand_demo_video',   'Brand Demo Video',            'SMB Visual Content',PRICE_BRAND_DEMO_VIDEO,     'fixed',   'video',                   1,  8),
            ('announcement_pack',  'Announcement Pack',           'SMB Visual Content',PRICE_ANNOUNCEMENT_PACK,    'fixed',   '3-piece pack',            1,  9),
            ('brand_starter_kit',  'Brand Starter Kit',           'Personal & Brand',  PRICE_BRAND_STARTER_KIT,    'fixed',   'brand kit',               1, 10),
            ('menu_design',        'Menu Design',                 'Personal & Brand',  PRICE_MENU_DESIGN,          'fixed',   'menu',                    1, 11),
            ('podcast_reel',       'Podcast Highlight Reel',      'Personal & Brand',  PRICE_PODCAST_REEL,         'fixed',   'highlight reel',          1, 12),
            ('equity_research',    'Equity Research Report',      'Research',          PRICE_EQUITY_RESEARCH,      'fixed',   'equity research report',  1, 13),
        ]
        conn.executemany(
            'INSERT INTO skus (task_key, label, cluster, price_paisa, price_type, price_label, is_active, sort_order) VALUES (?,?,?,?,?,?,?,?)',
            _seed
        )

    # ── sku_price_options: option-based pricing (duration/tier/format) ──
    # Each row is one selectable option for a SKU whose choice drives the price.
    # submit_order looks up the price by (task_key, field_name, option_value);
    # admin edits these prices from the SKUs tab.
    conn.execute('''CREATE TABLE IF NOT EXISTS sku_price_options (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        task_key     TEXT NOT NULL,
        field_name   TEXT NOT NULL,      -- the intake form field, e.g. 'duration'
        group_label  TEXT NOT NULL,      -- display heading, e.g. 'Video Duration'
        option_value TEXT NOT NULL,      -- submitted value, e.g. '15s'
        option_label TEXT NOT NULL,      -- display label, e.g. '15 sec'
        price_paisa  INTEGER NOT NULL,
        sort_order   INTEGER DEFAULT 0,
        UNIQUE(task_key, field_name, option_value)
    )''')
    if not conn.execute('SELECT 1 FROM sku_price_options LIMIT 1').fetchone():
        _opt_seed = [
            # brand_demo_video — priced by video duration (was flat ₹1249)
            ('brand_demo_video', 'duration', 'Video Duration', '15s', '15 sec',  99900, 1),
            ('brand_demo_video', 'duration', 'Video Duration', '30s', '30 sec', 124900, 2),
            ('brand_demo_video', 'duration', 'Video Duration', '60s', '60 sec', 174900, 3),
            # property_reel — existing tiers
            ('property_reel', 'reel_tier', 'Reel Tier', 'hook',     'Hook',      PRICE_PROPERTY_REEL_HOOK,     1),
            ('property_reel', 'reel_tier', 'Reel Tier', 'standard', 'Standard',  PRICE_PROPERTY_REEL_STANDARD, 2),
            ('property_reel', 'reel_tier', 'Reel Tier', 'showcase', 'Showcase',  PRICE_PROPERTY_REEL_SHOWCASE, 3),
            # virtual_staging — tier (extra rooms still added on top for Full)
            ('virtual_staging', 'vs_tier', 'Staging Tier', 'starter', 'Starter (2 rooms)', PRICE_VIRTUAL_STAGING_STARTER, 1),
            ('virtual_staging', 'vs_tier', 'Staging Tier', 'full',    'Full (up to 4 rooms)', PRICE_VIRTUAL_STAGING,      2),
            # instagram_carousel — format
            ('instagram_carousel', 'carousel_format', 'Format', 'Text-led',     'Text-led',     PRICE_INSTAGRAM_CAROUSEL, 1),
            ('instagram_carousel', 'carousel_format', 'Format', 'Image + Text', 'Image + Text', PRICE_INSTAGRAM_CAROUSEL, 2),
            ('instagram_carousel', 'carousel_format', 'Format', 'Photo-only',   'Photo-only',   PRICE_INSTAGRAM_CAROUSEL, 3),
            ('instagram_carousel', 'carousel_format', 'Format', 'Infographic',  'Infographic',  89900,                    4),
        ]
        conn.executemany(
            'INSERT INTO sku_price_options (task_key, field_name, group_label, option_value, option_label, price_paisa, sort_order) VALUES (?,?,?,?,?,?,?)',
            _opt_seed
        )

    # ── app_settings: generic admin-toggleable key/value flags ──
    conn.execute('''CREATE TABLE IF NOT EXISTS app_settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    )''')
    # Seed default flags (only inserts if missing)
    for _k, _v in [('voice_brief_enabled', '1')]:
        conn.execute('INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)', (_k, _v))

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

def get_option_price(task_key, field_name, option_value, conn=None):
    """Return the price_paisa for a selected SKU option, or None if not found.
    Used by submit_order to price choice-driven SKUs (duration/tier/format)."""
    own = conn is None
    if own:
        conn = get_db()
    try:
        row = conn.execute(
            'SELECT price_paisa FROM sku_price_options WHERE task_key=? AND field_name=? AND option_value=?',
            (task_key, field_name, (option_value or '').strip())).fetchone()
        return row['price_paisa'] if row else None
    except Exception:
        return None
    finally:
        if own:
            conn.close()


def sync_pricing_from_db():
    """Load admin-edited SKU prices/labels from DB into in-memory maps (called at startup + after edits)."""
    conn = get_db()
    rows = conn.execute('SELECT task_key, price_paisa, price_type, price_label, label FROM skus').fetchall()
    conn.close()
    for s in rows:
        PRICING_MAP[s['task_key']] = (s['price_paisa'], s['price_type'], s['price_label'])
        TASK_LABELS[s['task_key']] = s['label']


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
                      AND datetime(created_at, 'localtime') <= datetime('now', ?, 'localtime')
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

_ap_thread = None
def start_background_workers():
    """Start the AutoPilot auto-assign thread (parity with app.py 1201-1202).
    Called once from config.urls at startup."""
    global _ap_thread
    if _ap_thread is None or not _ap_thread.is_alive():
        _ap_thread = threading.Thread(target=_autopilot_auto_assign_worker, daemon=True, name='autopilot-autoassign')
        _ap_thread.start()
        
    try:
        from api.views.llm_research import start_llm_worker
        start_llm_worker()
    except Exception as e:
        print(f"Error starting LLM worker: {e}")

# ═══════════════════════════════════════════════════════════
# CUSTOMER EMAIL NOTIFICATIONS  (order placed + every status change)
# ═══════════════════════════════════════════════════════════
# Customer-facing copy per status. Keys match the `new` status passed to
# log_status(). Each value is (subject, body) and may use {name} {id} {task}
# {amount} {link}. Statuses not listed fall back to a generic update email.
# 'in_progress' is intentionally skipped (it fires right after 'assigned',
# which already tells the customer work has started) — add it here to enable.
STATUS_EMAILS = {
    'pending':        ("We've received your order #{id}",
                       "Hi {name},\n\nThanks for your order! We've received your request for {task} (₹{amount}) and it's now in our queue. A vetted Pilot will begin work shortly.\n\nTrack your order: {link}\n\n— Team Deleqate"),
    'assigned':       ("Your order #{id} is now in progress",
                       "Hi {name},\n\nGood news — a vetted Pilot has picked up your order for {task} and work has begun. We'll let you know the moment it's ready to preview.\n\nTrack your order: {link}\n\n— Team Deleqate"),
    'under_review':   ("Your order #{id} is in quality review",
                       "Hi {name},\n\nYour {task} has been completed by the Pilot and is now in our quality-check stage. Almost there!\n\nTrack your order: {link}\n\n— Team Deleqate"),
    'delivered':      ("Your order #{id} is ready to preview",
                       "Hi {name},\n\nYour {task} delivery is ready! Preview your files and approve to download.\n\nPreview now: {link}\n\n— Team Deleqate"),
    'approved':       ("Payment confirmed — order #{id} complete",
                       "Hi {name},\n\nPayment received and your {task} order is complete. Your files are unlocked for download. Thank you for choosing Deleqate!\n\nDownload: {link}\n\n— Team Deleqate"),
    'edit_requested': ("Revisions in progress for order #{id}",
                       "Hi {name},\n\nWe're applying the revisions you requested on your {task}. We'll notify you as soon as the updated delivery is ready.\n\nTrack your order: {link}\n\n— Team Deleqate"),
    'rejected':       ("Your order #{id} is being refined",
                       "Hi {name},\n\nOur QC team asked for a few improvements, so your {task} is being refined by the Pilot. No action is needed from you — we'll email you when it's ready.\n\nTrack your order: {link}\n\n— Team Deleqate"),
}
STATUS_EMAIL_SKIP = {'in_progress'}


def _send_brevo_email(to_email, to_name, subject, body_txt):
    brevo_key = os.environ.get('BREVO_API_KEY', '')
    from_email = os.environ.get('FROM_EMAIL', 'noreply@deleqate.com')
    if not brevo_key:
        print(f"\n[DEV EMAIL] (BREVO_API_KEY not set) To: {to_email}\nSubj: {subject}\n{body_txt}\n", flush=True)
        return
    try:
        import requests as req_lib
        resp = req_lib.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={'api-key': brevo_key, 'Content-Type': 'application/json'},
            json={
                'sender': {'name': 'Deleqate', 'email': from_email},
                'to': [{'email': to_email, 'name': to_name or 'there'}],
                'subject': subject,
                'textContent': body_txt,
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201, 202):
            print(f"[EMAIL] Brevo REJECTED '{subject}' to {to_email}: "
                  f"HTTP {resp.status_code} {resp.text}", flush=True)
        else:
            print(f"[EMAIL] sent '{subject}' to {to_email} (HTTP {resp.status_code})", flush=True)
    except Exception as e:
        print(f"[EMAIL] Brevo error sending '{subject}' to {to_email}: {e}", flush=True)


def notify_order_status(conn, order_id, new):
    """Email the customer about an order status change. Best-effort: never
    raises, sends in a background thread so it can't block or break the
    request/transaction."""
    try:
        if new in STATUS_EMAIL_SKIP:
            return
        row = conn.execute(
            'SELECT name, email, client_email, task, total_price FROM orders WHERE id=?',
            (order_id,)).fetchone()
        if not row:
            return
        # Pick a real, deliverable email. Phone-signup customers get a synthetic
        # placeholder like "9871722766@client.deleqate" which can't receive mail.
        def _real(e):
            return e and '@' in e and not e.endswith('@client.deleqate')
        to_email = next((e for e in (row['email'], row['client_email']) if _real(e)), None)
        if not to_email:
            print(f"[EMAIL] order {order_id}: no real email on file "
                  f"(email={row['email']!r}) — skipping '{new}' notification", flush=True)
            return
        task_label = TASK_LABELS.get(row['task'], row['task'])
        # total_price is stored in paise (e.g. 79900 = ₹799) — show rupees.
        _tp = row['total_price']
        if _tp is None:
            amount = ''
        else:
            _rupees = _tp / 100
            amount = f"{_rupees:,.0f}" if _rupees == int(_rupees) else f"{_rupees:,.2f}"
        link = f"{FRONTEND_URL.rstrip('/')}/order/{order_id}"
        subject, body = STATUS_EMAILS.get(
            new, ("Update on your order #{id}",
                  "Hi {name},\n\nYour order for {task} has been updated to: " + str(new) + ".\n\nTrack your order: {link}\n\n— Team Deleqate"))
        fields = {'name': row['name'] or 'there', 'id': order_id,
                  'task': task_label, 'amount': amount, 'link': link}
        subject = subject.format(**fields)
        body = body.format(**fields)
        threading.Thread(
            target=_send_brevo_email,
            args=(to_email, row['name'], subject, body),
            daemon=True,
        ).start()
    except Exception as e:
        print(f"[EMAIL] notify_order_status failed for order {order_id}: {e}")


def log_status(conn, order_id, old, new, by=None, note=''):
    conn.execute('INSERT INTO status_log (order_id,old_status,new_status,changed_by,note) VALUES (?,?,?,?,?)',
                 (order_id, old, new, by, note))
    if old != new:
        notify_order_status(conn, order_id, new)
