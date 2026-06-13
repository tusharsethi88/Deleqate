"""
api.views.pilot_extra — port of app.py pilot QC/submit/deliverable routes
(lines 3058-3216) and complete/restart (4130-4182).
"""
import os

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from werkzeug.utils import secure_filename
from datetime import datetime

from core.database import get_db, log_status
from core.auth import role_required
from core.business import is_allowed_upload, FRONTEND_URL
from api.helpers import body, ok, err


def _save_django_file(f, path):
    with open(path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)


# ── /api/pilot/qc (app.py 3058-3082) ───────────────────────
@require_POST
@role_required('pilot', 'admin')
def api_pilot_qc(request):
    current_user = request.user
    data = body(request)
    order_id = data.get('order_id')
    pov = data.get('pov', 'A')
    verdict = data.get('verdict', '').upper()   # PASS / MINOR FIXES / REGENERATE / BACK TO DESCRIBE
    passed = (verdict == 'PASS')
    result = 'pass' if passed else 'fail'
    status = 'qc_pass' if passed else ('qc_minor' if 'MINOR' in verdict else ('qc_regenerate' if 'REGENERATE' in verdict else 'qc_back_to_describe'))

    conn = get_db()
    conn.execute("UPDATE pilot_steps SET qc_result=?, qc_data=?, step_status=? WHERE order_id=? AND pov=?",
                 (result, verdict, status, order_id, pov))

    # Check if ALL POVs passed → auto-submit
    all_steps = conn.execute('SELECT * FROM pilot_steps WHERE order_id = ?', (order_id,)).fetchall()
    all_passed = all(s['qc_result'] == 'pass' for s in all_steps if s['render_filename'])
    if all_passed and len([s for s in all_steps if s['render_filename']]) == len(all_steps):
        o = conn.execute('SELECT status FROM orders WHERE id = ?', (order_id,)).fetchone()
        conn.execute("UPDATE orders SET status='submitted' WHERE id=?", (order_id,))
        log_status(conn, order_id, o['status'], 'submitted', current_user.id, 'All POVs passed QC')

    conn.commit(); conn.close()
    return ok({'success': True, 'result': result, 'all_passed': all_passed})


# ── /pilot/submit/<id> (app.py 3085-3119) ──────────────────
@require_POST
@role_required('pilot', 'admin')
def pilot_submit(request, order_id):
    current_user = request.user
    conn = get_db()
    # B-09: admin can submit on behalf of a pilot
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    # This is a full-page form POST from the server-rendered workflow page,
    # so we respond with real HTTP redirects (not JSON).
    dash = (FRONTEND_URL or '').rstrip('/') + '/pilot/dashboard'
    if o and o['status'] in ('assigned', 'in_progress', 'rejected', 'edit_requested'):
        if request.POST.get('qc_confirmed') != '1':
            conn.close()
            return HttpResponseRedirect(f'/pilot/job/{order_id}')
        deliverable_count = conn.execute(
            "SELECT COUNT(*) FROM deliverables WHERE order_id=?", (order_id,)).fetchone()[0]
        if deliverable_count == 0:
            conn.close()
            return HttpResponseRedirect(f'/pilot/job/{order_id}')
        conn.execute("UPDATE orders SET status='submitted', client_action=NULL WHERE id=?", (order_id,))
        log_status(conn, order_id, o['status'], 'submitted', current_user.id,
                   'Pilot submitted (revision)' if o['status'] == 'edit_requested' else 'Pilot submitted')
        conn.commit()
        conn.close()
        return HttpResponseRedirect(dash)
    conn.close()
    return HttpResponseRedirect(dash)


