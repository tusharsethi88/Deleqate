"""
autopilot/config.py
────────────────────────────────────────────────────────────────────────────────
AutoPilot configuration loader.
All secrets come from autopilot/.env — never hard-coded.
────────────────────────────────────────────────────────────────────────────────
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load from autopilot/.env (separate from the main app .env)
_ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(_ENV_PATH)

# ── AutoPilot Gmail account ───────────────────────────────────────────────────
AUTOPILOT_EMAIL        = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')          # e.g. deleqate@gmail.com
AUTOPILOT_APP_PASSWORD = os.environ.get('AUTOPILOT_APP_PASSWORD', '')   # Gmail App Password (not login password)
AUTOPILOT_PILOT_PASSWORD = os.environ.get('AUTOPILOT_PILOT_PASSWORD', '')  # Deleqate pilot account password

# ── Admin contact ─────────────────────────────────────────────────────────────
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'support@deleqate.com')

# ── Deleqate platform connection ──────────────────────────────────────────────
DELEQATE_BASE_URL = os.environ.get('DELEQATE_BASE_URL', 'http://localhost:5051')
AUTOPILOT_API_TOKEN = os.environ.get('AUTOPILOT_API_TOKEN', '')  # Shared secret for autopilot API endpoints

# ── Chrome browser profile ────────────────────────────────────────────────────
# Dedicated Chrome profile directory for the AutoPilot — keeps sessions separate from your personal Chrome
_profile_env = os.environ.get('CHROME_PROFILE_DIR', '').strip()
CHROME_PROFILE_DIR = _profile_env if _profile_env else str(Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'AutoPilotProfile')

# ── Google services URLs ──────────────────────────────────────────────────────
GEMINI_URL = 'https://gemini.google.com'
GOOGLE_FLOW_URL = 'https://labs.google/flow'

# ── Task queue database ───────────────────────────────────────────────────────
QUEUE_DB_PATH = str(Path(__file__).parent / 'queue.db')

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR  = Path(__file__).parent / 'logs'
LOG_FILE = LOG_DIR / 'agent.log'
LOG_DIR.mkdir(exist_ok=True)

# ── Polling interval (seconds) ────────────────────────────────────────────────
EMAIL_POLL_INTERVAL = int(os.environ.get('EMAIL_POLL_INTERVAL', '300'))   # 5 minutes
HEARTBEAT_INTERVAL  = int(os.environ.get('HEARTBEAT_INTERVAL', '60'))     # 1 minute

# ── Task execution settings ───────────────────────────────────────────────────
DOWNLOAD_DIR = Path(__file__).parent / 'downloads'
OUTPUT_DIR   = Path(__file__).parent / 'outputs'
DOWNLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Validation ────────────────────────────────────────────────────────────────
def validate():
    """Call at startup to warn about missing secrets."""
    missing = []
    for name, val in [
        ('AUTOPILOT_EMAIL',        AUTOPILOT_EMAIL),
        ('AUTOPILOT_APP_PASSWORD', AUTOPILOT_APP_PASSWORD),
        ('AUTOPILOT_PILOT_PASSWORD', AUTOPILOT_PILOT_PASSWORD),
        ('AUTOPILOT_API_TOKEN',    AUTOPILOT_API_TOKEN),
    ]:
        if not val:
            missing.append(name)
    if missing:
        print(f"⚠  WARNING: Missing config values in autopilot/.env: {', '.join(missing)}")
        print(f"   Copy autopilot/.env.template → autopilot/.env and fill in the blanks.")
    return len(missing) == 0
