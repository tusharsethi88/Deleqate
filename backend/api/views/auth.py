"""
api.views.auth — port of app.py auth routes (lines 1538-1954):
/login, /logout, /dq-control-7x9k, /login/phone, /verify-otp, /signup,
/verify-signup-otp, /forgot-password, /reset-password-verify,
/reset-password-new, plus OTP/captcha helpers.
GET page routes now return the data the React page needs (login_type,
captcha question, csrf token); POSTs keep identical validation, messages,
rate limits, honeypot and timing behavior.
"""
import os, re, time, secrets, string
from datetime import datetime, timedelta

from django.views.decorators.http import require_http_methods
from werkzeug.security import generate_password_hash, check_password_hash

from core.database import get_db
from core.auth import load_user, do_login, do_logout, dashboard_for, get_csrf_token, login_required
from core.security import (
    rate_limit, get_client_ip, sanitize_text, sanitize_email, sanitize_phone,
    record_login_failure, clear_login_failures, is_login_banned,
    honeypot_triggered, safe_redirect_url,
)
from api.helpers import form, ok, err


# ── session bootstrap for the React app ───────────────────
def session_view(request):
    """GET /api/session — who am I + CSRF token (replaces template context)."""
    user = load_user(request)
    d = {'ok': True, 'csrf_token': get_csrf_token(request),
         'authenticated': user.is_authenticated}
    if user.is_authenticated:
        d['user'] = {'id': user.id, 'email': user.email, 'name': user.name,
                     'role': user.role, 'phone': user.phone,
                     'dashboard': dashboard_for(user.role)}
    return ok(d)


# ── OTP helpers (verbatim from app.py 1651-1702) ───────────
def generate_otp():
    # H-3: cryptographically secure
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def send_otp_email(email, otp, name='there'):
    """Send OTP to email via Brevo, or print to console in DEV mode."""
    brevo_key = os.environ.get('BREVO_API_KEY', '')
    from_email = os.environ.get('FROM_EMAIL', 'noreply@deleqate.com')
    subject = 'Your Deleqate verification code'
    body_txt = (
        f"Hi {name},\n\n"
        f"Your Deleqate verification code is:\n\n"
        f"  {otp}\n\n"
        f"This code is valid for 10 minutes. Do not share it with anyone.\n\n"
        f"— Team Deleqate"
    )
    if brevo_key:
        try:
            import requests as req_lib
            req_lib.post(
                'https://api.brevo.com/v3/smtp/email',
                headers={'api-key': brevo_key, 'Content-Type': 'application/json'},
                json={
                    'sender': {'name': 'Deleqate', 'email': from_email},
                    'to': [{'email': email, 'name': name}],
                    'subject': subject,
                    'textContent': body_txt,
                },
                timeout=10
            )
        except Exception as e:
            print(f"[EMAIL] Brevo error: {e} — OTP for {email}: {otp}")
    else:
        print(f"\n{'='*40}\n[DEV EMAIL OTP] To: {email}  OTP: {otp}\n{'='*40}\n")


def send_otp_whatsapp(phone, otp):
    """Send OTP via MSG91 or print to console in DEV mode."""
    msg91_key = os.environ.get('MSG91_AUTH_KEY', '')
    if msg91_key:
        try:
            import requests as req_lib
            payload = {
                "template_id": os.environ.get('MSG91_OTP_TEMPLATE_ID', ''),
                "mobile": f"91{phone.lstrip('+').lstrip('91')}",
                "authkey": msg91_key,
                "otp": otp
            }
            req_lib.post('https://api.msg91.com/api/v5/otp', json=payload, timeout=5)
        except Exception as e:
            print(f"[OTP] MSG91 error: {e} — OTP for {phone}: {otp}")
    else:
        print(f"\n{'='*40}\n[DEV OTP] Phone: {phone}  OTP: {otp}\n{'='*40}\n")


# ── MATH CAPTCHA HELPERS (verbatim logic) ──────────────────
def _new_captcha(request):
    a, b = 2 + secrets.randbelow(8), 1 + secrets.randbelow(9)
    request.session['captcha_answer'] = a + b
    return f"{a} + {b}"


def _check_captcha(request, answer_str):
    try:
        return int(answer_str.strip()) == request.session.get('captcha_answer')
    except (ValueError, TypeError, AttributeError):
        return False


