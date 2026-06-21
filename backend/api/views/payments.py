"""
api.views.payments — port of app.py PayU routes (lines 3875-4070).
payment/initiate returns the exact form fields the auto-submitting PayU
form needs (the React page renders and submits it). success/failure are
posted by PayU's redirect through the user's browser — hash-verified,
CSRF-exempt, idempotent (H-2).
"""
import time, sqlite3
from datetime import datetime

from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect

from core.database import get_db, log_status
from core.auth import login_required
from core.business import (
    TASK_LABELS, SUPPORT_WHATSAPP, INITIAL_FREE_CREDITS,
    PRICE_EDIT_CREDIT_1, PRICE_EDIT_CREDIT_3,
    PAYU_URL, PAYU_KEY, FRONTEND_URL,
    payu_generate_hash, payu_verify_hash,
)
from api.helpers import ok, err

import os
# Where the React app lives — PayU browser redirects must land there,
# not on this API server. Set FRONTEND_APP_URL in production.
APP_URL = os.environ.get('FRONTEND_APP_URL', 'http://localhost:8061')


# ── /payment/initiate (app.py 3875-3937) ───────────────────
@login_required
def payment_initiate(request):
    current_user = request.user
    try:
        order_id = int(request.GET.get('order_id'))
    except (TypeError, ValueError):
        return err('Invalid payment link.', redirect='/client/orders')

    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=? AND client_id=?',
                     (order_id, current_user.id)).fetchone()
    conn.close()
    if not o:
        return err('Order not found.', redirect='/client/orders', status=404)
    _post_delivery = o['status'] == 'delivered' and o['client_action'] in ('pay_download', 'pay_edit')
    _upfront = o['status'] == 'pending' and o['client_action'] == 'pay_upfront'
    _buy_edit = o['status'] == 'delivered' and o['client_action'] in ('buy_edit_1', 'buy_edit_3')
    if not (_post_delivery or _upfront or _buy_edit):
        return err('Payment cannot be initiated for this order right now.',
                   redirect='/client/orders')

    txnid = f'DEL{order_id}{int(time.time() * 1000)}'

    if o['client_action'] == 'buy_edit_1':
        amount = f'{PRICE_EDIT_CREDIT_1 / 100:.2f}'
        productinfo = '1 Edit Credit — Deleqate'
    elif o['client_action'] == 'buy_edit_3':
        amount = f'{PRICE_EDIT_CREDIT_3 / 100:.2f}'
        productinfo = '3 Edit Credits — Deleqate'
    else:
        amount = f'{o["total_price"] / 100:.2f}'
        action_label = ' + Edit Request' if o['client_action'] == 'pay_edit' else ''
        productinfo = TASK_LABELS.get(o['task'], o['task']) + action_label
    firstname = (current_user.name or '').split()[0] or 'Customer'
    email = current_user.email or ''
    phone = current_user.phone or ''

    conn = get_db()
    conn.execute("UPDATE orders SET payment_ref=? WHERE id=?", (txnid, order_id))
    conn.commit(); conn.close()

    pay_hash = payu_generate_hash(txnid, amount, productinfo, firstname, email)

    surl = f'{FRONTEND_URL}/payment/success'
    furl = f'{FRONTEND_URL}/payment/failure'

    return ok({'payu_url': PAYU_URL, 'key': PAYU_KEY,
               'txnid': txnid, 'amount': amount,
               'productinfo': productinfo, 'firstname': firstname,
               'email': email, 'phone': phone,
               'surl': surl, 'furl': furl,
               'pay_hash': pay_hash, 'order_id': order_id,
               'client_action': o['client_action']})


