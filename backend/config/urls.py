"""
config.urls — every Flask route from app.py, same paths.
Page GETs serve JSON data for the React frontend; APIs are identical.
"""
from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve as static_serve
from django.http import HttpResponse
from pathlib import Path

from core import database
from api.views import (auth, public, orders, pilot, pilot_extra,
                       client, admin, payments, autopilot)

# ── React SPA shell ──────────────────────────────────────────────────────────
_SPA_HTML = (Path(settings.PROJECT_ROOT) / 'frontend' / 'dist' / 'index.html').read_text(encoding='utf-8')

def spa_view(request, *args, **kwargs):
    return HttpResponse(_SPA_HTML, content_type='text/html')

def logo_showroom_view(request):
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Deleqate - Logo Design Showroom</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Syne:wght@800&display=swap" rel="stylesheet">
    <style>
        body { background-color: #0B0F14; color: #F5F8FA; font-family: 'Inter', sans-serif; padding: 40px; margin: 0; text-align: center; }
        h1 { font-family: 'Syne', sans-serif; font-size: 2.5rem; margin-bottom: 15px; color: #F5F8FA; }
        .subtitle { color: #9DB4C6; font-size: 1.1rem; margin-bottom: 40px; }
        .sheet { margin: 50px auto; max-width: 1000px; background: #1E2A39; padding: 25px; border-radius: 12px; border: 1px solid #5C7386; text-align: left; }
        h2 { font-family: 'Syne', sans-serif; font-size: 1.5rem; margin-top: 0; margin-bottom: 20px; color: #F5F8FA; border-bottom: 1px solid #5C7386; padding-bottom: 10px; }
        img { width: 100%; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); display: block; }
        p { color: #D6DEE6; line-height: 1.6; font-size: 0.95rem; }
    </style>
</head>
<body>
    <h1>Deleqate Logo Showroom</h1>
    <div class="subtitle">Arctic Prestige Palette: Ice White (#F5F8FA) · Glacier Blue (#9DB4C6) · Arctic Navy (#1E2A39) · Obsidian (#0B0F14)</div>
    
    <div class="sheet">
        <h2>Sheet 11: Premium Abstract Logo Symbols <span class="badge-new" style="background: #2D7A4F; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; margin-left: 10px; font-weight: bold;">NEWEST (RECOMMENDED)</span></h2>
        <img src="/static/img/deleqate_abstract_symbol_logos_1781814065299.png" alt="Sheet 11">
        <p>10 new premium abstract tech symbols (no letters/monograms). Highlights include stylized microchip silicon wafers with neural node cores, cybernetic machine vision lenses, and geometric loops.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 10: Rotational Ambigram Wordmarks & Monograms <span class="badge" style="background: #ba1a1a; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; margin-left: 10px; font-weight: bold;">RETIRED</span></h2>
        <img src="/static/img/deleqate_ambigram_logos_1781813871077.png" alt="Sheet 10">
        <p>10 typographic concepts focusing on rotational symmetry, reading the same upside down. Retired as full-word tech ambigrams are too forced.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 9: Singular "D" & Wordmark Concepts</h2>
        <img src="/static/img/deleqate_single_d_logos_1781813753700.png" alt="Sheet 9">
        <p>10 new premium designs focusing exclusively on a single letter <strong>D</strong> monogram (integrating the microprocessor chip and vetting checkmark inside the letter form itself) and typographic wordmarks, completely removing the redundant D-d double letter connection.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 8: Refined Chip-Link & Cybernetic Eye Concepts <span class="badge" style="background: #ba1a1a; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; margin-left: 10px; font-weight: bold;">RETIRED (DOUBLE LETTER)</span></h2>
        <img src="/static/img/deleqate_refined_chip_eye_logos_1781813675379.png" alt="Sheet 8">
        <p>10 refined logo ideas expanding on your two favorite styles: the D-d/D-✓ Chip Link (with connecting waves and a microchip) and the Cybernetic Eye Shield (with diamond outer outlines and network nodes).</p>
    </div>

    <div class="sheet">
        <h2>Sheet 7: Chevron Streams & Origami Folds <span class="badge" style="background: #ba1a1a; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; margin-left: 10px; font-weight: bold;">RETIRED</span></h2>
        <img src="/static/img/deleqate_chevron_origami_logos_1781813573775.png" alt="Sheet 7">
        <p>10 new premium designs focusing specifically on speed chevrons (stacked speed vectors converting to checkmarks) and geometric origami ribbon folds forming 'd' and checkmarks.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 6: Refined D-Check & Vetted Wordmarks</h2>
        <img src="/static/img/deleqate_vetted_refined_logos_1781813409343.png" alt="Sheet 6">
        <p>10 refined logo ideas expanding on the concept of 'D + checkmark (✓)' and custom typographic treatments of the word 'Deleqate' where the 'q' is stylized as a quality vetting element.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 5: Vetted Delivery & Custom Wordmark Concepts</h2>
        <img src="/static/img/deleqate_vetted_logo_concepts_1781812946655.png" alt="Sheet 5">
        <p>Our initial vetted direction combining the letter <strong>D</strong> (Delivery) with a premium <strong>Checkmark (✓)</strong> representing vetted quality, completely avoiding the negative "DQ" association.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 4: Artistic D-Q Monograms <span class="badge" style="background: #ba1a1a; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; margin-left: 10px; font-weight: bold;">RETIRED (DQ / DISQUALIFIED ASSOCIATION)</span></h2>
        <img src="/static/img/deleqate_dq_logo_concepts_1781812844265.png" alt="Sheet 4">
        <p>Concepts connecting letters D and Q. Kept here for archive purposes only to avoid negative sports and compliance connotations.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 3: Premium Minimalist & Abstract Concepts (Stripe/Linear-Inspired)</h2>
        <img src="/static/img/deleqate_minimalist_tech_logos_1781812508669.png" alt="Sheet 3">
        <p>Ultra-minimalist, conceptual abstract shapes focusing on origami letter folds, negative space checkmarks, linked speed vectors, and modern branding ribbons.</p>
    </div>

    <div class="sheet">
        <h2>Sheet 2: Refined Chip & Eye Concepts (Selected Shortlist Styles)</h2>
        <img src="/static/img/deleqate_refined_tech_logos_1781812388632.png" alt="Sheet 2">
        <p>Refined concepts focusing on cybernetic eye shield constructs, diamond outline protection vectors, and linked letters connecting AI input to human output validation.</p>
    </div>
    
    <div class="sheet">
        <h2>Sheet 1: Computational & Neural Concepts (Nvidia-Inspired)</h2>
        <img src="/static/img/deleqate_nvidia_style_logos_1781812029069.png" alt="Sheet 1">
        <p>A computational aesthetic focusing on neural connectivity, microprocessors, and processing networks. Features variations of the "D-d Chip Link" and high-performance computing badges.</p>
    </div>
</body>
</html>"""
    return HttpResponse(html_content, content_type='text/html')

# ── startup parity with app.py module import ──────────────
database.init_db()
database.sync_pricing_from_db()
database.start_background_workers()

urlpatterns = [
    # ── session bootstrap for React ──
    path('api/session', auth.session_view),

    # ── public ──
    path('', spa_view),                         # SPA shell for homepage
    re_path(r'^logo-showroom/?$', logo_showroom_view),
    path('api/index-data', public.index_data),  # JSON data for homepage
    path('robots.txt', public.robots_txt),
    path('sitemap.xml', public.sitemap_xml),
    path('about', public.policy_data, {'page': 'about'}),
    path('terms', public.policy_data, {'page': 'terms'}),
    path('privacy', public.policy_data, {'page': 'privacy'}),
    path('refund-policy', public.policy_data, {'page': 'refund'}),
    path('shipping-policy', public.policy_data, {'page': 'shipping'}),
    path('.well-known/security.txt', public.security_txt),
    re_path(r'^api/hero-img/(?P<which>\w+)/(?P<filename>.+)$', public.hero_img),
    path('api/pricing', public.api_pricing),
    path('api/companies', public.api_companies),

    # ── auth ──
    path('login', auth.login),
    path('logout', auth.logout),
    path('dq-control-7x9k', auth.admin_secret_login),
    path('login/phone', auth.login_phone),
    path('verify-otp', auth.verify_otp),
    path('signup', auth.signup),
    path('verify-signup-otp', auth.verify_signup_otp),
    path('forgot-password', auth.forgot_password),
    path('reset-password-verify', auth.reset_password_verify),
    path('reset-password-new', auth.reset_password_new),

    # ── orders ──
    path('order', orders.order_wizard_data),
    path('submit-order', orders.submit_order),
    path('order/success', client.order_success),
    path('order/<int:order_id>', client.order_detail),
    path('order/<int:order_id>/edit', client.client_edit_order),
    path('order/<int:order_id>/preview', client.client_order_preview),
    path('order/<int:order_id>/client-choice', client.client_choice),

    # ── client ──
    path('client/orders', client.client_orders),
    path('api/client/orders-status', client.api_client_orders_status),
    path('api/client/order-status', client.api_client_order_status),

    # ── file serving ──
    re_path(r'^uploads/(?P<filename>.+)$', client.uploaded_file),
    re_path(r'^api/preview-img/(?P<filename>.+)$', client.preview_img_file),
    re_path(r'^deliverables/(?P<filename>.+)$', client.deliverable_file),
    # static assets for server-rendered legacy templates (pilot workflow CSS/JS/img)
    re_path(r'^static/(?P<path>.+)$', static_serve,
            {'document_root': str(settings.PROJECT_ROOT / 'static')}),

    # ── admin ──
    path('admin', admin.admin_home),
    path('admin/dashboard', admin.admin_home),
    path('admin/assign/<int:order_id>', admin.admin_assign),
    path('admin/qc/<int:order_id>', admin.admin_qc),
    path('admin/create-pilot', admin.admin_create_pilot),
    path('api/admin/pilot/toggle-status', admin.admin_toggle_pilot_status),
    path('api/admin/hero-video', admin.api_admin_hero_video),
    path('api/admin/hero-video/delete', admin.api_admin_hero_video_delete),
    path('api/admin/change-password', admin.admin_change_password),
    path('api/admin/assign', admin.api_admin_assign),
    path('api/admin/review-image', admin.api_admin_review_image),
    path('api/admin/approve', admin.api_admin_approve),
    path('api/admin/mark-delivered', admin.api_admin_mark_delivered),
    path('api/admin/reject-to-pilot', admin.api_admin_reject_to_pilot),
    path('api/admin/save-annotation', admin.api_admin_save_annotation),
    path('api/admin/confirm-payment', admin.api_admin_confirm_payment),
    path('api/admin/sku/toggle', admin.api_admin_sku_toggle),
    path('api/admin/sku/edit', admin.api_admin_sku_edit),
    path('api/admin/setting/toggle', admin.api_admin_setting_toggle),

    # ── pilot ──
    path('pilot/', pilot.pilot_dashboard_v2),
    path('pilot/dashboard', pilot.pilot_dashboard_v2),
    path('pilot/dashboard-legacy', pilot.pilot_dashboard_legacy),
    path('pilot/execute/<int:order_id>', pilot.pilot_job),
    path('pilot/job/<int:order_id>', pilot.pilot_job),
    path('pilot/submit/<int:order_id>', pilot_extra.pilot_submit),
    path('api/pilot/spatial', pilot.api_pilot_spatial),
    path('api/pilot/save-prompt-a', pilot.api_save_prompt_a),
    path('api/pilot/save-prompt-b', pilot.api_save_prompt_b),
    path('api/pilot/save-flow-prompt', pilot.api_save_flow_prompt),
    path('api/pilot/save-brand-dna', pilot.api_save_brand_dna),
    path('api/pilot/save-carousel-plan', pilot.api_save_carousel_plan),
    path('api/pilot/upload-labeled-plan', pilot.api_upload_labeled_plan),
    path('api/pilot/upload-render', pilot.api_upload_render),
    path('api/pilot/upload-moodboard', pilot.api_upload_moodboard),
    path('api/pilot/qc', pilot_extra.api_pilot_qc),
    path('api/pilot/upload-deliverable', pilot_extra.api_upload_deliverable),
    path('api/pilot/delete-deliverable', pilot_extra.api_delete_deliverable),
    path('api/pilot/unassign', pilot_extra.api_pilot_unassign),
    path('api/pilot/complete', pilot_extra.api_pilot_complete),
    path('api/pilot/restart-job', pilot_extra.api_pilot_restart_job),

    # ── payments (PayU) ──
    path('payment/initiate', payments.payment_initiate),
    path('payment/success', payments.payment_success),
    path('payment/failure', payments.payment_failure),

    # ── autopilot (token-gated) ──
    path('api/autopilot/pending_orders', autopilot.api_autopilot_pending_orders),
    path('api/autopilot/order/<int:order_id>', autopilot.api_autopilot_order_detail),
    re_path(r'^api/autopilot/download/(?P<order_id>\d+)/(?P<filename>.+)$', autopilot.api_autopilot_download),
    path('api/autopilot/deliver/<int:order_id>', autopilot.api_autopilot_deliver),
    path('api/autopilot/qc_pass/<int:order_id>', autopilot.api_autopilot_qc_pass),
    path('api/autopilot/qc_fail/<int:order_id>', autopilot.api_autopilot_qc_fail),
    path('api/autopilot/heartbeat', autopilot.api_autopilot_heartbeat),
    path('api/autopilot/status', admin.api_autopilot_status),
    path('api/autopilot/workflow/<int:order_id>', autopilot.api_autopilot_workflow),
    path('api/autopilot/spatial/<int:order_id>', autopilot.api_autopilot_spatial),
    path('api/ping_autopilot_test_xyz', autopilot.api_ping_test),

    # ── React SPA static assets ──────────────────────────────────────────────
    re_path(r'^assets/(?P<path>.+)$', static_serve,
            {'document_root': str(Path(settings.PROJECT_ROOT) / 'frontend' / 'dist' / 'assets')}),
    re_path(r'^css/(?P<path>.+)$', static_serve,
            {'document_root': str(Path(settings.PROJECT_ROOT) / 'frontend' / 'dist' / 'css')}),
    re_path(r'^img/(?P<path>.+)$', static_serve,
            {'document_root': str(Path(settings.PROJECT_ROOT) / 'frontend' / 'dist' / 'img')}),

    # ── SPA catch-all: serve index.html for all unmatched frontend routes ────
    re_path(r'^.*$', spa_view),
]
# reload-touch: 2026-06-21T03:53:00
