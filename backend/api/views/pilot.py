"""
api.views.pilot — port of app.py pilot routes (lines 2648-3220, 4130-4187).
"""
import os, json
from datetime import datetime

from django.conf import settings
from django.views.decorators.http import require_POST
from werkzeug.utils import secure_filename

from django.http import HttpResponse, HttpResponseRedirect
from core.database import get_db, log_status
from core.auth import role_required
from core.templating import render_flask_template
from core.business import (
    TASK_LABELS, is_allowed_upload, _file_ext,
    _clean_label, _unique_named_path, _IMAGE_EXTS,
    select_clips_for_reel, build_kling_narrative_v3, build_flow_prompts_for_order,
)
from api.helpers import body, ok, err


def _save_django_file(f, path):
    with open(path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)


def verify_image_content(uploaded):
    """M-3 content check (Django port of business.verify_image_content):
    image uploads must actually parse as an image."""
    try:
        from PIL import Image as _PILImage
        pos = uploaded.file.tell()
        img = _PILImage.open(uploaded.file)
        img.verify()
        uploaded.file.seek(pos)
        return True
    except Exception:
        try:
            uploaded.file.seek(0)
        except Exception:
            pass
        return False


def _enrich(rows, conn=None, with_attachments=False):
    result = []
    for o in rows:
        od = dict(o)
        od['intake'] = json.loads(o['intake_data'] or '{}')
        od['task_label'] = TASK_LABELS.get(o['task'], o['task'])
        if with_attachments and conn is not None:
            od['attachments'] = [dict(a) for a in conn.execute(
                'SELECT * FROM order_attachments WHERE order_id = ?', (o['id'],)).fetchall()]
        result.append(od)
    return result


# ── /pilot/dashboard (app.py 2648-2682) ────────────────────
@role_required('pilot', 'admin')
def pilot_dashboard_v2(request):
    current_user = request.user
    conn = get_db()
    active_rows = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id=? AND status IN ('assigned','in_progress','edit_requested','under_review') ORDER BY created_at DESC",
        (current_user.id,)).fetchall()
    submitted_rows = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id=? AND status='submitted' ORDER BY created_at DESC",
        (current_user.id,)).fetchall()
    done_rows = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id=? AND status IN ('delivered','approved') ORDER BY created_at DESC LIMIT 50",
        (current_user.id,)).fetchall()
    rejected_rows = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id=? AND status='rejected' ORDER BY created_at DESC LIMIT 20",
        (current_user.id,)).fetchall()
    conn.close()
    active_jobs = _enrich(active_rows) + _enrich(submitted_rows)
    completed_jobs = _enrich(done_rows)
    rejected_jobs = _enrich(rejected_rows)
    return ok({'active_jobs': active_jobs, 'completed_jobs': completed_jobs,
               'rejected_jobs': rejected_jobs,
               'active_count': len(active_jobs), 'done_count': len(completed_jobs)})


# ── /pilot/dashboard-legacy (app.py 2684-2709) ─────────────
@role_required('pilot', 'admin')
def pilot_dashboard_legacy(request):
    current_user = request.user
    conn = get_db()
    active = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id = ? AND status IN ('assigned','in_progress','rejected')",
        (current_user.id,)).fetchall()
    done = conn.execute(
        "SELECT * FROM orders WHERE assigned_pilot_id = ? AND status IN ('submitted','qc_review','delivered')",
        (current_user.id,)).fetchall()
    active_list = _enrich(active, conn, with_attachments=True)
    done_list = _enrich(done)
    conn.close()
    return ok({'active': active_list, 'done': done_list})


