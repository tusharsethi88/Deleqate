"""
api.views.autopilot — port of app.py AutoPilot endpoints (lines 4243-4891).
Token-gated with X-AutoPilot-Token header (HMAC-safe compare), exactly as
in the Flask app. These endpoints are CSRF-exempt (see core.middleware).
"""
import os, json, hmac as _hmac
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from werkzeug.utils import secure_filename

from core.database import get_db
from core.security import safe_serve_file
from core.business import _file_ext, _clean_label, _unique_named_path
from core.vs_prompts import (
    build_virtual_staging_prompt, build_gemini_room_analysis_prompt,
    parse_gemini_spatial_response, build_spatial_block,
)
from api.helpers import body as _json_body


def _autopilot_auth(request):
    """Return True if request carries the valid autopilot token."""
    token = request.headers.get('X-AutoPilot-Token', '')
    expected = os.environ.get('AUTOPILOT_API_TOKEN', '')
    if not expected:
        return False
    return _hmac.compare_digest(token.encode(), expected.encode())


def _unauth():
    return JsonResponse({'error': 'Unauthorized'}, status=401)


# ── /api/autopilot/pending_orders (app.py 4254-4289) ───────
def api_autopilot_pending_orders(request):
    if not _autopilot_auth(request):
        return _unauth()
    ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
    conn = get_db()
    pilot = conn.execute(
        "SELECT id FROM users WHERE email=? AND role='pilot'", (ap_email,)).fetchone()
    if not pilot:
        conn.close()
        return JsonResponse({'orders': []})
    rows = conn.execute("""
        SELECT id, task, task_type, status, intake_data, client_name, client_email,
               created_at, assigned_at, render_count, brief_text
        FROM orders
        WHERE assigned_pilot_id=? AND status IN ('assigned','in_progress')
        ORDER BY created_at ASC
    """, (pilot['id'],)).fetchall()
    conn.close()
    orders = []
    for r in rows:
        od = dict(r)
        od['task_type'] = od.get('task_type') or od.get('task') or 'unknown'
        conn2 = get_db()
        atts = conn2.execute(
            "SELECT filename, original_name FROM order_attachments WHERE order_id=?",
            (od['id'],)).fetchall()
        conn2.close()
        od['attachments'] = [dict(a) for a in atts]
        orders.append(od)
    return JsonResponse({'orders': orders})


