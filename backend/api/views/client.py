"""
api.views.client — port of app.py client routes (lines 3222-3668, 3700-3868)
and authenticated file serving (3271-3347).
"""
import os, json
from datetime import datetime

from django.conf import settings
from django.http import Http404, FileResponse
from django.views.decorators.http import require_POST
from werkzeug.utils import secure_filename

from core.database import get_db, log_status
from core.auth import role_required, login_required
from core.security import safe_serve_file, rate_limit
from core.business import (
    TASK_LABELS, SUPPORT_WHATSAPP, SUPPORT_UPI, TEST_CLIENT_PHONE,
    _file_ext, _unique_named_path,
)
from api.helpers import body, ok, err


def _save_django_file(f, path):
    with open(path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)


# ── /client/orders (app.py 3227-3254) ──────────────────────
@role_required('client')
def client_orders(request):
    current_user = request.user
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM orders WHERE client_id=? ORDER BY created_at DESC',
        (current_user.id,)).fetchall()
    orders = []
    for r in rows:
        od = dict(r)
        try:
            od['intake'] = json.loads(od.get('intake_data') or '{}')
        except Exception:
            od['intake'] = {}
        od['task_label'] = TASK_LABELS.get(od.get('task', ''), od.get('task', ''))
        od['has_deliverables'] = conn.execute(
            'SELECT COUNT(*) FROM deliverables WHERE order_id=?', (od['id'],)
        ).fetchone()[0] > 0
        orders.append(od)
    user_row = conn.execute(
        'SELECT edit_credits FROM users WHERE id=?', (current_user.id,)).fetchone()
    edit_credits = user_row['edit_credits'] if user_row else 0
    conn.close()
    return ok({'orders': orders, 'edit_credits': edit_credits})


# ── /api/client/orders-status (app.py 3257-3266) ───────────
@role_required('client')
def api_client_orders_status(request):
    conn = get_db()
    rows = conn.execute(
        'SELECT id, status FROM orders WHERE client_id=?', (request.user.id,)).fetchall()
    conn.close()
    return ok({'orders': [{'id': r['id'], 'status': r['status']} for r in rows]})


# ── /uploads/<filename> (app.py 3271-3299, C-4) ────────────
@login_required
def uploaded_file(request, filename):
    current_user = request.user
    if os.path.basename(filename).startswith('hero_video.') and '/' not in filename and '\\' not in filename:
        return safe_serve_file(settings.UPLOAD_FOLDER, filename)
    if current_user.role == 'admin':
        return safe_serve_file(settings.UPLOAD_FOLDER, filename)
    conn = get_db()
    row = conn.execute(
        'SELECT o.client_id, o.assigned_pilot_id FROM order_attachments a '
        'JOIN orders o ON a.order_id = o.id WHERE a.filename = ?',
        (filename,)).fetchone()
    if not row:
        row = conn.execute(
            'SELECT o.client_id, o.assigned_pilot_id FROM edit_requests e '
            'JOIN orders o ON e.order_id = o.id WHERE e.attachment_filename = ?',
            (filename,)).fetchone()
    conn.close()
    if not row:
        raise Http404
    if current_user.role == 'pilot' and row['assigned_pilot_id'] == current_user.id:
        return safe_serve_file(settings.UPLOAD_FOLDER, filename)
    if current_user.role == 'client' and row['client_id'] == current_user.id:
        return safe_serve_file(settings.UPLOAD_FOLDER, filename)
    return err('Forbidden', status=403)


# ── /api/preview-img/<filename> (app.py 3304-3324) ─────────
@login_required
def preview_img_file(request, filename):
    current_user = request.user
    if current_user.role in ('admin', 'pilot'):
        resp = safe_serve_file(settings.DELIVERABLES_FOLDER, filename)
        resp['Content-Disposition'] = 'inline'
        return resp
    conn = get_db()
    row = conn.execute(
        'SELECT o.client_id, o.status FROM deliverables d '
        'JOIN orders o ON d.order_id = o.id WHERE d.filename = ?',
        (filename,)).fetchone()
    conn.close()
    if not row or row['client_id'] != current_user.id:
        return err('Forbidden', status=403)
    if row['status'] not in ('delivered', 'approved'):
        return err('Not available', status=403)
    resp = safe_serve_file(settings.DELIVERABLES_FOLDER, filename)
    resp['Content-Disposition'] = 'inline'
    resp['Cache-Control'] = 'no-store, no-cache'
    return resp