# ── /pilot/job/<id> (app.py 2717-2827) ─────────────────────
@role_required('pilot', 'admin')
def pilot_job(request, order_id):
    """Main pilot execution data — everything pilot_sku_workflow.html got."""
    current_user = request.user
    conn = get_db()
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    if not o:
        conn.close()
        return err('Order not found or not assigned to you.',
                   redirect='/pilot/dashboard', status=404)

    order = dict(o)
    intake = json.loads(o['intake_data'] or '{}')
    order['intake'] = intake

    rows = conn.execute(
        'SELECT filename, attachment_type, original_name, file_label FROM order_attachments WHERE order_id = ?',
        (order_id,)).fetchall()
    order['attachments'] = ','.join([r['filename'] for r in rows if r['filename']])
    order['attachments_data'] = [dict(r) for r in rows]
    moodboard_filename = next((r['filename'] for r in rows if r['attachment_type'] == 'moodboard'), None)

    pov_list = [dict(s) for s in conn.execute(
        'SELECT * FROM pilot_steps WHERE order_id = ? ORDER BY id', (order_id,)).fetchall()]

    # Auto-advance assigned → in_progress when pilot first opens job
    if o['status'] == 'assigned':
        conn.execute("UPDATE orders SET status='in_progress' WHERE id=?", (order_id,))
        conn.commit()

    task_label = TASK_LABELS.get(o['task'], o['task'])

    # ── Property Reel: compute clip selection + narrative + Flow prompts ──
    reel_clips, reel_skipped, reel_narrative, flow_prompts = [], [], '', {}
    if o['task'] == 'property_reel':
        photo_labels = intake.get('photo_labels', [])
        reel_tier = intake.get('reel_tier', 'hook').lower()
        prop_name = intake.get('property_name', '')
        prop_type = intake.get('property_type', 'Residential')
        location = intake.get('location', '')
        tone = intake.get('tone', 'Family')
        bhk_size = intake.get('bhk_size', '')
        interior_style = intake.get('interior_style', 'Modern/Contemporary')
        furnished_status = intake.get('furnished_status', 'Fully Furnished')
        price_bracket = intake.get('price_bracket', '')
        special_note = intake.get('special_note', '')

        if photo_labels:
            selected, skipped = select_clips_for_reel(photo_labels, reel_tier)
            reel_clips, reel_skipped = selected, skipped
            reel_narrative = build_kling_narrative_v3(
                selected, prop_name=prop_name, location=location,
                prop_type=prop_type, tone=tone, bhk_size=bhk_size)
            flow_prompts = build_flow_prompts_for_order(
                selected, tone=tone, prop_type=prop_type, location=location,
                bhk_size=bhk_size, interior_style=interior_style,
                furnished_status=furnished_status, price_bracket=price_bracket,
                special_note=special_note)

    edit_requests = [dict(r) for r in conn.execute(
        'SELECT er.*, d.file_label FROM edit_requests er '
        'LEFT JOIN deliverables d ON d.id = er.deliverable_id '
        'WHERE er.order_id=? ORDER BY er.id',
        (order_id,)).fetchall()]

    uploaded_deliverables = [dict(r) for r in conn.execute(
        'SELECT * FROM deliverables WHERE order_id = ?', (order_id,)).fetchall()]

    conn.close()
    ctx = {
        'order': order, 'intake': intake,
        'attachments': order['attachments_data'],
        'task_label': task_label,
        'moodboard_filename': moodboard_filename,
        'pov_list': pov_list,
        'reel_clips': reel_clips, 'reel_skipped': reel_skipped,
        'reel_narrative': reel_narrative, 'flow_prompts': flow_prompts,
        'rooms': intake.get('rooms', []),
        'edit_requests': edit_requests,
        'qc_annotation_filename': order.get('qc_annotation_filename'),
        'uploaded_deliverables': uploaded_deliverables,
    }
    # Render the ORIGINAL full pilot workflow template verbatim (server-side),
    # so the rich step-by-step UI is identical to the pre-migration app.
    html = render_flask_template('pilot_sku_workflow.html', request, **ctx)
    return HttpResponse(html)


# ── /api/pilot/spatial (app.py 2830-2852) ──────────────────
@require_POST
@role_required('pilot', 'admin')
def api_pilot_spatial(request):
    data = body(request)
    order_id = data.get('order_id')
    pov = data.get('pov', 'A')
    pov_section = data.get('pov_section', '').strip()
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                     (order_id, request.user.id)).fetchone()
    if not o:
        conn.close()
        return err('Not found', status=404)
    existing = conn.execute('SELECT id FROM pilot_steps WHERE order_id=? AND pov=?', (order_id, pov)).fetchone()
    if existing:
        conn.execute("UPDATE pilot_steps SET spatial_facts=?, step_status='pov_section_saved' WHERE order_id=? AND pov=?",
                     (pov_section, order_id, pov))
    else:
        conn.execute("INSERT INTO pilot_steps (order_id,pov,spatial_facts,step_status) VALUES (?,?,?,'pov_section_saved')",
                     (order_id, pov, pov_section))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/save-prompt-a (app.py 2854-2871) ────────────
