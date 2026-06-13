"""
api.views.admin — port of app.py admin routes (lines 2511-2642, 3461-3617,
3674-3694, 4077-4123, 4189-4235, 4458-4480).
"""
import os, json, base64
import re as _re
from datetime import datetime

from django.conf import settings
from django.views.decorators.http import require_POST
from werkzeug.security import generate_password_hash, check_password_hash

from core.database import get_db, log_status, PRICING_MAP, get_setting, set_setting
from core.auth import role_required
from core.business import TASK_LABELS, _file_ext
from api.helpers import body, ok, err


def _save_django_file(f, path):
    with open(path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)


# ── /admin/dashboard data (app.py 4189-4235) ───────────────
@role_required('admin')
def admin_home(request):
    conn = get_db()
    raw_orders = [dict(r) for r in conn.execute(
        'SELECT * FROM orders ORDER BY created_at DESC').fetchall()]
    order_list = []
    for od in raw_orders:
        if od.get('assigned_pilot_id'):
            p = conn.execute('SELECT name FROM users WHERE id=?',
                             (od['assigned_pilot_id'],)).fetchone()
            od['pilot_name'] = p['name'] if p else '—'
        else:
            od['pilot_name'] = None
        try:
            od['intake'] = json.loads(od.get('intake_data') or '{}')
        except Exception:
            od['intake'] = {}
        first_del = conn.execute(
            "SELECT filename FROM deliverables WHERE order_id=? AND filename NOT LIKE '%.mp4' AND filename NOT LIKE '%.webm' ORDER BY id ASC LIMIT 1",
            (od['id'],)).fetchone()
        od['first_deliverable'] = first_del['filename'] if first_del else None
        order_list.append(od)
    pilots = [dict(r) for r in conn.execute(
        "SELECT * FROM users WHERE role IN ('pilot')").fetchall()]
    pilot_list = []
    for p in pilots:
        pd = dict(p)
        pd.pop('password_hash', None)   # never expose hashes over JSON
        pd['active_jobs'] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE assigned_pilot_id=? AND status IN ('assigned','in_progress','under_review','submitted')",
            (p['id'],)).fetchone()[0]
        pd['done_jobs'] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE assigned_pilot_id=? AND status IN ('delivered','approved')",
            (p['id'],)).fetchone()[0]
        pilot_list.append(pd)

    stats = {
        'pending':     conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
        'in_progress': conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('assigned','in_progress','under_review','submitted')").fetchone()[0],
        'delivered':   conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('delivered','approved')").fetchone()[0],
        'revenue':     conn.execute("SELECT COALESCE(SUM(total_price),0) FROM orders WHERE status='approved'").fetchone()[0],
    }
    skus = [dict(r) for r in conn.execute('SELECT * FROM skus ORDER BY sort_order').fetchall()]
    conn.close()
    return ok({'orders': order_list, 'pilots': pilot_list, 'stats': stats,
               'task_labels': TASK_LABELS, 'skus': skus,
               'settings': {'voice_brief_enabled': get_setting('voice_brief_enabled', '1') == '1'}})


# ── /api/admin/setting/toggle — flip a boolean app_setting ──
@require_POST
@role_required('admin')
def api_admin_setting_toggle(request):
    data = body(request)
    key = data.get('key', '').strip()
    allowed = {'voice_brief_enabled'}
    if key not in allowed:
        return err('Unknown setting', status=400)
    new_val = '0' if get_setting(key, '1') == '1' else '1'
    set_setting(key, new_val)
    return ok({'success': True, 'key': key, 'value': new_val == '1'})


# ── /admin/assign/<id> (app.py 2511-2523) ──────────────────
@require_POST
@role_required('admin')
def admin_assign(request, order_id):
    pilot_id = request.POST.get('pilot_id')
    if pilot_id:
        conn = get_db()
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        conn.execute('UPDATE orders SET assigned_pilot_id = ?, status = ?, assigned_at = CURRENT_TIMESTAMP WHERE id = ?',
                     (int(pilot_id), 'assigned', order_id))
        log_status(conn, order_id, o['status'], 'assigned', request.user.id, 'Assigned by admin')
        conn.commit(); conn.close()
        return ok(flash=[('success', f'Order #{order_id} assigned.')], redirect='/admin/dashboard')
    return ok(redirect='/admin/dashboard')