# ── /deliverables/<filename> (app.py 3327-3347) ────────────
@login_required
def deliverable_file(request, filename):
    current_user = request.user
    if current_user.role in ('admin', 'pilot'):
        return safe_serve_file(settings.DELIVERABLES_FOLDER, filename)
    # Clients: must own the order AND order must be 'approved'
    conn = get_db()
    row = conn.execute(
        'SELECT o.client_id, o.status FROM deliverables d '
        'JOIN orders o ON d.order_id = o.id WHERE d.filename = ?',
        (filename,)).fetchone()
    conn.close()
    if not row or row['client_id'] != current_user.id:
        return err('File not found.', redirect='/client/orders', status=404)
    if row['status'] != 'approved':
        return err('Complete payment to unlock your download.', redirect='/client/orders', status=403)
    return safe_serve_file(settings.DELIVERABLES_FOLDER, filename)


# ── /order/success (app.py 3367-3383) ──────────────────────
@login_required
def order_success(request):
    current_user = request.user
    order_id = request.GET.get('id', '')
    if order_id:
        conn = get_db()
        o = conn.execute('SELECT id, client_action FROM orders WHERE id=? AND client_id=?',
                         (order_id, current_user.id)).fetchone()
        conn.close()
        if not o and current_user.role != 'admin':
            return err('Order not found.', redirect='/client/orders', status=404)
        client_action = o['client_action'] if o else None
    else:
        client_action = None
    return ok({'order_id': order_id, 'client_action': client_action})


# ── /order/<id> (app.py 3385-3425) ─────────────────────────
@role_required('admin', 'client')
def order_detail(request, order_id):
    current_user = request.user
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found.',
                   redirect='/admin/dashboard' if current_user.role == 'admin' else '/client/orders',
                   status=404)
    if current_user.role == 'client' and o['client_id'] != current_user.id:
        conn.close()
        return err('Access denied.', redirect='/client/orders', status=403)
    if current_user.role == 'client' and o['status'] in ('delivered', 'approved'):
        conn.close()
        return ok(redirect=f'/order/{order_id}/preview')
    # Clients must NEVER see the internal admin/QC view
    if current_user.role == 'client':
        conn.close()
        return ok(redirect='/client/orders')
    order = dict(o)
    if o['assigned_pilot_id']:
        p = conn.execute('SELECT name FROM users WHERE id=?', (o['assigned_pilot_id'],)).fetchone()
        order['pilot_name'] = p['name'] if p else '—'
    else:
        order['pilot_name'] = None
    steps = [dict(s) for s in conn.execute(
        'SELECT * FROM pilot_steps WHERE order_id = ? ORDER BY id', (order_id,)).fetchall()]
    attachments = [dict(a) for a in conn.execute(
        'SELECT * FROM order_attachments WHERE order_id = ?', (order_id,)).fetchall()]
    deliverables = [dict(d) for d in conn.execute(
        'SELECT * FROM deliverables WHERE order_id = ? ORDER BY id', (order_id,)).fetchall()]
    conn.close()
    intake = json.loads(order.get('intake_data') or '{}')
    return ok({'order': order, 'steps': steps, 'intake': intake,
               'attachments': attachments, 'deliverables': deliverables})


# ── /order/<id>/edit (app.py 3429-3457) ────────────────────
@require_POST
@login_required
def client_edit_order(request, order_id):
    current_user = request.user
    if current_user.role not in ('client', 'admin'):
        return err('Forbidden', status=403, success=False)
    conn = get_db()
    if current_user.role == 'client':
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND client_id = ?',
                         (order_id, current_user.id)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', status=404, success=False)
    if o['status'] not in ('pending', None):
        conn.close()
        return err('Order can no longer be edited (already assigned)', success=False)
    data = body(request)
    intake = data.get('intake')
    if not isinstance(intake, dict):
        conn.close()
        return err('Invalid intake data', success=False)
    conn.execute('UPDATE orders SET intake_data = ? WHERE id = ?',
                 (json.dumps(intake), order_id))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /order/<id>/preview (app.py 3621-3653) ─────────────────