# ── /login (app.py 1538-1606) ──────────────────────────────
@require_http_methods(['GET', 'POST'])
@rate_limit(limit=20, window=60, ban_secs=600, scope='login')
def login(request):
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect=dashboard_for(user.role))
    ip = get_client_ip(request)
    login_type = request.GET.get('type', 'client')
    if is_login_banned(ip):
        return err('Too many failed attempts. Please try again in 30 minutes.', status=429)

    if request.method == 'POST':
        if honeypot_triggered(request):
            time.sleep(2)
            return err('Invalid credentials.', status=401)

        login_type = form(request, 'login_type', request.GET.get('type', 'client'))

        # ── CLIENT: phone + 4-digit PIN ────────────────────
        if login_type == 'client':
            phone = sanitize_phone(form(request, 'phone', ''))
            pin = str(form(request, 'pin', '')).strip()[:8]
            if not phone or not pin:
                return err('Please enter your phone number and PIN.')
            conn = get_db()
            row = conn.execute(
                'SELECT * FROM users WHERE phone=? AND role=?', (phone, 'client')
            ).fetchone()
            conn.close()
            if row and check_password_hash(row['password_hash'], pin):
                if row['account_status'] == 'inactive':
                    return err('Account inactive. Contact support.', status=403)
                clear_login_failures(ip)
                do_login(request, row)
                next_url = request.GET.get('next') or '/client/orders'
                return ok(redirect=safe_redirect_url(request, next_url))
            record_login_failure(ip)
            time.sleep(0.5)
            return err('Incorrect phone number or PIN.', status=401)

        # ── PILOT: email + password ────────────────────────
        else:
            email = sanitize_email(form(request, 'email', ''))
            pw = str(form(request, 'password', ''))[:128]
            if not email or not pw:
                return err('Please enter your email and password.')
            conn = get_db()
            row = conn.execute(
                'SELECT * FROM users WHERE email=? AND role=?', (email, 'pilot')
            ).fetchone()
            conn.close()
            if row and check_password_hash(row['password_hash'], pw):
                if row['account_status'] == 'inactive':
                    return err('Account inactive. Contact admin.', status=403)
                clear_login_failures(ip)
                do_login(request, row)
                return ok(redirect='/pilot/dashboard')
            record_login_failure(ip)
            time.sleep(0.5)
            return err('Incorrect email or password.', status=401)

    return ok({'login_type': login_type, 'csrf_token': get_csrf_token(request)})


# ── /logout (app.py 1608-1612) ─────────────────────────────
@login_required
def logout(request):
    do_logout(request)
    return ok(redirect='/')


# ── /dq-control-7x9k (app.py 1614-1645) ────────────────────
@require_http_methods(['GET', 'POST'])
def admin_secret_login(request):
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect='/admin/dashboard')
    ip = get_client_ip(request)
    if request.method == 'POST':
        if is_login_banned(ip):
            return err('Too many failed attempts. Please wait before trying again.', status=429)
        if honeypot_triggered(request):
            time.sleep(3)
            return err('Invalid credentials.', status=401)
        email = sanitize_email(form(request, 'email', ''))
        pw = str(form(request, 'password', ''))[:128]
        if not email or not pw:
            return err('Invalid credentials.', status=401)
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE email=? AND role=?', (email, 'admin')).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], pw):
            if row['account_status'] == 'inactive':
                return err('Account inactive.', status=403)
            clear_login_failures(ip)
            do_login(request, row)
            return ok(redirect='/admin/dashboard')
        record_login_failure(ip)
        time.sleep(1)
        return err('Invalid credentials.', status=401)
    return ok({'csrf_token': get_csrf_token(request)})


# ── /login/phone (app.py 1704-1737) ────────────────────────
@require_http_methods(['GET', 'POST'])
@rate_limit(limit=20, window=60, ban_secs=600, scope='login')
def login_phone(request):
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect=dashboard_for(user.role))
    ip = get_client_ip(request)
    if is_login_banned(ip):
        return err('Too many failed attempts. Please try again in 30 minutes.', status=429)
    if request.method == 'POST':
        if honeypot_triggered(request):
            time.sleep(2)
            return err('Invalid email or password.', status=401)
        email = sanitize_email(form(request, 'email', ''))
        pw = str(form(request, 'password', ''))[:128]
        if not email or not pw:
            return err('Invalid email or password.', status=401)
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE email=? AND role=?', (email, 'client')).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], pw):
            if row['account_status'] == 'inactive':
                return err('Account inactive.', status=403)
            clear_login_failures(ip)
            do_login(request, row)
            next_url = request.GET.get('next') or dashboard_for(row['role'])
            return ok(redirect=safe_redirect_url(request, next_url))
        record_login_failure(ip)
        time.sleep(0.5)
        return err('Invalid email or password.', status=401)
    return ok({'csrf_token': get_csrf_token(request)})