@require_POST
@role_required('pilot', 'admin')
def api_save_prompt_a(request):
    data = body(request)
    order_id = data.get('order_id')
    output = data.get('output', '').strip()
    wall_inv = data.get('wall_inventory', '').strip()
    moodboard = data.get('moodboard_materials', '').strip()
    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                     (order_id, request.user.id)).fetchone()
    if not o:
        conn.close()
        return err('Not found', status=404)
    conn.execute("UPDATE orders SET prompt_a_output=?, wall_inventory_output=?, moodboard_output=? WHERE id=?",
                 (output, wall_inv, moodboard, order_id))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/save-prompt-b (app.py 2873-2889) ────────────
@require_POST
@role_required('pilot', 'admin')
def api_save_prompt_b(request):
    data = body(request)
    order_id = data.get('order_id')
    pov = data.get('pov', 'A')
    prompt_b = data.get('prompt_b', '').strip()
    conn = get_db()
    existing = conn.execute('SELECT id FROM pilot_steps WHERE order_id=? AND pov=?', (order_id, pov)).fetchone()
    if existing:
        conn.execute("UPDATE pilot_steps SET generated_prompt=?, step_status='prompt_b_ready' WHERE order_id=? AND pov=?",
                     (prompt_b, order_id, pov))
    else:
        conn.execute("INSERT INTO pilot_steps (order_id,pov,generated_prompt,step_status) VALUES (?,?,?,'prompt_b_ready')",
                     (order_id, pov, prompt_b))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/save-flow-prompt (app.py 2891-2907) ─────────
@require_POST
@role_required('pilot', 'admin')
def api_save_flow_prompt(request):
    data = body(request)
    order_id = data.get('order_id')
    pov = data.get('pov', 'A')
    flow_prompt = data.get('flow_prompt', '').strip()
    conn = get_db()
    existing = conn.execute('SELECT id FROM pilot_steps WHERE order_id=? AND pov=?', (order_id, pov)).fetchone()
    if existing:
        conn.execute("UPDATE pilot_steps SET flow_prompt=? WHERE order_id=? AND pov=?",
                     (flow_prompt, order_id, pov))
    else:
        conn.execute("INSERT INTO pilot_steps (order_id,pov,flow_prompt) VALUES (?,?,?)",
                     (order_id, pov, flow_prompt))
    conn.commit(); conn.close()
    return ok({'success': True})


# ── /api/pilot/upload-labeled-plan (app.py 2909-2941) ──────
@require_POST
@role_required('pilot', 'admin')
def api_upload_labeled_plan(request):
    order_id = int(request.POST.get('order_id', 0))
    pov = request.POST.get('pov', 'A')
    f = request.FILES.get('plan')
    if not f or not f.name:
        return err('No file')
    if not is_allowed_upload(f.name):  # M-3
        return err('File type not allowed')

    conn = get_db()
    o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                     (order_id, request.user.id)).fetchone()
    if not o:
        conn.close()
        return err('Not found', status=404)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(settings.DELIVERABLES_FOLDER, f'order_{order_id}')
    os.makedirs(folder, exist_ok=True)
    safe = f'PLAN_{pov}_{ts}_{secure_filename(f.name) or "plan"}'
    path = os.path.join(folder, safe)
    _save_django_file(f, path)
    rel = f'order_{order_id}/{safe}'

    existing = conn.execute('SELECT id FROM pilot_steps WHERE order_id=? AND pov=?', (order_id, pov)).fetchone()
    if existing:
        conn.execute("UPDATE pilot_steps SET labeled_plan_filename=? WHERE order_id=? AND pov=?", (rel, order_id, pov))
    else:
        conn.execute("INSERT INTO pilot_steps (order_id,pov,labeled_plan_filename) VALUES (?,?,?)", (order_id, pov, rel))
    conn.commit(); conn.close()
    return ok({'success': True, 'filename': rel, 'url': f'/deliverables/{rel}'})