@role_required('client')
def client_order_preview(request, order_id):
    current_user = request.user
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=? AND client_id=?',
                     (order_id, current_user.id)).fetchone()
    if not o or o['status'] not in ('delivered', 'approved'):
        conn.close()
        return err('Preview is only available once your delivery is ready.',
                   redirect='/client/orders', status=403)
    order = dict(o)
    deliverables = [dict(d) for d in conn.execute(
        'SELECT * FROM deliverables WHERE order_id=? ORDER BY id', (order_id,)).fetchall()]
    attachments = [dict(a) for a in conn.execute(
        "SELECT * FROM order_attachments WHERE order_id=? ORDER BY id", (order_id,)).fetchall()]
    user_row = conn.execute('SELECT edit_credits FROM users WHERE id=?',
                            (current_user.id,)).fetchone()
    edit_credits = user_row['edit_credits'] if user_row else 0
    paid_count = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=? AND payment_method IN ('payu','free_pass')",
        (current_user.id,)).fetchone()[0]
    _tc = (current_user.phone or '') == TEST_CLIENT_PHONE
    has_paid_before = paid_count > 0 or _tc
    conn.close()
    task_label = TASK_LABELS.get(order.get('task', ''), order.get('task', ''))
    return ok({'order': order, 'deliverables': deliverables, 'attachments': attachments,
               'task_label': task_label, 'support_whatsapp': SUPPORT_WHATSAPP,
               'support_upi': SUPPORT_UPI, 'edit_credits': edit_credits,
               'has_paid_before': has_paid_before})


# ── /api/client/order-status (app.py 3657-3668) ────────────
@role_required('client')
@rate_limit(limit=30, window=60, json_response=True)  # M-5
def api_client_order_status(request):
    try:
        order_id = int(request.GET.get('order_id'))
    except (TypeError, ValueError):
        order_id = None
    conn = get_db()
    o = conn.execute('SELECT status FROM orders WHERE id=? AND client_id=?',
                     (order_id, request.user.id)).fetchone()
    conn.close()
    if not o:
        return ok({'status': 'unknown'})
    return ok({'status': o['status']})


# ── helper used by client_choice edit blocks (verbatim logic) ──
def _save_edit_remarks(request, conn, order_id, allowed_exts):
    deliverable_ids = request.POST.getlist('deliverable_id[]')
    remarks_list = request.POST.getlist('edit_remark[]')
    att_files = request.FILES.getlist('edit_attachment[]')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(settings.UPLOAD_FOLDER, f'order_{order_id}_edits_{ts}')

    def _ext_ok(fn):
        e = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
        return e in allowed_exts

    for i, (did, remark) in enumerate(zip(deliverable_ids, remarks_list)):
        remark = remark.strip()
        att_fn = att_orig = att_size = None
        if i < len(att_files) and att_files[i] and att_files[i].name and _ext_ok(att_files[i].name):
            f = att_files[i]
            os.makedirs(folder, exist_ok=True)
            sfn = secure_filename(f.name) or 'att'
            stem = sfn.rsplit('.', 1)[0] if '.' in sfn else sfn
            safe, path = _unique_named_path(folder, f'edit_{order_id}_{i}_{stem}', _file_ext(f.name))
            _save_django_file(f, path)
            att_fn = f'order_{order_id}_edits_{ts}/{safe}'
            att_orig = f.name
            att_size = os.path.getsize(path)
        if remark or att_fn:
            conn.execute(
                'INSERT INTO edit_requests (order_id,deliverable_id,remark,attachment_filename,attachment_original_name,attachment_size) VALUES (?,?,?,?,?,?)',
                (order_id, int(did) if did else None, remark, att_fn, att_orig, att_size))


_EDIT_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf', 'docx', 'doc', 'txt', 'mp4', 'mov', 'zip'}


