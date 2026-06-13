// Port of templates/client_dashboard.html — order cards with live status
// timeline, 30s auto-refresh, edit-credit badge.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet } from '../api.js';

const css = `
.page-wrap{max-width:900px;margin:0 auto;padding:2rem 1.5rem 4rem;}
.page-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:2rem;gap:1rem;flex-wrap:wrap;}
.page-title{font-size:1.625rem;font-weight:800;color:var(--navy);margin-bottom:.2rem;}
.page-sub{color:var(--gray-500);font-size:.875rem;}
.order-card{background:#FFFFFF;border:1px solid #DDE3EC;border-radius:14px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 6px rgba(26,58,92,0.06);transition:box-shadow .2s;cursor:pointer;}
.order-card:hover{box-shadow:0 4px 16px rgba(26,58,92,0.1);border-color:#C2D4E8;}
.order-card-top{display:flex;align-items:flex-start;gap:1rem;margin-bottom:1.25rem;}
.order-num{font-size:.75rem;font-weight:700;color:#8B9AAB;letter-spacing:.05em;}
.order-task{font-size:1rem;font-weight:700;color:var(--navy);margin-bottom:.15rem;}
.order-summary{font-size:.8125rem;color:var(--gray-500);}
.order-meta{margin-left:auto;text-align:right;flex-shrink:0;}
.order-amount{font-size:1.125rem;font-weight:800;color:var(--navy);}
.order-date{font-size:.75rem;color:#8B9AAB;margin-top:.1rem;}
.status-track{display:grid;grid-template-columns:repeat(5,1fr);align-items:start;margin-bottom:1.25rem;gap:0;}
.st-step{display:flex;flex-direction:column;align-items:center;position:relative;}
.st-step + .st-step::before{content:'';position:absolute;top:10px;right:50%;left:-50%;height:2px;background:#DDE3EC;z-index:0;}
.st-step.done + .st-step::before,.st-step.active + .st-step::before{background:#1B6B3A;}
.st-dot{width:20px;height:20px;border-radius:50%;border:2px solid #DDE3EC;background:#FFFFFF;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:#B0BAC9;position:relative;z-index:1;flex-shrink:0;}
.st-dot.done{background:#1B6B3A;border-color:#1B6B3A;color:#fff;}
.st-dot.active{background:#1A3A5C;border-color:#1A3A5C;color:#fff;box-shadow:0 0 0 4px rgba(26,58,92,0.12);}
.st-label{font-size:.67rem;font-weight:600;color:#B0BAC9;margin-top:5px;text-align:center;line-height:1.3;white-space:nowrap;}
.st-label.done{color:#1B6B3A;}
.st-label.active{color:var(--navy);font-weight:700;}
.status-pill{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;font-size:.75rem;font-weight:700;letter-spacing:.03em;}
.sp-pending{background:#FFF8E6;color:#8B6A00;border:1px solid #E8C84A;}
.sp-assigned{background:#EEF4FB;color:#1A3A5C;border:1px solid #C2D8EC;}
.sp-in_progress{background:#EEF4FB;color:#1A3A5C;border:1px solid #9DC3E6;}
.sp-under_review{background:#FFF0E6;color:#8B3D00;border:1px solid #F0A87A;}
.sp-delivered{background:#EBF6F0;color:#1B6B3A;border:1px solid #8FD4AE;}
.sp-approved{background:#E8F5E9;color:#1B5E20;border:1px solid #81C784;}
.sp-submitted{background:#FFF0E6;color:#8B3D00;border:1px solid #F0A87A;}
.sp-rejected{background:#FDECEA;color:#8B1A1A;border:1px solid #F0A0A0;}
.order-actions{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;}
.order-card.card-delivered{border:2px solid #F59E0B;box-shadow:0 0 0 4px rgba(245,158,11,0.12),0 4px 20px rgba(245,158,11,0.15);animation:pulse-gold 2.2s ease-in-out infinite;}
.order-card.card-approved{border:2px solid #1B6B3A;box-shadow:0 0 0 3px rgba(27,107,58,0.08);}
@keyframes pulse-gold{0%,100%{box-shadow:0 0 0 4px rgba(245,158,11,0.12),0 4px 20px rgba(245,158,11,0.12);}50%{box-shadow:0 0 0 8px rgba(245,158,11,0.22),0 4px 28px rgba(245,158,11,0.22);}}
.btn-review{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,#F59E0B,#D97706);color:#fff;border:none;border-radius:9px;padding:10px 22px;font-size:.9rem;font-weight:800;cursor:pointer;text-decoration:none;letter-spacing:.01em;box-shadow:0 2px 8px rgba(245,158,11,0.35);transition:all .15s;}
.btn-review:hover{background:linear-gradient(135deg,#D97706,#B45309);color:#fff;box-shadow:0 4px 14px rgba(245,158,11,0.45);}
.empty-state{text-align:center;padding:5rem 2rem;background:#FFFFFF;border-radius:14px;border:1px solid #DDE3EC;}
.refresh-bar{display:flex;align-items:center;gap:.5rem;font-size:.75rem;color:#8B9AAB;margin-bottom:1rem;}
.refresh-dot{width:7px;height:7px;border-radius:50%;background:#8B9AAB;animation:cd-pulse 2s infinite;}
@keyframes cd-pulse{0%,100%{opacity:.4}50%{opacity:1}}
@media(max-width:768px){
  .page-wrap{padding:1rem 1rem 3rem !important;}
  .page-header{flex-direction:column;align-items:flex-start;gap:.5rem;}
  .order-card-top{flex-wrap:wrap;}
  .order-meta{margin-left:0 !important;text-align:left;}
}
@media(max-width:600px){
  .status-track-outer{overflow-x:auto;-webkit-overflow-scrolling:touch;}
  .status-track{min-width:440px;}
  .order-actions{flex-direction:column;align-items:stretch;}
  .order-actions a,.order-actions button{width:100%;justify-content:center;text-align:center;}
  .st-label{font-size:.6rem;}
}
@media(max-width:480px){
  .page-title{font-size:1.375rem !important;}
  .order-card{padding:1rem;}
  .order-task{font-size:.9375rem !important;}
  .order-amount{font-size:1rem !important;}
}
`;