# ── /api/autopilot/order/<id> (app.py 4292-4310) ───────────
def api_autopilot_order_detail(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return JsonResponse({'error': 'Not found'}, status=404)
    od = dict(o)
    od['task_type'] = od.get('task_type') or od.get('task') or 'unknown'
    atts = conn.execute(
        "SELECT filename, original_name, file_size FROM order_attachments WHERE order_id=?",
        (order_id,)).fetchall()
    od['attachments'] = [dict(a) for a in atts]
    conn.close()
    return JsonResponse(od)


# ── /api/autopilot/download/<id>/<filename> (4313-4330) ────
def api_autopilot_download(request, order_id, filename):
    if not _autopilot_auth(request):
        return _unauth()
    conn = get_db()
    row = conn.execute(
        'SELECT filename FROM order_attachments WHERE order_id=? AND filename=?',
        (order_id, filename)).fetchone()
    conn.close()
    if not row:
        return JsonResponse({'error': 'Not found'}, status=404)
    return safe_serve_file(settings.UPLOAD_FOLDER, row['filename'])


# ── /api/autopilot/deliver/<id> (app.py 4333-4392) ─────────
@require_POST
def api_autopilot_deliver(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file'}, status=400)
    f = request.FILES['file']
    notes = request.POST.get('notes', 'Completed by AutoPilot')
    pov = request.POST.get('pov', 'A')
    file_label = request.POST.get('file_label', '').strip()
    conn = get_db()
    o = conn.execute('SELECT id, status FROM orders WHERE id=?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return JsonResponse({'error': 'Order not found'}, status=404)
    folder = os.path.join(settings.DELIVERABLES_FOLDER, f'order_{order_id}')
    os.makedirs(folder, exist_ok=True)
    ext = _file_ext(f.name or 'render.jpg', default='jpg')
    if file_label:
        base = f'{_clean_label(file_label)} POV {pov}'
    else:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        sfn = secure_filename(f.name) or f'deliverable.{ext}'
        base = f'POV{pov}_{ts}_{sfn.rsplit(".",1)[0] if "." in sfn else sfn}'
    safe, save_path = _unique_named_path(folder, base, ext)
    with open(save_path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)
    rel = f'order_{order_id}/{safe}'
    size = os.path.getsize(save_path)
    ap_email = os.environ.get('AUTOPILOT_EMAIL', 'deleqate@gmail.com')
    ap_pilot = conn.execute(
        "SELECT id FROM users WHERE email=? AND role='pilot'", (ap_email,)).fetchone()
    ap_pilot_id = ap_pilot['id'] if ap_pilot else 0
    conn.execute(
        'INSERT INTO deliverables (order_id, pilot_id, pov, filename, original_name, '
        'file_size, file_label, img_status, notes) VALUES (?,?,?,?,?,?,?,?,?)',
        (order_id, ap_pilot_id, pov, rel, f.name or safe,
         size, file_label or None, 'pending', notes))
    conn.execute(
        "UPDATE pilot_steps SET render_filename=?, step_status='render_uploaded' "
        "WHERE order_id=? AND pov=?", (rel, order_id, pov))
    conn.execute(
        "UPDATE orders SET status='under_review', delivered_at=CURRENT_TIMESTAMP WHERE id=?",
        (order_id,))
    conn.execute(
        "INSERT INTO status_log (order_id, old_status, new_status, note) VALUES (?,?,?,?)",
        (order_id, o['status'], 'under_review', f'AutoPilot delivered: {rel}'))
    conn.commit(); conn.close()
    return JsonResponse({'success': True, 'filename': rel})


# ── /api/autopilot/qc_pass/<id> (app.py 4395-4411) ─────────
@require_POST
def api_autopilot_qc_pass(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    notes = _json_body(request).get('notes', 'QC passed by AutoPilot')
    conn = get_db()
    o = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()
    if o:
        conn.execute("UPDATE orders SET qc_notes=? WHERE id=?", (notes, order_id))
        conn.execute(
            "INSERT INTO status_log (order_id, old_status, new_status, note) VALUES (?,?,?,?)",
            (order_id, o['status'], o['status'], f'AutoPilot QC passed: {notes}'))
        conn.commit()
    conn.close()
    return JsonResponse({'success': True})


# ── /api/autopilot/qc_fail/<id> (app.py 4414-4430) ─────────
@require_POST
def api_autopilot_qc_fail(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    notes = _json_body(request).get('notes', 'QC failed — escalated by AutoPilot')
    conn = get_db()
    o = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()
    if o:
        conn.execute("UPDATE orders SET qc_notes=?, status='rejected' WHERE id=?", (notes, order_id))
        conn.execute(
            "INSERT INTO status_log (order_id, old_status, new_status, note) VALUES (?,?,?,?)",
            (order_id, o['status'], 'rejected', f'AutoPilot QC failed: {notes}'))
        conn.commit()
    conn.close()
    return JsonResponse({'success': True})


# ── /api/autopilot/heartbeat (app.py 4433-4455) ────────────
@require_POST
def api_autopilot_heartbeat(request):
    if not _autopilot_auth(request):
        return _unauth()
    data = _json_body(request)
    conn = get_db()
    row = conn.execute('SELECT id FROM autopilot_status LIMIT 1').fetchone()
    if row:
        conn.execute("""
            UPDATE autopilot_status
            SET status='online', last_beat=CURRENT_TIMESTAMP, agent_email=?
            WHERE id=?
        """, (data.get('email', ''), row['id']))
    else:
        conn.execute("""
            INSERT INTO autopilot_status (status, last_beat, agent_email, tasks_done)
            VALUES ('online', CURRENT_TIMESTAMP, ?, 0)
        """, (data.get('email', ''),))
    conn.commit(); conn.close()
    return JsonResponse({'success': True, 'ts': datetime.utcnow().isoformat()})


# ── /api/autopilot/workflow/<id> (app.py 4761-4833) ────────
def api_autopilot_workflow(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return JsonResponse({'error': 'Not found'}, status=404)
    try:
        intake = json.loads(o['intake_data'] or '{}')
    except Exception:
        intake = {}
    atts = [dict(a) for a in conn.execute(
        'SELECT filename, original_name, attachment_type, file_label '
        'FROM order_attachments WHERE order_id=? ORDER BY id', (order_id,)).fetchall()]
    conn.close()

    task = o['task']
    rooms_out = []
    if task == 'virtual_staging':
        rooms = intake.get('rooms', [])
        room_labels = [r.get('label', f'Room {i+1}') if isinstance(r, dict) else str(r)
                       for i, r in enumerate(rooms)]
        if not room_labels:
            room_labels = sorted({a.get('file_label') for a in atts
                                  if a.get('attachment_type') == 'room_photo' and a.get('file_label')})
        photos_a = [a for a in atts if a['attachment_type'] == 'room_photo']
        photos_b = [a for a in atts if a['attachment_type'] == 'room_photo_b']
        moodboards = [a for a in atts if a['attachment_type'] == 'moodboard']

        def _match(pool, label, idx):
            for a in pool:
                if a.get('file_label') == label:
                    return a['filename']
            return pool[idx]['filename'] if idx < len(pool) else None

        for i, label in enumerate(room_labels):
            pov_a = _match(photos_a, label, i)
            pov_b = _match(photos_b, label, i)
            mood = _match(moodboards, label, i)
            rooms_out.append({
                'label': label,
                'pov_a': pov_a,
                'pov_b': pov_b,
                'moodboard': mood,
                'prompt': build_virtual_staging_prompt(
                    intake, label, has_pov_b=bool(pov_b), has_moodboard=bool(mood)),
                'gemini_prompt': build_gemini_room_analysis_prompt(label),
            })

    return JsonResponse({
        'order_id': order_id,
        'task': task,
        'intake': intake,
        'rooms': rooms_out,
        'workflow_steps': [
            'For each room: open Google Flow, create/enter a project',
            'Upload POV A (staging canvas), POV B (geometry reference) and moodboard (style reference) if present',
            'Paste the exact pre-built prompt and generate',
            'Verify: no floating furniture, geometry preserved, photorealistic',
            'Download the result and submit as deliverable for that room',
        ],
    })


# ── /api/autopilot/spatial/<id> (app.py 4836-4886) ─────────
@require_POST
def api_autopilot_spatial(request, order_id):
    if not _autopilot_auth(request):
        return _unauth()
    data = _json_body(request)
    room_label = data.get('room_label', '')
    pov = data.get('pov', 'A')
    gemini_text = data.get('gemini_text', '')
    if not room_label or not gemini_text:
        return JsonResponse({'error': 'room_label and gemini_text required'}, status=400)

    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    if not o:
        conn.close()
        return JsonResponse({'error': 'Not found'}, status=404)
    try:
        intake = json.loads(o['intake_data'] or '{}')
    except Exception:
        intake = {}
    atts = conn.execute(
        'SELECT attachment_type, file_label FROM order_attachments WHERE order_id=?',
        (order_id,)).fetchall()
    has_pov_b = any(a['attachment_type'] == 'room_photo_b' for a in atts)
    has_mood = any(a['attachment_type'] == 'moodboard' for a in atts)

    spatial_data = parse_gemini_spatial_response(gemini_text)
    spatial_block = build_spatial_block(spatial_data)
    final_prompt = build_virtual_staging_prompt(
        intake, room_label, has_pov_b=has_pov_b, has_moodboard=has_mood,
        spatial_block=spatial_block)

    existing = conn.execute(
        'SELECT id FROM pilot_steps WHERE order_id=? AND pov=?', (order_id, pov)).fetchone()
    if existing:
        conn.execute('UPDATE pilot_steps SET flow_prompt=? WHERE order_id=? AND pov=?',
                     (final_prompt, order_id, pov))
    else:
        conn.execute('INSERT INTO pilot_steps (order_id, pov, flow_prompt) VALUES (?,?,?)',
                     (order_id, pov, final_prompt))
    conn.commit(); conn.close()
    return JsonResponse({'success': True, 'prompt': final_prompt, 'spatial': spatial_data})


# ── /api/ping_autopilot_test_xyz (app.py 4889-4891) ────────
def api_ping_test(request):
    return HttpResponse('pong_autopilot_123', status=200)