# ── /admin/qc/<id> (app.py 2525-2542) ──────────────────────
@require_POST
@role_required('admin')
def admin_qc(request, order_id):
    action = request.POST.get('action')
    notes = request.POST.get('qc_notes', '')
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    fl = []
    if action == 'approve':
        conn.execute("UPDATE orders SET status='delivered', qc_notes=?, delivered_at=? WHERE id=?",
                     (notes, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        log_status(conn, order_id, o['status'], 'delivered', request.user.id, f'QC approved. {notes}')
        fl = [('success', f'Order #{order_id} delivered!')]
    elif action == 'reject':
        conn.execute("UPDATE orders SET status='rejected', qc_notes=? WHERE id=?", (notes, order_id))
        log_status(conn, order_id, o['status'], 'rejected', request.user.id, f'QC rejected. {notes}')
        fl = [('error', f'Order #{order_id} rejected.')]
    conn.commit(); conn.close()
    return ok(flash=fl, redirect='/admin/dashboard')


# ── /admin/create-pilot (app.py 2544-2563) ─────────────────
@require_POST
@role_required('admin')
def admin_create_pilot(request):
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    pw = request.POST.get('password', '').strip()
    if not all([name, email, pw]):
        return err('All fields required.', redirect='/admin/dashboard')
    conn = get_db()
    if conn.execute('SELECT id FROM users WHERE email=? AND role=?', (email, 'pilot')).fetchone():
        conn.close()
        return err('A pilot account with this email already exists.', redirect='/admin/dashboard')
    conn.execute('INSERT INTO users (email,password_hash,name,phone,role) VALUES (?,?,?,?,?)',
                 (email, generate_password_hash(pw), name, phone, 'pilot'))
    conn.commit(); conn.close()
    return ok(flash=[('success', f'Pilot "{name}" created.')], redirect='/admin/dashboard')


# ── /api/admin/pilot/toggle-status (app.py 2565-2580) ──────
@require_POST
@role_required('admin')
def admin_toggle_pilot_status(request):
    data = body(request)
    pilot_id = data.get('pilot_id')
    if not pilot_id:
        return err('Missing pilot_id')
    conn = get_db()
    row = conn.execute("SELECT account_status FROM users WHERE id=? AND role='pilot'", (pilot_id,)).fetchone()
    if not row:
        conn.close()
        return err('Pilot not found', status=404)
    new_status = 'inactive' if row['account_status'] == 'active' else 'active'
    conn.execute("UPDATE users SET account_status=? WHERE id=?", (new_status, pilot_id))
    conn.commit(); conn.close()
    return ok({'status': new_status})


# ── hero video upload/delete (app.py 2585-2621) ────────────
HERO_VIDEO_EXTS = ('mp4', 'webm', 'mov', 'ogg')


@require_POST
@role_required('admin')
def api_admin_hero_video(request):
    f = request.FILES.get('video')
    if not f or not f.name:
        return err('No file uploaded.')
    ext = _file_ext(f.name, default='')
    if ext not in HERO_VIDEO_EXTS:
        return err(f'Format .{ext} not allowed. Use: ' + ', '.join(HERO_VIDEO_EXTS))
    for e in HERO_VIDEO_EXTS:
        old = os.path.join(settings.UPLOAD_FOLDER, f'hero_video.{e}')
        try:
            if os.path.exists(old):
                os.remove(old)
        except Exception:
            pass
    _save_django_file(f, os.path.join(settings.UPLOAD_FOLDER, f'hero_video.{ext}'))
    return ok({'url': f'/uploads/hero_video.{ext}'})


@require_POST
@role_required('admin')
def api_admin_hero_video_delete(request):
    removed = False
    for e in HERO_VIDEO_EXTS:
        p = os.path.join(settings.UPLOAD_FOLDER, f'hero_video.{e}')
        try:
            if os.path.exists(p):
                os.remove(p)
                removed = True
        except Exception:
            pass
    return ok({'removed': removed})


# ── /api/admin/change-password (app.py 2623-2642) ──────────
@require_POST
@role_required('admin')
def admin_change_password(request):
    data = body(request)
    cur_pw = str(data.get('current_password', ''))[:128]
    new_pw = str(data.get('new_password', ''))[:128]
    if not cur_pw or not new_pw:
        return err('Both fields are required.')
    if len(new_pw) < 8:
        return err('Password must be at least 8 characters.')
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id=? AND role=?',
                       (request.user.id, 'admin')).fetchone()
    if not row or not check_password_hash(row['password_hash'], cur_pw):
        conn.close()
        return err('Current password is incorrect.')
    conn.execute('UPDATE users SET password_hash=? WHERE id=?',
                 (generate_password_hash(new_pw), request.user.id))
    conn.commit(); conn.close()
    return ok()


# ── /api/admin/assign (app.py 3461-3480) ───────────────────
@require_POST
@role_required('admin')
def api_admin_assign(request):
    data = body(request)
    order_id = data.get('order_id')
    pilot_id = data.get('pilot_id')
    if not order_id or not pilot_id:
        return err('Missing order_id or pilot_id', success=False)
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    conn.execute('UPDATE orders SET assigned_pilot_id = ?, status = ?, assigned_at = CURRENT_TIMESTAMP WHERE id = ?',
                 (pilot_id, 'assigned', order_id))
    log_status(conn, order_id, o['status'], 'assigned', request.user.id, 'Assigned via admin panel')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/review-image (app.py 3483-3516) ─────────────
@require_POST
@role_required('admin')
def api_admin_review_image(request):
    data = body(request)
    deliverable_id = data.get('deliverable_id')
    action = data.get('action')           # 'approve' | 'reject'
    remark = (data.get('remark') or '').strip()
    if action not in ('approve', 'reject'):
        return err('Invalid action', success=False)
    conn = get_db()
    d = conn.execute('SELECT * FROM deliverables WHERE id = ?', (deliverable_id,)).fetchone()
    if not d:
        conn.close()
        return err('Deliverable not found', success=False)
    new_img_status = 'approved' if action == 'approve' else 'rejected'
    conn.execute('UPDATE deliverables SET img_status=?, img_remark=? WHERE id=?',
                 (new_img_status, remark or None, deliverable_id))
    order_id = d['order_id']
    all_imgs = conn.execute('SELECT img_status FROM deliverables WHERE order_id=?', (order_id,)).fetchall()
    if all(r['img_status'] == 'approved' for r in all_imgs):
        o = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()
        conn.execute("UPDATE orders SET status='delivered', delivered_at=? WHERE id=?",
                     (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        log_status(conn, order_id, o['status'], 'delivered', request.user.id,
                   'All images approved by admin — delivered to client')
    elif new_img_status == 'rejected':
        o = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()
        conn.execute("UPDATE orders SET status='rejected', qc_notes=? WHERE id=?",
                     (remark, order_id))
        log_status(conn, order_id, o['status'], 'rejected', request.user.id,
                   f'Admin rejected image: {remark}')
    conn.commit(); conn.close()
    return ok({'success': True, 'img_status': new_img_status})


# ── /api/admin/approve (app.py 3521-3536) ──────────────────
@require_POST
@role_required('admin')
def api_admin_approve(request):
    data = body(request)
    order_id = data.get('order_id')
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    conn.execute("UPDATE orders SET status='approved', completed_at=? WHERE id=?",
                 (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
    log_status(conn, order_id, o['status'], 'approved', request.user.id,
               'Admin marked order complete — fully approved')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/mark-delivered (app.py 3539-3555) ───────────
@require_POST
@role_required('admin')
def api_admin_mark_delivered(request):
    data = body(request)
    order_id = data.get('order_id')
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    conn.execute("UPDATE orders SET status='delivered', delivered_at=? WHERE id=?",
                 (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
    log_status(conn, order_id, o['status'], 'delivered', request.user.id, 'Admin marked delivered after QC')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/reject-to-pilot (app.py 3558-3574) ──────────
@require_POST
@role_required('admin')
def api_admin_reject_to_pilot(request):
    data = body(request)
    order_id = data.get('order_id')
    note = data.get('note', '')
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    conn.execute("UPDATE orders SET status='rejected', qc_notes=? WHERE id=?", (note, order_id))
    log_status(conn, order_id, o['status'], 'rejected', request.user.id, f'Admin rejected back to pilot. {note}')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/save-annotation (app.py 3577-3617) ──────────
@require_POST
@role_required('admin')
def api_admin_save_annotation(request):
    data = body(request)
    order_id = data.get('order_id')
    note = (data.get('note') or '').strip()
    img_b64 = data.get('image_b64', '')   # data:image/png;base64,....

    if not order_id:
        return err('order_id required', success=False)

    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', status=404, success=False)

    ann_filename = None
    if img_b64:
        match = _re.match(r'data:image/\w+;base64,(.*)', img_b64, _re.DOTALL)
        raw = base64.b64decode(match.group(1) if match else img_b64)
        folder = os.path.join(settings.UPLOAD_FOLDER, f'order_{order_id}_annotations')
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'qc_annotation_{ts}.png'
        with open(os.path.join(folder, fname), 'wb') as fh:
            fh.write(raw)
        ann_filename = f'order_{order_id}_annotations/{fname}'

    conn.execute(
        "UPDATE orders SET status='rejected', qc_notes=?, qc_annotation_filename=? WHERE id=?",
        (note, ann_filename, order_id))
    log_status(conn, order_id, o['status'], 'rejected', request.user.id,
               f'Admin rejected with annotation. {note}')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/confirm-payment (app.py 3674-3694) ──────────
@require_POST
@role_required('admin')
def api_admin_confirm_payment(request):
    data = body(request)
    order_id = data.get('order_id')
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    if o['status'] != 'delivered':
        conn.close()
        return err(f"Order is '{o['status']}' — only 'delivered' orders can be payment-confirmed",
                   success=False)
    conn.execute("UPDATE orders SET status='approved', completed_at=? WHERE id=?",
                 (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), order_id))
    log_status(conn, order_id, 'delivered', 'approved', request.user.id,
               'Admin confirmed payment via WhatsApp — download unlocked')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/admin/sku/toggle (app.py 4077-4093) ───────────────
@require_POST
@role_required('admin')
def api_admin_sku_toggle(request):
    data = body(request)
    task_key = data.get('task_key', '').strip()
    if not task_key:
        return err('task_key required')
    conn = get_db()
    row = conn.execute('SELECT is_active FROM skus WHERE task_key=?', (task_key,)).fetchone()
    if not row:
        conn.close()
        return err('SKU not found', status=404)
    new_state = 0 if row['is_active'] else 1
    conn.execute('UPDATE skus SET is_active=? WHERE task_key=?', (new_state, task_key))
    conn.commit(); conn.close()
    return ok({'success': True, 'is_active': new_state})


# ── /api/admin/sku/edit (app.py 4096-4123) ─────────────────
@require_POST
@role_required('admin')
def api_admin_sku_edit(request):
    data = body(request)
    task_key = data.get('task_key', '').strip()
    label = data.get('label', '').strip()
    price_str = str(data.get('price', '')).strip()
    note = data.get('note', '').strip()
    if not task_key:
        return err('task_key required')
    conn = get_db()
    row = conn.execute('SELECT * FROM skus WHERE task_key=?', (task_key,)).fetchone()
    if not row:
        conn.close()
        return err('SKU not found', status=404)
    new_label = label if label else row['label']
    try:
        new_price = int(float(price_str) * 100) if price_str else row['price_paisa']
    except ValueError:
        conn.close()
        return err('Invalid price')
    conn.execute('UPDATE skus SET label=?, price_paisa=?, note=? WHERE task_key=?',
                 (new_label, new_price, note, task_key))
    conn.commit(); conn.close()
    PRICING_MAP[task_key] = (new_price, row['price_type'], row['price_label'])
    TASK_LABELS[task_key] = new_label
    return ok({'success': True, 'price_paisa': new_price, 'label': new_label})


# ── /api/autopilot/status (admin-only, app.py 4458-4480) ───
@role_required('admin')
def api_autopilot_status(request):
    conn = get_db()
    ap_row = conn.execute('SELECT * FROM autopilot_status LIMIT 1').fetchone()
    ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
    pilot = conn.execute(
        "SELECT id FROM users WHERE email=? AND role='pilot'", (ap_email,)).fetchone()
    queue = {}
    if pilot:
        queue['assigned'] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE assigned_pilot_id=? AND status='assigned'",
            (pilot['id'],)).fetchone()[0]
        queue['in_progress'] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE assigned_pilot_id=? AND status='in_progress'",
            (pilot['id'],)).fetchone()[0]
    conn.close()
    return ok({'autopilot': dict(ap_row) if ap_row else None, 'queue': queue})