# ── /payment/success (app.py 3940-4052) ────────────────────
@require_POST
def payment_success(request):
    """PayU posts here on successful payment (browser redirect).
    Verify hash, apply effects idempotently, then redirect into the app."""
    posted = {k: v for k, v in request.POST.items()}

    if not payu_verify_hash(posted):
        return HttpResponseRedirect(f'{APP_URL}/client/orders?pay_error=verify_failed')

    status = posted.get('status', '')
    txnid = posted.get('txnid', '')
    mihpayid = posted.get('mihpayid', '')

    if status.lower() != 'success':
        return HttpResponseRedirect(f'{APP_URL}/client/orders?pay_error=status_{status}')

    conn = get_db()

    # H-2: idempotency
    prior = conn.execute('SELECT order_id FROM payments WHERE txnid=?', (txnid,)).fetchone()
    if prior:
        conn.close()
        return HttpResponseRedirect(f'{APP_URL}/order/success?id={prior["order_id"]}')

    o = conn.execute('SELECT * FROM orders WHERE payment_ref=?', (txnid,)).fetchone()
    if not o:
        conn.close()
        return HttpResponseRedirect(f'{APP_URL}/client/orders?pay_error=order_not_found')

    order_id = o['id']
    client_action = o['client_action'] or 'pay_download'

    if o['status'] in ('approved', 'edit_requested') or o['client_action'] == 'paid_upfront':
        conn.close()
        return HttpResponseRedirect(f'{APP_URL}/order/success?id={order_id}')

    # H-2: record txn BEFORE applying effects (PRIMARY KEY guards double-apply)
    try:
        conn.execute(
            'INSERT INTO payments (txnid, mihpayid, order_id, client_action, amount) VALUES (?,?,?,?,?)',
            (txnid, mihpayid, order_id, client_action, posted.get('amount', '')))
    except sqlite3.IntegrityError:
        conn.close()
        return HttpResponseRedirect(f'{APP_URL}/order/success?id={order_id}')

    if client_action == 'pay_edit':
        new_status = 'edit_requested'
        log_note = f'PayU paid + edit requested — txnid={txnid} mihpayid={mihpayid}'
    elif client_action == 'pay_upfront':
        new_status = 'pending'
        log_note = f'PayU upfront payment confirmed — txnid={txnid} mihpayid={mihpayid}'
    elif client_action == 'buy_edit_1':
        new_status = 'edit_requested'
        log_note = f'Bought 1 edit credit (300) + edit submitted — txnid={txnid}'
    elif client_action == 'buy_edit_3':
        new_status = 'edit_requested'
        log_note = f'Bought 3 edit credits (500) + edit submitted — txnid={txnid}'
    else:
        new_status = 'approved'
        log_note = f'PayU payment success — txnid={txnid} mihpayid={mihpayid}'

    new_client_action = 'paid_upfront' if client_action == 'pay_upfront' else o['client_action']
    conn.execute(
        "UPDATE orders SET status=?, payment_method='payu', client_action=?, "
        "payment_ref=?, completed_at=? WHERE id=?",
        (new_status, new_client_action, mihpayid or txnid,
         datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
    log_status(conn, order_id, o['status'], new_status, o['client_id'], log_note)

    # Grant initial free edit credits on first-ever PayU payment
    if client_action in ('pay_download', 'pay_edit', 'pay_upfront'):
        prev_paid = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE client_id=? AND payment_method IN ('payu','free_pass') AND id!=?",
            (o['client_id'], order_id)).fetchone()[0]
        if prev_paid == 0:
            conn.execute('UPDATE users SET edit_credits = edit_credits + ? WHERE id=?',
                         (INITIAL_FREE_CREDITS, o['client_id']))
            log_status(conn, order_id, new_status, new_status, o['client_id'],
                       f'Granted {INITIAL_FREE_CREDITS} initial free edit credits')

    # H-2: explicit single-step credit accounting
    if client_action == 'buy_edit_3':
        conn.execute('UPDATE users SET edit_credits = edit_credits + 2 WHERE id=?',
                     (o['client_id'],))
    # buy_edit_1 → no balance change

    conn.commit(); conn.close()

    if new_status == 'edit_requested':
        return HttpResponseRedirect(f'{APP_URL}/client/orders?paid=edit')
    return HttpResponseRedirect(f'{APP_URL}/order/success?id={order_id}')


# ── /payment/failure (app.py 4055-4070) ────────────────────
@require_POST
def payment_failure(request):
    posted = {k: v for k, v in request.POST.items()}
    txnid = posted.get('txnid', '')
    status = posted.get('status', 'failure')
    error = posted.get('error_Message') or posted.get('field9', 'Payment was not completed.')
    conn = get_db()
    o = conn.execute('SELECT id FROM orders WHERE payment_ref=?', (txnid,)).fetchone()
    conn.close()
    order_id = o['id'] if o else None
    # Redirect into the React failure page with context in the query string
    from urllib.parse import urlencode
    q = urlencode({'error': error, 'status': status,
                   'order_id': order_id or '', 'support_whatsapp': SUPPORT_WHATSAPP})
    return HttpResponseRedirect(f'{APP_URL}/payment/failure-page?{q}')
