// Port of templates/admin.html — order queue, pilot management, SKU controls.
// GET /admin/dashboard (JSON) → orders/pilots/stats/task_labels/skus.
// Review tab restores the original Flask QC UX: before/after slider
// (client reference vs pilot render), per-image pass/fail, and a
// MANDATORY rejection note that is sent back to the pilot.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, apiPost, apiPostForm, fileUrl } from '../api.js';

const title = (s) => (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const rupees = (paise) => `₹${Number((paise || 0) / 100).toLocaleString('en-IN')}`;

// Orders that are waiting for admin QC. Both legacy 'submitted' and the
// canonical 'under_review' are treated as the same "needs review" set so
// older rows written before the status unification still appear.
const REVIEW_STATES = ['submitted', 'under_review'];
const isReview = (s) => REVIEW_STATES.includes(s);

const IMG_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'];
const ext = (fn) => (fn && fn.includes('.') ? fn.split('.').pop().toLowerCase() : '');
const isImg = (fn) => IMG_EXTS.includes(ext(fn));

const css = `
.adm-wrap{max-width:1100px;margin:0 auto;padding:1.5rem;}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;}
.stat-card{background:#fff;border:1px solid #DDE3EC;border-radius:12px;padding:1.25rem;display:flex;align-items:center;gap:0.85rem;}
.stat-icon{width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;}
.stat-icon.gold{background:#FFF8E6;}.stat-icon.navy{background:#EEF4FB;}.stat-icon.success{background:#EBF6F0;}
.stat-value{font-size:1.6rem;font-weight:800;color:#1A3A5C;}
.stat-label{font-size:0.78rem;color:#8B9AAB;}
.tab-bar{display:flex;border-bottom:2px solid #DDE3EC;margin-bottom:1.5rem;overflow-x:auto;}
.tab{padding:0.75rem 1.5rem;font-weight:600;cursor:pointer;color:#8B9AAB;border-bottom:3px solid transparent;margin-bottom:-2px;white-space:nowrap;}
.tab.active{color:#1A3A5C;border-color:#1A3A5C;}
.tab .badge{display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:20px;padding:0 6px;margin-left:6px;border-radius:10px;background:#FFF0E6;color:#8B3D00;font-size:0.7rem;font-weight:800;}
.atable{width:100%;border-collapse:collapse;background:#fff;border:1px solid #DDE3EC;border-radius:12px;overflow:hidden;}
.atable th,.atable td{text-align:left;padding:0.7rem 0.9rem;font-size:0.85rem;border-bottom:1px solid #EEF1F6;}
.atable th{background:#F7F9FC;color:#8B9AAB;font-size:0.78rem;text-transform:uppercase;}
.pill{display:inline-flex;border-radius:20px;font-weight:700;font-size:0.72rem;padding:3px 10px;}
.pill-pending{background:#FFF8E6;color:#8B6A00;}.pill-assigned,.pill-in_progress{background:#EEF4FB;color:#1A3A5C;}
.pill-submitted,.pill-under_review{background:#FFF0E6;color:#8B3D00;}.pill-delivered{background:#EBF6F0;color:#1B6B3A;}
.pill-approved{background:#E8F5E9;color:#1B5E20;}.pill-rejected{background:#FDECEA;color:#8B1A1A;}
.abtn{font-size:0.78rem;font-weight:700;border-radius:6px;padding:5px 11px;cursor:pointer;border:1px solid #DDE3EC;background:#fff;color:#1A3A5C;}
.abtn.primary{background:#1A3A5C;color:#fff;border:none;}.abtn.success{background:#16A34A;color:#fff;border:none;}
.abtn.warn{background:#FFF0E6;color:#8B3D00;border:1px solid #F0A87A;}
.abtn.danger{background:#DC2626;color:#fff;border:none;}
.abtn:disabled{opacity:0.5;cursor:not-allowed;}
.aselect,.ainput{padding:5px 9px;border:1.5px solid #DDE3EC;border-radius:7px;font-size:0.82rem;}
/* ── load / error states ── */
.adm-state{max-width:560px;margin:4rem auto;text-align:center;color:#5b6b7d;}
.adm-state h2{color:#1A3A5C;margin-bottom:0.5rem;}
.adm-spinner{width:34px;height:34px;border:3px solid #DDE3EC;border-top-color:#1A3A5C;border-radius:50%;margin:0 auto 1rem;animation:adm-spin 0.8s linear infinite;}
@keyframes adm-spin{to{transform:rotate(360deg);}}
/* ── review panel ── */
.rev-card{background:#fff;border:1px solid #DDE3EC;border-radius:14px;padding:1.25rem 1.4rem;margin-bottom:1.5rem;}
.rev-hd{display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap;margin-bottom:1rem;}
.rev-hd .num{font-weight:800;color:#1A3A5C;font-size:1.05rem;}
.rev-hd .meta{font-size:0.82rem;color:#8B9AAB;}
.rev-deliv{background:#0F1E33;border-radius:12px;overflow:hidden;margin-bottom:1rem;}
.rev-deliv-hd{display:flex;align-items:center;gap:0.6rem;padding:0.6rem 0.9rem;}
.rev-deliv-hd .lbl{background:#C9A84C;color:#fff;border-radius:5px;padding:3px 10px;font-size:0.72rem;font-weight:800;text-transform:uppercase;}
.rev-deliv-hd .cap{font-size:0.74rem;color:rgba(255,255,255,0.6);}
.cp-cmp{position:relative;line-height:0;overflow:hidden;cursor:col-resize;user-select:none;}
.cp-cmp img{width:100%;display:block;pointer-events:none;}
.cp-cmp .after{position:absolute;inset:0;clip-path:inset(0 0 0 var(--split,50%));}
.cp-handle{position:absolute;top:0;bottom:0;width:2px;background:#fff;left:var(--split,50%);}
.cp-handle::after{content:'⇆';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;color:#1A3A5C;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;font-weight:900;box-shadow:0 2px 10px rgba(0,0,0,0.4);}
.cp-caption{display:flex;justify-content:space-between;padding:6px 10px;font-size:0.7rem;font-weight:700;color:rgba(255,255,255,0.8);text-transform:uppercase;letter-spacing:0.04em;}
.rev-reject{margin-top:0.5rem;}
.rev-reject textarea{width:100%;border:1.5px solid #F0A87A;border-radius:8px;padding:8px 10px;font-size:0.85rem;font-family:inherit;margin:6px 0;min-height:64px;}
.rev-actions{display:flex;gap:0.6rem;flex-wrap:wrap;margin-top:0.5rem;}
`;

// Before/after comparison slider (mirrors ClientPreview.jsx).
function Slider({ before, after }) {
  const [split, setSplit] = useState(50);
  let el = null;
  const move = (clientX) => {
    if (!el) return;
    const r = el.getBoundingClientRect();
    setSplit(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  };
  return (
    <div className="cp-cmp" ref={n => { el = n; }} style={{ '--split': `${split}%` }}
      onMouseMove={e => e.buttons === 1 && move(e.clientX)}
      onClick={e => move(e.clientX)}
      onTouchMove={e => move(e.touches[0].clientX)}>
      <img src={before} alt="Client reference" />
      <img className="after" src={after} alt="Pilot render" />
      <div className="cp-handle" />
    </div>
  );
}

// One reviewable order: lazy-loads its deliverables + attachments, shows a
// slider per image, and Approve / Reject (note required) controls.
function ReviewCard({ order, labels, flash, refresh }) {
  const [detail, setDetail] = useState(null);
  const [errored, setErrored] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  const loadDetail = () => {
    setErrored(false);
    apiGet(`/order/${order.id}`)
      .then(r => {
        if (r.ok === false || r.error) { setErrored(true); return; }
        setDetail(r);
      })
      .catch(() => setErrored(true));
  };
  useEffect(() => { loadDetail(); }, [order.id]);

  const deliverables = detail?.deliverables || [];
  const attachments = detail?.attachments || [];
  const imgAtts = attachments.filter(a => isImg(a.filename));

  // Match a deliverable to its client reference (by room/area label, else index).
  const beforeFor = (dv, idx) => {
    if (dv.file_label) {
      const m = imgAtts.find(a => a.file_label === dv.file_label && !(a.attachment_type || '').endsWith('_b'));
      if (m) return m;
    }
    return imgAtts[idx] || null;
  };

  async function approve() {
    setBusy(true);
    const r = await apiPost('/api/admin/mark-delivered', { order_id: order.id });
    if (r.success !== false) { flash(`Order #${order.id} approved & delivered.`); refresh(); }
    else { flash(r.error || 'Error', false); setBusy(false); }
  }
  async function reject() {
    if (!note.trim()) { flash('A rejection note is required for the pilot.', false); return; }
    setBusy(true);
    const r = await apiPost('/api/admin/reject-to-pilot', { order_id: order.id, note: note.trim() });
    if (r.success !== false) { flash(`Order #${order.id} sent back to pilot.`); refresh(); }
    else { flash(r.error || 'Error', false); setBusy(false); }
  }

  return (
    <div className="rev-card">
      <div className="rev-hd">
        <span className="num">#{order.id}</span>
        <span className="pill pill-under_review">{title(order.status)}</span>
        <span className="meta">{labels[order.task || order.task_type] || title(order.task || order.task_type)} · {order.name || order.client_name || 'Client'} · Pilot: {order.pilot_name || '—'}</span>
        <Link to={`/order/${order.id}`} className="abtn" style={{ marginLeft: 'auto' }}>Open order</Link>
      </div>

      {errored && (
        <div style={{ color: '#8B1A1A', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
          Couldn't load this order's files. <button className="abtn" onClick={loadDetail}>Retry</button>
        </div>
      )}
      {!detail && !errored && <div style={{ color: '#8B9AAB', fontSize: '0.85rem' }}>Loading deliverables…</div>}

      {detail && deliverables.length === 0 && (
        <div style={{ color: '#8B9AAB', fontSize: '0.85rem', marginBottom: '0.75rem' }}>No deliverables uploaded for this order.</div>
      )}

      {detail && deliverables.map((dv, idx) => {
        const before = beforeFor(dv, idx);
        const afterUrl = fileUrl(`/api/preview-img/${dv.filename}`);
        const showSlider = isImg(dv.filename) && before && isImg(before.filename);
        return (
          <div className="rev-deliv" key={dv.id}>
            <div className="rev-deliv-hd">
              {dv.file_label && <span className="lbl">{dv.file_label}</span>}
              <span className="cap">{idx + 1} of {deliverables.length} · {dv.original_name || dv.filename}</span>
            </div>
            {showSlider ? (
              <>
                <Slider before={fileUrl(`/uploads/${before.filename}`)} after={afterUrl} />
                <div className="cp-caption"><span>◀ Client reference</span><span>Pilot render ▶</span></div>
              </>
            ) : isImg(dv.filename) ? (
              <img src={afterUrl} alt="Deliverable" style={{ width: '100%', display: 'block' }} />
            ) : (
              <div style={{ padding: '1.3rem', textAlign: 'center' }}>
                <a href={fileUrl(`/deliverables/${dv.filename}`)} style={{ color: '#C9A84C', fontWeight: 700 }} target="_blank" rel="noreferrer">↓ {dv.original_name || dv.filename}</a>
              </div>
            )}
          </div>
        );
      })}

      <div className="rev-reject">
        <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#8B3D00' }}>Rejection note (required to reject)</label>
        <textarea
          placeholder="Tell the pilot exactly what to fix — this is shown to them."
          value={note}
          onChange={e => setNote(e.target.value)}
        />
      </div>
      <div className="rev-actions">
        <button className="abtn success" disabled={busy} onClick={approve}>✓ Approve &amp; Deliver</button>
        <button className="abtn danger" disabled={busy || !note.trim()} onClick={reject}>✗ Reject to Pilot</button>
      </div>
    </div>
  );
}

export default function AdminDashboard({ session }) {
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [loadErr, setLoadErr] = useState(null);
  const [tab, setTab] = useState('orders');
  const [assignSel, setAssignSel] = useState({});
  const [newPilot, setNewPilot] = useState({ name: '', email: '', phone: '', password: '' });
  const [toast, setToast] = useState(null);
  const [now, setNow] = useState(Date.now());

  const load = () => {
    setLoadErr(null);
    return apiGet('/admin/dashboard')
      .then(r => {
        if (r.redirect) { nav(r.redirect); return; }
        if (r.ok === false || r.error) { setLoadErr(r.error || 'Failed to load dashboard.'); return; }
        setD(r);
      })
      .catch(() => setLoadErr('Network error — could not reach the server.'));
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (d && window.lucide) {
      window.lucide.createIcons();
    }
  }, [d, tab]);
  function flash(msg, ok = true) { setToast({ msg, ok }); setTimeout(() => setToast(null), 2500); }
  function elapsed(createdAt) {
    if (!createdAt) return '—';
    // DB timestamps are UTC ("YYYY-MM-DD HH:MM:SS" with no zone). JS parses a
    // space-separated string as LOCAL time, causing a timezone offset error —
    // normalise to ISO UTC so the age is correct.
    let iso = String(createdAt).includes('T') ? String(createdAt) : String(createdAt).replace(' ', 'T');
    if (!/[zZ]|[+-]\d\d:?\d\d$/.test(iso)) iso += 'Z';
    const ms = now - new Date(iso).getTime();
    if (isNaN(ms) || ms < 0) return '—';
    const totalSec = Math.floor(ms / 1000);
    const dd = Math.floor(totalSec / 86400);
    const h = Math.floor((totalSec % 86400) / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    if (dd > 0) return `${dd}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  async function assign(orderId) {
    const pilot_id = assignSel[orderId];
    if (!pilot_id) { flash('Select a pilot first.', false); return; }
    const r = await apiPost('/api/admin/assign', { order_id: orderId, pilot_id: Number(pilot_id) });
    if (r.success !== false) { flash('Order assigned.'); load(); } else flash(r.error || 'Error', false);
  }
  async function qc(orderId, kind) {
    const url = { deliver: '/api/admin/mark-delivered', close: '/api/admin/approve' }[kind];
    const r = await apiPost(url, { order_id: orderId });
    if (r.success !== false) { flash('Done.'); load(); } else flash(r.error || 'Error', false);
  }
  async function createPilot(e) {
    e.preventDefault();
    const r = await apiPostForm('/admin/create-pilot', newPilot);
    if (r.success !== false && !r.error) { flash('Pilot created.'); setNewPilot({ name: '', email: '', phone: '', password: '' }); load(); }
    else flash(r.error || 'Error', false);
  }
  async function togglePilot(pilot_id) {
    const r = await apiPost('/api/admin/pilot/toggle-status', { pilot_id });
    if (r.success !== false) { flash('Status toggled.'); load(); } else flash(r.error || 'Error', false);
  }
  async function toggleSku(task_key) {
    const r = await apiPost('/api/admin/sku/toggle', { task_key });
    if (r.success !== false) { flash('SKU toggled.'); load(); } else flash(r.error || 'Error', false);
  }
  async function editSku(sku) {
    const label = window.prompt('Label', sku.label || '');
    if (label === null) return;
    const price = window.prompt('Price (₹, paise as stored)', sku.price ?? '');
    if (price === null) return;
    const r = await apiPost('/api/admin/sku/edit', { task_key: sku.task_key, label, price, note: sku.note || '' });
    if (r.success !== false) { flash('SKU updated.'); load(); } else flash(r.error || 'Error', false);
  }

  async function toggleVoiceBrief() {
    const r = await apiPost('/api/admin/setting/toggle', { key: 'voice_brief_enabled' });
    if (r.success !== false) { flash(`Voice Brief ${r.value ? 'enabled' : 'disabled'}.`); load(); }
    else flash(r.error || 'Error', false);
  }

  // ── Loading / error states (never render a blank page) ──
  if (loadErr) {
    return (
      <div className="adm-wrap">
        <style>{css}</style>
        <div className="adm-state">
          <h2>Couldn't load the dashboard</h2>
          <p>{loadErr}</p>
          <button className="abtn primary" onClick={load} style={{ marginTop: '0.5rem' }}>Retry</button>
        </div>
      </div>
    );
  }
  if (!d) {
    return (
      <div className="adm-wrap">
        <style>{css}</style>
        <div className="adm-state"><div className="adm-spinner" />Loading dashboard…</div>
      </div>
    );
  }

  const { orders = [], pilots = [], stats = {}, skus = [] } = d;
  const labels = d.task_labels || {};
  const reviewOrders = orders.filter(o => isReview(o.status));
  const voiceEnabled = d.settings ? d.settings.voice_brief_enabled : true;
  const adminName = session?.user?.name || '';

  return (
    <div>
      <style>{css}</style>
      <nav className="navbar">
        <Link to="/" className="navbar-brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><img src="/img/logo.png" alt="Delegate" /> <small style={{ color: '#8B9AAB' }}>Admin</small></Link>
        <div className="navbar-nav">
          {adminName && <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#6b7280' }}>{adminName}</span>}
          <Link to="/logout" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--navy)', border: '2px solid var(--navy)', borderRadius: 20, padding: '0.35rem 1rem' }}>Logout</Link>
        </div>
      </nav>

      <div className="adm-wrap">
        <div className="stat-grid">
          <div className="stat-card"><div className="stat-icon gold" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><i data-lucide="download" style={{ width: 18, height: 18, color: '#d97706' }}></i></div><div><div className="stat-value">{stats.pending || 0}</div><div className="stat-label">Pending Orders</div></div></div>
          <div className="stat-card"><div className="stat-icon navy" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><i data-lucide="zap" style={{ width: 18, height: 18, color: '#1d4ed8' }}></i></div><div><div className="stat-value">{stats.in_progress || 0}</div><div className="stat-label">In Progress</div></div></div>
          <div className="stat-card"><div className="stat-icon success" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><i data-lucide="check-circle" style={{ width: 18, height: 18, color: '#16a34a' }}></i></div><div><div className="stat-value">{stats.delivered || 0}</div><div className="stat-label">Delivered</div></div></div>
          <div className="stat-card"><div className="stat-icon gold" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><i data-lucide="indian-rupee" style={{ width: 18, height: 18, color: '#d97706' }}></i></div><div><div className="stat-value">{rupees(stats.revenue)}</div><div className="stat-label">Revenue (approved)</div></div></div>
        </div>

        <div className="tab-bar">
          {[['orders', 'Orders', 'list-todo'], ['review', 'Review', 'search'], ['pilots', 'Pilots', 'user-check'], ['skus', 'SKUs', 'sliders'], ['settings', 'Settings', 'settings']].map(([k, lbl, iconName]) => (
            <div key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <i data-lucide={iconName} style={{ width: 14, height: 14 }}></i>
              <span>{lbl}</span>
              {k === 'review' && reviewOrders.length > 0 && <span className="badge">{reviewOrders.length}</span>}
            </div>
          ))}
        </div>

        {tab === 'orders' && (
          <table className="atable">
            <thead><tr><th>#</th><th>Task</th><th>Client</th><th>Status</th><th>Age</th><th>Total</th><th>Pilot / Assign</th><th>Actions</th></tr></thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id}>
                  <td><Link to={`/order/${o.id}`}>#{o.id}</Link></td>
                  <td>{labels[o.task || o.task_type] || title(o.task || o.task_type)}</td>
                  <td>{o.name || o.client_name || '—'}</td>
                  <td><span className={`pill pill-${o.status || 'pending'}`}>{title(o.status || 'pending')}</span></td>
                  <td style={{ fontVariantNumeric: 'tabular-nums', color: '#64748b', fontSize: '0.8rem' }}>{elapsed(o.created_at)}</td>
                  <td>{rupees(o.total_price)}</td>
                  <td>
                    {['delivered', 'approved', 'closed'].includes(o.status) ? (
                      <span style={{ color: '#1A3A5C', fontWeight: 600 }}>{o.pilot_name || '—'}</span>
                    ) : (
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        {o.assigned_pilot_id && (
                          <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600, minWidth: 60 }}>{o.pilot_name}</span>
                        )}
                        <select
                          className="aselect"
                          value={assignSel[o.id] !== undefined ? assignSel[o.id] : (o.assigned_pilot_id ? String(o.assigned_pilot_id) : '')}
                          onChange={e => setAssignSel(s => ({ ...s, [o.id]: e.target.value }))}
                        >
                          <option value="">Select pilot</option>
                          {pilots.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>
                        <button className="abtn primary" onClick={() => assign(o.id)}>
                          {o.assigned_pilot_id ? 'Re-assign' : 'Assign'}
                        </button>
                      </div>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {isReview(o.status) && (
                        <button className="abtn primary" onClick={() => setTab('review')}>🔍 Review</button>
                      )}
                      {o.status === 'delivered' && <button className="abtn success" onClick={() => qc(o.id, 'close')}>✓ Close</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'review' && (
          <div>
            {reviewOrders.length === 0 ? (
              <div className="adm-state" style={{ margin: '3rem auto' }}>
                <h2>Nothing to review</h2>
                <p>Orders submitted by pilots will appear here for QC.</p>
              </div>
            ) : (
              reviewOrders.map(o => (
                <ReviewCard key={o.id} order={o} labels={labels} flash={flash} refresh={load} />
              ))
            )}
          </div>
        )}

        {tab === 'pilots' && (
          <div>
            <form onSubmit={createPilot} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'end' }}>
              <input className="ainput" placeholder="Name" required value={newPilot.name} onChange={e => setNewPilot(p => ({ ...p, name: e.target.value }))} />
              <input className="ainput" type="email" placeholder="pilot@email.com" required value={newPilot.email} onChange={e => setNewPilot(p => ({ ...p, email: e.target.value }))} />
              <input className="ainput" placeholder="Phone" required value={newPilot.phone} onChange={e => setNewPilot(p => ({ ...p, phone: e.target.value }))} />
              <input className="ainput" type="password" placeholder="Password" required value={newPilot.password} onChange={e => setNewPilot(p => ({ ...p, password: e.target.value }))} />
              <button className="abtn primary" type="submit">+ Add Pilot</button>
            </form>
            <table className="atable">
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Active Jobs</th><th>Done</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {pilots.map(p => (
                  <tr key={p.id}>
                    <td>{p.name}</td><td>{p.email}</td><td>{p.phone}</td>
                    <td>{p.active_jobs ?? 0}</td><td>{p.done_jobs ?? 0}</td>
                    <td><span className={`pill ${p.account_status === 'inactive' ? 'pill-rejected' : 'pill-approved'}`}>{p.account_status || 'active'}</span></td>
                    <td><button className="abtn" onClick={() => togglePilot(p.id)}>{p.account_status === 'inactive' ? 'Activate' : 'Deactivate'}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'skus' && (
          <table className="atable">
            <thead><tr><th>Key</th><th>Label</th><th>Price</th><th>Active</th><th></th></tr></thead>
            <tbody>
              {skus.map(s => (
                <tr key={s.task_key}>
                  <td>{s.task_key}</td><td>{s.label}</td><td>{s.price}</td>
                  <td><span className={`pill ${s.is_active ? 'pill-approved' : 'pill-rejected'}`}>{s.is_active ? 'Active' : 'Off'}</span></td>
                  <td style={{ display: 'flex', gap: 6 }}>
                    <button className="abtn" onClick={() => toggleSku(s.task_key)}>{s.is_active ? 'Disable' : 'Enable'}</button>
                    <button className="abtn" onClick={() => editSku(s)}>Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'settings' && (
          <div style={{ background: '#fff', border: '1px solid #DDE3EC', borderRadius: 12, padding: '1.25rem 1.5rem', maxWidth: 560 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, color: '#1A3A5C', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <i data-lucide="mic" style={{ width: 18, height: 18 }}></i>
                  <span>Voice Brief on order page</span>
                </div>
                <div style={{ fontSize: '0.82rem', color: '#8B9AAB', marginTop: 2 }}>
                  Let customers record / upload an optional voice brief while placing an order.
                </div>
              </div>
              <span className={`pill ${voiceEnabled ? 'pill-approved' : 'pill-rejected'}`}>{voiceEnabled ? 'On' : 'Off'}</span>
              <button className="abtn primary" onClick={toggleVoiceBrief}>{voiceEnabled ? 'Turn Off' : 'Turn On'}</button>
            </div>
          </div>
        )}
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 3000, padding: '0.8rem 1.3rem', borderRadius: 10, fontWeight: 600, fontSize: '0.9rem', color: '#fff', background: toast.ok ? '#1B6B3A' : '#dc2626' }}>{toast.msg}</div>
      )}
    </div>
  );
}
