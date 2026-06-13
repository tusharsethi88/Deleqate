"""
config.urls — every Flask route from app.py, same paths.
Page GETs serve JSON data for the React frontend; APIs are identical.
"""
from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve as static_serve

from core import database
from api.views import (auth, public, orders, pilot, pilot_extra,
                       client, admin, payments, autopilot)

# ── startup parity with app.py module import ──────────────
database.init_db()
database.sync_pricing_from_db()
database.start_background_workers()

urlpatterns = [
    # ── session bootstrap for React ──
    path('api/session', auth.session_view),

    # ── public ──
    path('', public.index_data),
    path('api/index-data', public.index_data),
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
    path('api/pilot/upload-labeled-plan', pilot.api_upload_labeled_plan),
    path('api/pilot/upload-render', pilot.api_upload_render),
    path('api/pilot/upload-moodboard', pilot.api_upload_moodboard),
    path('api/pilot/qc', pilot_extra.api_pilot_qc),
    path('api/pilot/upload-deliverable', pilot_extra.api_upload_deliverable),
    path('api/pilot/delete-deliverable', pilot_extra.api_delete_deliverable),
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
]