# ── /api/pilot/upload-render (app.py 2944-3007) ────────────
@require_POST
@role_required('pilot', 'admin')
def api_upload_render(request):
    current_user = request.user
    order_id = int(request.POST.get('order_id', 0))
    pov = request.POST.get('pov', 'A')
    file_label = request.POST.get('file_label', '').strip()
    f = request.FILES.get('render')
    if not f or not f.name:
        return err('No file')
    if not is_allowed_upload(f.name):  # M-3
        return err('File type not allowed')
    if _file_ext(f.name, default='') in _IMAGE_EXTS and not verify_image_content(f):
        return err('File is not a valid image')

    conn = get_db()
    if current_user.role == 'admin':
        o = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    else:
        o = conn.execute('SELECT * FROM orders WHERE id = ? AND assigned_pilot_id = ?',
                         (order_id, current_user.id)).fetchone()
    if not o:
        conn.close()
        return err('Not found', status=404)

    # ── If order was rejected, wipe all old deliverables first ──
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
        conn.execute("UPDATE pilot_steps SET render_filename=NULL, step_status='pending' WHERE order_id=?",
                     (order_id,))

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(settings.DELIVERABLES_FOLDER, f'order_{order_id}')
    os.makedirs(folder, exist_ok=True)
    ext = _file_ext(f.name, default='png')
    if file_label:
        base = f'{_clean_label(file_label)} POV {pov}'
    else:
        sfn = secure_filename(f.name) or f'deliverable.{ext}'
        base = f'POV{pov}_{ts}_{sfn.rsplit(".",1)[0] if "." in sfn else sfn}'
    safe, path = _unique_named_path(folder, base, ext)
    _save_django_file(f, path)
    rel = f'order_{order_id}/{safe}'
    size = os.path.getsize(path)

    cur = conn.cursor()
    cur.execute('INSERT INTO deliverables (order_id,pilot_id,pov,filename,original_name,file_size,file_label,img_status) VALUES (?,?,?,?,?,?,?,?)',
                (order_id, current_user.id, pov, rel, f.name, size, file_label or None, 'pending'))
    deliverable_id = cur.lastrowid
    conn.execute("UPDATE pilot_steps SET render_filename=?, step_status='render_uploaded' WHERE order_id=? AND pov=?",
                 (rel, order_id, pov))
    conn.commit(); conn.close()
    return ok({'success': True, 'filename': rel, 'deliverable_id': deliverable_id,
               'url': f'/deliverables/{rel}'})


# ── /api/pilot/upload-moodboard (app.py 3010-3055) ─────────
@require_POST
@role_required('pilot', 'admin')
def api_upload_moodboard(request):
    current_user = request.user
    order_id = int(request.POST.get('order_id', 0))
    room_label = request.POST.get('room_label', '').strip()
    f = request.FILES.get('file')
    if not f or not f.name:
        return err('No file')

    ext = os.path.splitext(f.name)[1].lower()
    if not is_allowed_upload(f.name, allowed={'png', 'jpg', 'jpeg', 'webp', 'pdf', 'avif'}):  # M-3
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

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(settings.UPLOAD_FOLDER, f'order_{order_id}_{ts}')
    os.makedirs(folder, exist_ok=True)

    safe, path = _unique_named_path(folder, f'Moodboard_{_clean_label(room_label)}', ext)
    _save_django_file(f, path)
    rel = f'order_{order_id}_{ts}/{safe}'
    size = os.path.getsize(path)

    conn.execute('DELETE FROM order_attachments WHERE order_id = ? AND attachment_type = ? AND file_label = ?',
                 (order_id, 'moodboard', room_label))
    conn.execute(
        'INSERT INTO order_attachments (order_id, attachment_type, filename, original_name, file_size, file_label) VALUES (?, ?, ?, ?, ?, ?)',
        (order_id, 'moodboard', rel, f.name, size, room_label))
    conn.commit(); conn.close()
    return ok({'success': True, 'filename': rel, 'url': f'/uploads/{rel}'})
