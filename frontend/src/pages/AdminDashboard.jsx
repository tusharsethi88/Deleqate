// Port of templates/admin.html — order queue, pilot management, SKU controls.
// GET /admin/dashboard (JSON) → orders/pilots/stats/task_labels/skus.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, apiPost, apiPostForm } from '../api.js';

const title = (s) => (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const rupees = (paise) => `₹${Number((paise || 0) / 100).toLocaleString('en-IN')}`;

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
.aselect,.ainput{padding:5px 9px;border:1.5px solid #DDE3EC;border-radius:7px;font-size:0.82rem;}
`;

export default function AdminDashboard({ session }) {
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('orders');
  const [assignSel, setAssignSel] = useState({});
  const [newPilot, setNewPilot] = useState({ name: '', email: '', phone: '', password: '' });
  const [toast, setToast] = useState(null);

  const load = () => apiGet('/admin/dashboard').then(r => {
    if (r.redirect) { nav(r.redirect); return; }
    setD(r);
  });
  useEffect(() => { load(); }, []);
  function flash(msg, ok = true) { setToast({ msg, ok }); setTimeout(() => setToast(null), 2500); }

  async function assign(orderId) {
    const pilot_id = assignSel[orderId];
    if (!pilot_id) { flash('Select a pilot first.', false); return; }
    const r = await apiPost('/api/admin/assign', { order_id: orderId, pilot_id: Number(pilot_id) });
    if (r.success !== false) { flash('Order assigned.'); load(); } else flash(r.error || 'Error', false);
  }
  async function qc(orderId, kind) {
    const url = { deliver: '/api/admin/mark-delivered', reject: '/api/admin/reject-to-pilot', close: '/api/admin/approve' }[kind];
    const r = await apiPost(url, { order_id: orderId, note: '' });
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

  if (!d) return null;
  const { orders = [], pilots = [], stats = {}, skus = [] } = d;
  const labels = d.task_labels || {};
  const voiceEnabled = d.settings ? d.settings.voice_brief_enabled : true;

  return (
    <div>
      <style>{css}</style>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">Dele<span>qate</span> <small style={{ color: '#8B9AAB' }}>Admin</small></Link>
        <div className="navbar-nav">
          <Link to="/logout" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--navy)', border: '2px solid var(--navy)', borderRadius: 20, padding: '0.35rem 1rem' }}>Logout</Link>
        </div>
      </nav>

      <div className="adm-wrap">
        <div className="stat-grid">
          <div className="stat-card"><div className="stat-icon gold">📥</div><div><div className="stat-value">{stats.pending || 0}</div><div className="stat-label">Pending Orders</div></div></div>
          <div className="stat-card"><div className="stat-icon navy">⚡</div><div><div className="stat-value">{stats.in_progress || 0}</div><div className="stat-label">In Progress</div></div></div>
          <div className="stat-card"><div className="stat-icon success">✅</div><div><div className="stat-value">{stats.delivered || 0}</div><div className="stat-label">Delivered</div></div></div>
          <div className="stat-card"><div className="stat-icon gold">💰</div><div><div className="stat-value">{rupees(stats.revenue)}</div><div className="stat-label">Revenue (approved)</div></div></div>
        </div>

        <div className="tab-bar">
          {[['orders', '📋 Orders'], ['pilots', '🚀 Pilots'], ['skus', '🎛️ SKUs'], ['settings', '⚙️ Settings']].map(([k, lbl]) => (
            <div key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{lbl}</div>
          ))}
        </div>

        {tab === 'orders' && (
          <table className="atable">
            <thead><tr><th>#</th><th>Task</th><th>Client</th><th>Status</th><th>Total</th><th>Pilot / Assign</th><th>Actions</th></tr></thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id}>
                  <td><Link to={`/order/${o.id}`}>#{o.id}</Link></td>
                  <td>{labels[o.task || o.task_type] || title(o.task || o.task_type)}</td>
                  <td>{o.name || o.client_name || '—'}</td>
                  <td><span className={`pill pill-${o.status || 'pending'}`}>{title(o.status || 'pending')}</span></td>
                  <td>{rupees(o.total_price)}</td>
                  <td>
                    {(!o.assigned_pilot_id && (o.status === 'pending' || !o.status)) ? (
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <select className="aselect" value={assignSel[o.id] || ''} onChange={e => setAssignSel(s => ({ ...s, [o.id]: e.target.value }))}>
                          <option value="">Select pilot</option>
                          {pilots.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>
                        <button className="abtn primary" onClick={() => assign(o.id)}>Assign</button>
                      </div>
                    ) : <span style={{ color: '#1A3A5C', fontWeight: 600 }}>{o.pilot_name || '—'}</span>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {['assigned', 'in_progress', 'under_review', 'delivered', 'submitted', 'rejected'].includes(o.status) && (
                        <Link to={`/pilot/execute/${o.id}`} className="abtn">Pilot View</Link>
                      )}
                      {['submitted', 'under_review'].includes(o.status) && (
                        <>
                          <button className="abtn success" onClick={() => qc(o.id, 'deliver')}>✓ Pass QC</button>
                          <button className="abtn warn" onClick={() => qc(o.id, 'reject')}>✗ Reject</button>
                        </>
                      )}
                      {o.status === 'delivered' && <button className="abtn success" onClick={() => qc(o.id, 'close')}>✓ Close</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
                <div style={{ fontWeight: 700, color: '#1A3A5C' }}>🎙️ Voice Brief on order page</div>
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