# ── /verify-otp (app.py 1739-1781) ─────────────────────────
@require_http_methods(['GET', 'POST'])
@rate_limit(limit=10, window=300, ban_secs=600, scope='otp_verify')
def verify_otp(request):
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect=dashboard_for(user.role))
    phone = request.session.get('otp_phone')
    if not phone:
        return err('No pending OTP.', redirect='/login/phone', status=400)
    if request.method == 'POST':
        entered = str(form(request, 'otp', '')).strip()
        conn = get_db()
        token = conn.execute(
            "SELECT * FROM otp_tokens WHERE phone=? AND otp=? AND used=0 ORDER BY id DESC LIMIT 1",
            (phone, entered)
        ).fetchone()
        if not token:
            conn.close()
            return err('Incorrect OTP. Please try again.', status=401)
        if datetime.utcnow() > datetime.fromisoformat(str(token['expires_at'])):
            conn.execute("UPDATE otp_tokens SET used=1 WHERE id=?", (token['id'],))
            conn.commit(); conn.close()
            return err('OTP expired. Request a new one.', redirect='/login/phone', status=401)
        # Valid — mark used
        conn.execute("UPDATE otp_tokens SET used=1 WHERE id=?", (token['id'],))
        # Find or create client user
        row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)",
                (f"{phone}@whatsapp.deleqate", generate_password_hash(secrets.token_urlsafe(24)),
                 f"Client {phone[-4:]}", phone, 'client', 'active')
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        conn.commit(); conn.close()
        request.session.pop('otp_phone', None)
        do_login(request, row)
        next_url = request.session.pop('next_url', None)
        return ok(redirect=next_url or dashboard_for(row['role']))
    return ok({'phone': phone, 'csrf_token': get_csrf_token(request)})