# ── /order/<id>/client-choice (app.py 3700-3868) ───────────
@require_POST
@role_required('client')
def client_choice(request, order_id):
    """Handles client actions on the preview page: accept / edit_free /
    buy_edit_1 / buy_edit_3 / reject / pay_download / pay_edit."""
    current_user = request.user
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=? AND client_id=?',
                     (order_id, current_user.id)).fetchone()
    if not o or o['status'] != 'delivered':
        conn.close()
        return err('This order is not available for action.', redirect='/client/orders')

    action = request.POST.get('action', '').strip()

    # ── Accept & Download (paid users, no extra payment) ──
    if action == 'accept':
        if o['payment_method'] not in ('payu', 'free_pass'):
            conn.close()
            return err('Cannot accept — this order has no confirmed payment on file.',
                       redirect=f'/order/{order_id}/preview')
        conn.execute("UPDATE orders SET status='approved', completed_at=? WHERE id=?",
                     (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        log_status(conn, order_id, 'delivered', 'approved', current_user.id,
                   'Client accepted delivery — upfront payment already on file')
        conn.commit(); conn.close()
        return ok(redirect=f'/order/success?id={order_id}')

    # ── Edit Free (use 1 edit credit) ──
    if action == 'edit_free':
        user_row = conn.execute('SELECT edit_credits FROM users WHERE id=?',
                                (current_user.id,)).fetchone()
        credits = user_row['edit_credits'] if user_row else 0
        if credits <= 0:
            conn.close()
            return err('No edit credits remaining. Please purchase credits to submit an edit.',
                       redirect=f'/order/{order_id}/preview')
        conn.execute('UPDATE users SET edit_credits = edit_credits - 1 WHERE id=?',
                     (current_user.id,))
        conn.execute('DELETE FROM edit_requests WHERE order_id=?', (order_id,))
        conn.execute('UPDATE orders SET client_action=? WHERE id=?', ('edit_free', order_id))
        _save_edit_remarks(request, conn, order_id, _EDIT_EXTS)
        conn.execute("UPDATE orders SET status='edit_requested' WHERE id=?", (order_id,))
        log_status(conn, order_id, 'delivered', 'edit_requested', current_user.id,
                   'Client submitted free edit (1 credit deducted)')
        conn.commit(); conn.close()
        return ok(flash=[('success', 'Edit request submitted! The pilot will revise and redeliver.')],
                  redirect='/client/orders')

    # ── Buy Edit Credits then submit edit ──
    if action in ('buy_edit_1', 'buy_edit_3'):
        conn.execute('DELETE FROM edit_requests WHERE order_id=?', (order_id,))
        conn.execute('UPDATE orders SET client_action=? WHERE id=?', (action, order_id))
        _save_edit_remarks(request, conn, order_id, _EDIT_EXTS)
        conn.commit(); conn.close()
        return ok(redirect=f'/payment/initiate?order_id={order_id}')

    # ── Reject ──
    if action == 'reject':
        remark = request.POST.get('rejection_remark', '').strip()
        conn.execute(
            "UPDATE orders SET status='rejected_by_client', rejection_remark=?, client_action='rejected' WHERE id=?",
            (remark, order_id))
        log_status(conn, order_id, 'delivered', 'rejected_by_client', current_user.id,
                   f'Client rejected deliverable. Reason: {remark[:200]}')
        conn.commit(); conn.close()
        return ok(flash=[('success', 'Your feedback has been submitted. Our team will review it.')],
                  redirect='/client/orders')

    # ── Pay (download or edit) ──
    if action not in ('pay_download', 'pay_edit'):
        conn.close()
        return err('Invalid action.', redirect=f'/order/{order_id}/preview')

    conn.execute('DELETE FROM edit_requests WHERE order_id=?', (order_id,))
    conn.execute('UPDATE orders SET client_action=? WHERE id=?', (action, order_id))
    if action == 'pay_edit':
        _save_edit_remarks(request, conn, order_id, _EDIT_EXTS)
    conn.commit(); conn.close()
    return ok(redirect=f'/payment/initiate?order_id={order_id}')