const STAGES = [['pending', 'With Admin'], ['assigned', 'Assigned'], ['in_progress', 'In Progress'],
  ['under_review', 'Under Review'], ['delivered', 'Delivered']];
const STAGE_KEYS = ['pending', 'assigned', 'in_progress', 'under_review', 'delivered'];

function summary(o) {
  const i = o.intake || {};
  switch (o.task) {
    case 'virtual_staging': return `${i.style || 'Virtual staging'} · 4 rooms`;
    case 'property_reel': return `${i.property_name || ''}${i.location ? ', ' + i.location : ''}`;
    case 'property_social_card': return `${i.property_name || '3BHK'} · ${i.location || '—'}`;
    case 'bg_cleanup': return `${o.render_count} images · ${i.background_type || 'white'} background`;
    case 'product_listing': return `${i.product_name || '—'} · ${i.platform || 'Amazon'}`;
    case 'product_mockup': return `${i.product_name || '—'} · ${i.scene_setting || ''}`;
    case 'instagram_carousel': return `${i.carousel_idea || '—'} · ${i.num_slides || '5'} slides`;
    case 'brand_demo_video': return `${i.brand_name || '—'} · ${i.duration || '30s'}`;
    case 'announcement_pack': return `${i.brand_name || '—'} · ${i.announcement_type || 'Announcement'}`;
    case 'brand_starter_kit': return `${i.business_name || '—'} · ${i.industry || ''}`;
    case 'menu_design': return `${i.business_name || '—'} · ${i.menu_format || ''}`;
    case 'podcast_reel': return i.show_name || i.episode_topic || '—';
    default: return `Order #${o.id}`;
  }
}