# ── /api/pilot/upload-deliverable (app.py 3121-3177) ───────
@require_POST
@role_required('pilot', 'admin')
def api_upload_deliverable(request):
    """Generic deliverable upload for non-render SKUs (video, zip, pdf, etc.)."""
    current_user = request.user
    order_id = int(request.POST.get('order_id', 0))
    f = request.FILES.get('file')
    if not f or not f.name:
        return err('No file')

    ext = os.path.splitext(f.name)[1].lower()
    if not is_allowed_upload(f.name, allowed={'mp4', 'zip', 'png', 'jpg', 'jpeg', 'pdf', 'docx', 'doc', 'mov', 'webm'}):  # M-3
        return err(f'File type {ext} not allowed')

    conn = get_db()
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', status=404)

    # Wipe old deliverables if order was rejected
    if o['status'] == 'rejected':
        old_rows = conn.execute(
            'SELECT filename FROM deliverables WHERE order_id = ?', (order_id,)).fetchall()
        for row in old_rows:
            old_path = os.path.join(settings.DELIVERABLES_FOLDER, row['filename'])
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass
        conn.execute('DELETE FROM deliverables WHERE order_id = ?', (order_id,))

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(settings.DELIVERABLES_FOLDER, f'order_{order_id}')
    os.makedirs(folder, exist_ok=True)
    safe = f'{ts}_{secure_filename(f.name) or "deliverable"}'
    path = os.path.join(folder, safe)
    _save_django_file(f, path)
    rel = f'order_{order_id}/{safe}'

    room_label = request.POST.get('room_label', '').strip() or None
    pov = request.POST.get('pov', 'A').strip()
    conn.execute(
        'INSERT INTO deliverables (order_id, pilot_id, pov, filename, original_name, file_label) VALUES (?, ?, ?, ?, ?, ?)',
        (order_id, current_user.id, pov, rel, f.name, room_label))
    if o['status'] == 'assigned':
        conn.execute("UPDATE orders SET status='in_progress' WHERE id=?", (order_id,))
        log_status(conn, order_id, 'assigned', 'in_progress', current_user.id, 'Deliverable uploaded')
    conn.commit()
    deliverable_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return ok({'success': True, 'filename': rel, 'deliverable_id': deliverable_id})


# ── /api/pilot/delete-deliverable (app.py 3179-3216) ───────
@require_POST
@role_required('pilot', 'admin')
def api_delete_deliverable(request):
    """Delete a single uploaded deliverable (before submission)."""
    current_user = request.user
    data = body(request)
    deliverable_id = data.get('deliverable_id')
    order_id = data.get('order_id')
    if not deliverable_id or not order_id:
        return err('Missing params', success=False)
    conn = get_db()
    if current_user.role == 'admin':
        row = conn.execute('SELECT * FROM deliverables WHERE id=? AND order_id=?',
                           (deliverable_id, order_id)).fetchone()
    else:
        row = conn.execute('SELECT d.* FROM deliverables d JOIN orders o ON d.order_id=o.id '
                           'WHERE d.id=? AND d.order_id=? AND o.assigned_pilot_id=?',
                           (deliverable_id, order_id, current_user.id)).fetchone()
    if not row:
        conn.close()
        return err('Not found or access denied', status=404, success=False)
    o = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()
    if o and o['status'] in ('under_review', 'delivered', 'approved'):
        conn.close()
        return err('Cannot delete after submission', success=False)
    file_path = os.path.join(settings.DELIVERABLES_FOLDER, row['filename'])
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    conn.execute('DELETE FROM deliverables WHERE id=?', (deliverable_id,))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/complete (app.py 4130-4151) ─────────────────
@require_POST
@role_required('pilot', 'admin')
def api_pilot_complete(request):
    current_user = request.user
    data = body(request)
    order_id = data.get('order_id')
    conn = get_db()
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    is_revision = o['status'] == 'edit_requested'
    conn.execute("UPDATE orders SET status='under_review', qc_notes=NULL, client_action=NULL WHERE id=?",
                 (order_id,))
    log_status(conn, order_id, o['status'], 'under_review', current_user.id,
               'Pilot submitted revision for review' if is_revision else 'Pilot submitted for review')
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/restart-job (app.py 4154-4182) ──────────────
@require_POST
@role_required('pilot', 'admin')
def api_pilot_restart_job(request):
    current_user = request.user
    data = body(request)
    order_id = data.get('order_id')
    conn = get_db()
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    if not o:
        conn.close()
        return err('Order not found', success=False)
    conn.execute("""
        UPDATE orders
        SET prompt_a_output=NULL, wall_inventory_output=NULL, moodboard_output=NULL, status='in_progress'
        WHERE id=?
    """, (order_id,))
    conn.execute("""
        UPDATE pilot_steps
        SET spatial_facts=NULL, generated_prompt=NULL, qc_result=NULL, qc_data=NULL,
            render_filename=NULL, flow_prompt=NULL, labeled_plan_filename=NULL,
            step_status='pending'
        WHERE order_id=?
    """, (order_id,))
    conn.commit(); conn.close()
    return ok({'success': True})