# ── /signup (app.py 1800-1855) ─────────────────────────────
@require_http_methods(['GET', 'POST'])
def signup(request):
    """Client-only sign-up: phone + name + 4-digit PIN + math captcha."""
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect=dashboard_for(user.role))

    # Block any attempt to sign up as pilot publicly
    if request.GET.get('role') == 'pilot' or form(request, 'role') == 'pilot':
        return err('Pilot accounts are created by the admin only.', redirect='/signup')

    if request.method == 'POST':
        name = sanitize_text(str(form(request, 'name', '')).strip(), max_length=100, allow_newlines=False)
        phone = sanitize_phone(form(request, 'phone', ''))
        email = str(form(request, 'email', '')).strip().lower()
        pin = str(form(request, 'pin', '')).strip()
        pin_cfm = str(form(request, 'pin_confirm', '')).strip()
        captcha = str(form(request, 'captcha_answer', '')).strip()

        if not name:
            return err('Please enter your full name.', captcha_question=_new_captcha(request))
        if not phone:
            return err('Please enter a valid 10-digit Indian mobile number.', captcha_question=_new_captcha(request))
        if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) or len(email) > 254:
            return err('Please enter a valid email address.', captcha_question=_new_captcha(request))
        if not re.match(r'^\d{4}$', pin):
            return err('PIN must be exactly 4 digits.', captcha_question=_new_captcha(request))
        if pin != pin_cfm:
            return err('PINs do not match. Please try again.', captcha_question=_new_captcha(request))
        if not _check_captcha(request, captcha):
            return err('Incorrect captcha answer. Please try again.', captcha_question=_new_captcha(request))

        conn = get_db()
        if conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (phone, 'client')).fetchone():
            conn.close()
            return err('This phone number is already registered. Please sign in.',
                       redirect='/login?type=client')
        if conn.execute('SELECT id FROM users WHERE email=? AND role=?', (email, 'client')).fetchone():
            conn.close()
            return err('This email address is already registered. Please sign in.',
                       redirect='/login?type=client')

        conn.execute(
            'INSERT INTO users (email, password_hash, name, phone, role, account_status) VALUES (?,?,?,?,?,?)',
            (email, generate_password_hash(pin), name, phone, 'client', 'active')
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE phone=? AND role=?', (phone, 'client')).fetchone()
        conn.close()
        do_login(request, row)
        return ok(flash=[('success', f'Welcome, {name}! Your account is ready.')],
                  redirect='/client/orders')

    return ok({'captcha_question': _new_captcha(request),
               'csrf_token': get_csrf_token(request)})


# ── /verify-signup-otp (legacy, app.py 1857-1860) ──────────
def verify_signup_otp(request):
    return ok(redirect='/signup')


# ── /forgot-password (app.py 1864-1890) ────────────────────
@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    user = load_user(request)
    if user.is_authenticated:
        return ok(redirect=dashboard_for(user.role))
    role = request.GET.get('role', form(request, 'role', 'client'))
    if role not in ('client', 'pilot', 'admin'):
        role = 'client'
    if request.method == 'POST':
        email = sanitize_email(form(request, 'email', ''))
        if not email:
            return err('Please enter your email address.')
        conn = get_db()
        u = conn.execute('SELECT id,name FROM users WHERE email=? AND role=?', (email, role)).fetchone()
        conn.close()
        if u:
            otp = generate_otp()
            expires = datetime.utcnow() + timedelta(minutes=15)
            conn = get_db()
            conn.execute("UPDATE otp_tokens SET used=1 WHERE phone=? AND used=0", (f'reset_{email}_{role}',))
            conn.execute("INSERT INTO otp_tokens (phone, otp, expires_at) VALUES (?,?,?)",
                         (f'reset_{email}_{role}', otp, expires))
            conn.commit(); conn.close()
            send_otp_email(email, otp, u['name'])
        return ok(redirect=f'/reset-password-verify?email={email}&role={role}')
    return ok({'role': role, 'csrf_token': get_csrf_token(request)})


# ── /reset-password-verify (app.py 1892-1926) ──────────────
@require_http_methods(['GET', 'POST'])
@rate_limit(limit=10, window=300, ban_secs=600, scope='reset_verify')
def reset_password_verify(request):
    email = sanitize_email(request.GET.get('email', form(request, 'email', '')))
    role = request.GET.get('role', form(request, 'role', 'client'))
    if role not in ('client', 'pilot', 'admin'):
        role = 'client'
    if not email:
        return err('Invalid reset link. Please start again.', redirect='/forgot-password')
    if request.method == 'POST':
        entered = str(form(request, 'otp', '')).strip()
        key = f'reset_{email}_{role}'
        conn = get_db()
        token = conn.execute(
            "SELECT * FROM otp_tokens WHERE phone=? AND otp=? AND used=0 ORDER BY id DESC LIMIT 1",
            (key, entered)
        ).fetchone()
        if not token:
            conn.close()
            return err('Incorrect code. Please try again.', status=401)
        if datetime.utcnow() > datetime.fromisoformat(str(token['expires_at'])):
            conn.execute("UPDATE otp_tokens SET used=1 WHERE id=?", (token['id'],))
            conn.commit(); conn.close()
            return err('Code expired. Please request a new one.',
                       redirect=f'/forgot-password?role={role}', status=401)
        conn.execute("UPDATE otp_tokens SET used=1 WHERE id=?", (token['id'],))
        conn.commit(); conn.close()
        request.session['pw_reset'] = {'email': email, 'role': role, 'verified': True}
        request.session.modified = True
        return ok(redirect='/reset-password-new')
    return ok({'email': email, 'role': role, 'csrf_token': get_csrf_token(request)})


# ── /reset-password-new (app.py 1928-1954) ─────────────────
@require_http_methods(['GET', 'POST'])
def reset_password_new(request):
    pending = request.session.get('pw_reset')
    if not pending or not pending.get('verified'):
        return err('Session expired. Please start again.', redirect='/forgot-password', status=401)
    role = pending['role']
    is_client = role == 'client'
    if request.method == 'POST':
        pw = str(form(request, 'password', '')).strip()
        pw2 = str(form(request, 'password2', '')).strip()
        if is_client:
            if not re.match(r'^\d{4}$', pw):
                return err('PIN must be exactly 4 digits.')
        elif len(pw) < 8:
            return err('Password must be at least 8 characters.')
        if pw != pw2:
            return err('PINs do not match.' if is_client else 'Passwords do not match.')
        conn = get_db()
        # M-2: bump session_version so every existing session is invalidated
        conn.execute('UPDATE users SET password_hash=?, '
                     'session_version=COALESCE(session_version,0)+1 WHERE email=? AND role=?',
                     (generate_password_hash(pw), pending['email'], pending['role']))
        conn.commit(); conn.close()
        request.session.flush()
        return ok(flash=[('success', 'PIN updated! Please sign in.' if is_client else 'Password updated! Please sign in.')],
                  redirect=f'/login?type={role}')
    return ok({'role': role, 'csrf_token': get_csrf_token(request)})