function pillLabel(s) {
  return { pending: '⏳ With Admin', assigned: '👤 Assigned', in_progress: '🔄 In Progress',
    under_review: '🔍 Under Review', delivered: '✅ Delivered', approved: '✅ Delivered' }[s]
    || s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function ClientDashboard({ session }) {
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [refreshLabel, setRefreshLabel] = useState('Auto-updating every 30s');

  const load = () => apiGet('/client/orders').then(r => {
    if (r.status === 401 || r.status === 403) nav(r.login_url || '/login');
    else setD(r);
  });

  useEffect(() => { load(); }, []);

  // 30s status poll — reload list if any status changed
  useEffect(() => {
    if (!d) return;
    const statuses = Object.fromEntries((d.orders || []).map(o => [o.id, o.status || 'pending']));
    const t = setInterval(async () => {
      try {
        const r = await apiGet('/api/client/orders-status');
        const changed = (r.orders || []).some(o => statuses[o.id] && statuses[o.id] !== o.status);
        if (changed) { setRefreshLabel('Status updated — refreshing…'); setTimeout(load, 1200); }
        else setRefreshLabel(`Auto-updating · last checked ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`);
      } catch { /* silent */ }
    }, 30000);
    return () => clearInterval(t);
  }, [d]);

  if (!d) return null;
  const orders = d.orders || [];
  const credits = d.edit_credits || 0;
  const userName = session?.user?.name || '';

  return (
    <div>
      <style>{css}</style>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">Dele<span>qate</span></Link>
        <div className="navbar-nav">
          <Link to="/order" className="btn-nav">+ New Order</Link>
          <Link to="/logout" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--navy)', border: '2px solid var(--navy)', borderRadius: 20, padding: '0.35rem 1rem' }}>Logout</Link>
        </div>
      </nav>

      <div className="page-wrap">
        <div className="page-header">
          <div>
            <div className="page-title">My Orders</div>
            <div className="page-sub">Hi {userName} — your Deleqate deliveries, live.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span title="Edit credits let you request revisions on delivered orders"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#FFF8E6', border: '1.5px solid #E8C84A', color: '#7A5A00', borderRadius: 20, padding: '6px 14px', fontSize: '0.8125rem', fontWeight: 700 }}>
              <span aria-hidden="true">✦</span> {credits} edit credit{credits !== 1 ? 's' : ''}
            </span>
            <Link to="/order" className="btn btn-gold">+ Place New Order</Link>
          </div>
        </div>

        {orders.length ? (
          <>
            <div className="refresh-bar">
              <span className="refresh-dot" />
              <span>{refreshLabel}</span>
            </div>

            {orders.map(o => {
              const cur = o.status || 'pending';
              const allDone = cur === 'approved';
              const curIdx = allDone ? 4 : (STAGE_KEYS.includes(cur) ? STAGE_KEYS.indexOf(cur) : 0);
              const target = (cur === 'delivered' || cur === 'approved') ? `/order/${o.id}/preview` : `/order/${o.id}`;
              return (
                <div key={o.id}
                  className={`order-card ${cur === 'delivered' ? 'card-delivered' : cur === 'approved' ? 'card-approved' : ''}`}
                  onClick={() => nav(target)} title="Click to view order">
                  <div className="order-card-top">
                    <div style={{ flex: 1 }}>
                      <div className="order-num">ORDER #{o.id}</div>
                      <div className="order-task">{o.task_label}</div>
                      <div className="order-summary">{summary(o)}</div>
                    </div>
                    <div className="order-meta">
                      <div className="order-amount">₹{Math.floor((o.total_price || 0) / 100).toLocaleString('en-IN')}</div>
                      <div className="order-date">{o.created_at ? o.created_at.slice(0, 10) : '—'}</div>
                    </div>
                  </div>

                  <div className="status-track-outer">
                    <div className="status-track">
                      {STAGES.map(([sk, slabel], si) => {
                        const cls = (allDone || si < curIdx) ? 'done' : si === curIdx ? 'active' : '';
                        return (
                          <div key={sk} className={`st-step ${cls}`}>
                            <div className={`st-dot ${cls}`}>{cls === 'done' ? '✓' : cls === 'active' ? '●' : si + 1}</div>
                            <div className={`st-label ${cls}`}>{slabel}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="order-actions">
                    <span className={`status-pill sp-${cur}`}>{pillLabel(cur)}</span>
                    {(cur === 'delivered' || cur === 'approved') && (
                      <Link to={`/order/${o.id}/preview`} className="btn-review" onClick={e => e.stopPropagation()}>
                        {cur === 'approved' ? '⬇ View & Download' : '👁 Review & Approve'}
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </>
        ) : (
          <div className="empty-state">
            <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>📋</div>
            <h3 style={{ color: 'var(--navy)', marginBottom: '0.5rem' }}>No orders yet</h3>
            <p style={{ margin: '0 0 2rem', color: 'var(--gray-500)' }}>Place your first order — AI results delivered in under 4 hours, from ₹79.</p>
            <Link to="/order" className="btn btn-gold btn-lg">Place First Order →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
