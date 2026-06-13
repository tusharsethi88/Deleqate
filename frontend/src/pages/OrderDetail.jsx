// Port of templates/order_detail.html — admin/pilot order + QC view.
// Consumes GET /order/<id> (JSON) and posts QC actions to /api/admin/*.
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiGet, apiPost, fileUrl } from '../api.js';

const IMG_EXTS = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'avif', 'heic', 'heif'];
const ext = (fn) => (fn && fn.includes('.') ? fn.split('.').pop().toLowerCase() : '');
const isImg = (fn) => IMG_EXTS.includes(ext(fn));
const title = (s) => (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const rupees = (paise) => `₹${Number((paise || 0) / 100).toLocaleString('en-IN')}`;

const css = `
.od-top{display:flex;align-items:center;gap:1rem;background:#fff;border-bottom:1px solid #DDE3EC;padding:0.9rem 1.5rem;}
.od-logo{font-weight:800;color:#1A3A5C;font-size:1.15rem;text-decoration:none;}
.od-logo span{color:var(--gold);}
.od-back{font-size:0.82rem;color:#1A3A5C;font-weight:600;text-decoration:none;margin-left:auto;}
.od-wrap{max-width:1000px;margin:0 auto;padding:1.5rem;}
.od-card{background:#fff;border:1px solid #DDE3EC;border-radius:14px;padding:1.5rem;margin-bottom:1.25rem;}
.od-card h2{font-size:0.95rem;color:#1A3A5C;margin:0 0 1rem;font-weight:800;}
.od-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #EEF1F6;font-size:0.85rem;}
.od-row-lbl{color:#8B9AAB;}
.od-row-val{color:#1A3A5C;font-weight:600;text-align:right;}
.pill{display:inline-flex;border-radius:20px;font-weight:700;font-size:0.75rem;padding:4px 12px;}
.pill-pending{background:#FFF8E6;color:#8B6A00;}
.pill-submitted,.pill-under_review{background:#FFF0E6;color:#8B3D00;}
.pill-delivered{background:#EBF6F0;color:#1B6B3A;}
.pill-approved{background:#E8F5E9;color:#1B5E20;}
.pill-rejected{background:#FDECEA;color:#8B1A1A;}
.pill-assigned,.pill-in_progress{background:#EEF4FB;color:#1A3A5C;}
.room-card{border:1.5px solid #DDE3EC;border-radius:12px;padding:1rem;margin-bottom:1rem;}
.room-card.approved-card{border-color:#8FD4AE;background:#F6FCF8;}
.room-card.rejected-card{border-color:#F0A0A0;background:#FEF6F6;}
.cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;}
.cmp-grid img{width:100%;border-radius:8px;border:1px solid #DDE3EC;cursor:zoom-in;}
.cmp-cap{font-size:0.7rem;font-weight:700;color:#8B9AAB;text-transform:uppercase;margin-bottom:4px;}
.btn-approve-img{background:#16A34A;color:#fff;border:none;border-radius:8px;padding:8px 20px;font-size:0.82rem;font-weight:700;cursor:pointer;}
.btn-reject-img{background:#fff;color:#DC2626;border:1.5px solid #DC2626;border-radius:8px;padding:8px 20px;font-size:0.82rem;font-weight:700;cursor:pointer;}
.btn-disabled{opacity:0.4;cursor:not-allowed;pointer-events:none;}
.edit-textarea{width:100%;border:1.5px solid #DDE3EC;border-radius:8px;padding:8px 10px;font-size:0.85rem;font-family:inherit;margin:8px 0;}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,0.85);display:none;align-items:center;justify-content:center;z-index:2000;padding:2rem;}
.lightbox.open{display:flex;}
.lightbox img{max-width:95%;max-height:90%;border-radius:6px;}
`;

export default function OrderDetail({ session }) {
  const { orderId } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [statuses, setStatuses] = useState({}); // deliverable_id -> img_status
  const [remarks, setRemarks] = useState({});
  const [qcNote, setQcNote] = useState('');
  const [lb, setLb] = useState(null);
  const [toast, setToast] = useState(null);
  const isAdmin = session?.user?.role === 'admin';

  const load = () => apiGet(`/order/${orderId}`).then(r => {
    if (r.redirect) { nav(r.redirect); return; }
    setD(r);
    setStatuses(Object.fromEntries((r.deliverables || []).map(dv => [dv.id, dv.img_status || 'pending'])));
  });
  useEffect(() => { load(); }, [orderId]);

  function flash(msg, ok = true) { setToast({ msg, ok }); setTimeout(() => setToast(null), 2500); }

  async function reviewImg(dvId, action) {
    const remark = (remarks[dvId] || '').trim();
    if (action === 'reject' && !remark) { flash('Enter a rejection remark before rejecting.', false); return; }
    const r = await apiPost('/api/admin/review-image', { deliverable_id: dvId, action, remark });
    if (r.success) { setStatuses(s => ({ ...s, [dvId]: r.img_status })); flash(action === 'approve' ? '✓ Image approved' : '✗ Rejected — pilot notified', action === 'approve'); }
    else flash(r.error || 'Error', false);
  }
  async function orderQC(action) {
    const url = action === 'approve' ? '/api/admin/mark-delivered' : '/api/admin/reject-to-pilot';
    const r = await apiPost(url, { order_id: Number(orderId), note: qcNote.trim() });
    if (r.success) { flash(action === 'approve' ? '✓ Delivered to client!' : '✗ Rejected back to pilot'); setTimeout(load, 1200); }
    else flash(r.error || 'Error', false);
  }
  async function confirmPayment() {
    if (!window.confirm('Have you verified the payment? This will immediately unlock the client download.')) return;
    const r = await apiPost('/api/admin/confirm-payment', { order_id: Number(orderId) });
    if (r.success) { flash('✓ Payment confirmed'); setTimeout(load, 1200); }
    else flash(r.error || 'Error', false);
  }

  const order = d?.order;
  const intake = d?.intake || {};
  const attachments = d?.attachments || [];
  const deliverables = d?.deliverables || [];
  const imgAtts = useMemo(() => attachments.filter(a => isImg(a.filename)), [attachments]);
  const otherFiles = useMemo(() => attachments.filter(a => !isImg(a.filename)), [attachments]);

  // before/after pairing by file_label (simplified port of the Jinja logic)
  const beforeFor = (dv, idx) => {
    if (dv.file_label) {
      const m = imgAtts.find(a => a.file_label && a.file_label === dv.file_label
        && !(a.attachment_type || '').endsWith('_b'));
      if (m) return m;
    }
    return imgAtts[idx] || null;
  };

  if (!d || !order) return null;
  const canQC = isAdmin && ['submitted', 'under_review'].includes(order.status);

  return (
    <div>
      <style>{css}</style>
      <div className="od-top">
        <Link to="/" className="od-logo">Dele<span>qate</span></Link>
        <Link to="/admin/dashboard" className="od-back">← Admin Queue</Link>
        <Link to="/logout" style={{ fontSize: '0.82rem', color: '#8B9AAB', textDecoration: 'none' }}>Logout</Link>
      </div>

      <div className="od-wrap">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
          <h1 style={{ margin: 0, fontSize: '1.6rem', color: '#1A3A5C' }}>Order #{order.id}</h1>
          <span className={`pill pill-${order.status || 'pending'}`}>{title(order.status || 'pending')}</span>
          {order.assigned_pilot_id && (
            <Link to={`/pilot/execute/${order.id}`} style={{ background: '#1A3A5C', color: '#fff', borderRadius: 9, padding: '8px 18px', fontSize: '0.82rem', fontWeight: 700, textDecoration: 'none' }}>Open Execution</Link>
          )}
        </div>

        <div className="od-card">
          <h2>Order Summary</h2>
          {[
            ['Name', order.name || order.client_name || '—'],
            ['Phone', order.phone || order.client_phone || '—'],
            ['Email', order.email || order.client_email || '—'],
            ['Task', title(order.task_type || order.task || '—')],
            ['Units', order.render_count || 1],
            ['Total', rupees(order.total_price)],
            ['Pilot Payout', rupees(order.pilot_payout)],
            ['Pilot', order.pilot_name || '—'],
            ['Submitted', order.created_at ? String(order.created_at).slice(0, 16) : '—'],
            ['Assigned', order.assigned_at ? String(order.assigned_at).slice(0, 16) : 'Pending'],
          ].map(([k, v]) => (
            <div className="od-row" key={k}><span className="od-row-lbl">{k}</span><span className="od-row-val">{v}</span></div>
          ))}
        </div>

        <div className="od-card">
          <h2>Brief / Intake</h2>
          {Object.keys(intake).filter(k => k !== 'rooms').length === 0 && !intake.rooms && (
            <div style={{ color: '#8B9AAB', fontSize: '0.85rem' }}>No intake data.</div>
          )}
          {Object.entries(intake).filter(([k]) => k !== 'rooms').map(([k, v]) => (
            <div className="od-row" key={k}>
              <span className="od-row-lbl">{title(k)}</span>
              <span className="od-row-val">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
            </div>
          ))}
          {Array.isArray(intake.rooms) && intake.rooms.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div className="cmp-cap">Rooms</div>
              {intake.rooms.map((room, i) => (
                <div key={i} style={{ fontSize: '0.82rem', color: '#1A3A5C', padding: '4px 0' }}>
                  {room.label || room.room_label || `Room ${i + 1}`}
                  {room.geometry && <span style={{ color: '#8B9AAB', fontSize: '0.75rem' }}> · {room.geometry}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {otherFiles.length > 0 && (
          <div className="od-card">
            <h2>Other Files</h2>
            {otherFiles.map(a => (
              <div key={a.id} className="od-row">
                <span className="od-row-lbl">{a.original_name || a.filename}<br /><small>{a.attachment_type}</small></span>
                <a href={fileUrl(`/uploads/${a.filename}`)} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1A3A5C', border: '1px solid #DDE3EC', borderRadius: 6, padding: '4px 12px', textDecoration: 'none' }}>View</a>
              </div>
            ))}
          </div>
        )}

        <div className="od-card">
          <h2>Deliverables &amp; QC ({deliverables.length})</h2>
          {deliverables.length === 0 && <div style={{ color: '#8B9AAB', fontSize: '0.85rem' }}>No deliverables submitted yet.</div>}
          {deliverables.map((dv, idx) => {
            const st = statuses[dv.id] || 'pending';
            const before = beforeFor(dv, idx);
            const afterUrl = fileUrl(`/api/preview-img/${dv.filename}`);
            const showImg = isImg(dv.filename);
            return (
              <div key={dv.id} className={`room-card ${st}-card`}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
                  {dv.file_label && <span style={{ background: '#C9A84C', color: '#fff', borderRadius: 5, padding: '3px 10px', fontSize: '0.72rem', fontWeight: 800 }}>{dv.file_label}</span>}
                  <span style={{ fontSize: '0.78rem', color: '#8B9AAB' }}>{idx + 1} of {deliverables.length} · {dv.original_name || dv.filename}</span>
                  <span className={`pill pill-${st === 'approved' ? 'approved' : st === 'rejected' ? 'rejected' : 'pending'}`} style={{ marginLeft: 'auto' }}>{st}</span>
                </div>
                {showImg ? (
                  <div className="cmp-grid">
                    {before && (
                      <div>
                        <div className="cmp-cap">Before (client photo)</div>
                        <img src={fileUrl(`/uploads/${before.filename}`)} alt="Before" onClick={() => setLb({ src: fileUrl(`/uploads/${before.filename}`), label: 'Before' })} />
                      </div>
                    )}
                    <div>
                      <div className="cmp-cap">After (deliverable)</div>
                      <img src={afterUrl} alt="After" onClick={() => setLb({ src: afterUrl, label: dv.file_label || 'Deliverable' })} />
                    </div>
                  </div>
                ) : (
                  <a href={fileUrl(`/deliverables/${dv.filename}`)} target="_blank" rel="noreferrer" style={{ fontSize: '0.82rem', fontWeight: 700, color: '#1A3A5C' }}>↓ {dv.original_name || dv.filename}</a>
                )}

                {canQC && (
                  <>
                    <textarea className="edit-textarea" rows="2" placeholder="Rejection remark (required to reject)"
                      value={remarks[dv.id] || ''} onChange={e => setRemarks(r => ({ ...r, [dv.id]: e.target.value }))} />
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className={`btn-approve-img ${st === 'approved' ? 'btn-disabled' : ''}`} onClick={() => reviewImg(dv.id, 'approve')}>✓ Approve</button>
                      <button className={`btn-reject-img ${st === 'rejected' ? 'btn-disabled' : ''}`} onClick={() => reviewImg(dv.id, 'reject')}>✗ Reject</button>
                    </div>
                  </>
                )}
              </div>
            );
          })}

          {canQC && (
            <div style={{ marginTop: '1rem', borderTop: '1px solid #DDE3EC', paddingTop: '1rem' }}>
              <textarea className="edit-textarea" rows="2" placeholder="Optional QC note for the whole order"
                value={qcNote} onChange={e => setQcNote(e.target.value)} />
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn-approve-img" onClick={() => orderQC('approve')}>✓ QC Pass — Deliver to Client</button>
                <button className="btn-reject-img" onClick={() => orderQC('reject')}>✗ Reject All — Back to Pilot</button>
              </div>
            </div>
          )}

          {isAdmin && order.status === 'delivered' && order.payment_method && order.payment_method !== 'payu' && order.payment_method !== 'free_pass' && (
            <button className="btn-approve-img" style={{ marginTop: '1rem' }} onClick={confirmPayment}>✓ Confirm Payment &amp; Unlock Download</button>
          )}
        </div>
      </div>

      <div className={`lightbox ${lb ? 'open' : ''}`} onClick={() => setLb(null)}>
        {lb && <img src={lb.src} alt={lb.label} />}
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 3000, padding: '0.8rem 1.3rem', borderRadius: 10, fontWeight: 600, fontSize: '0.9rem', color: '#fff', background: toast.ok ? '#1B6B3A' : '#dc2626' }}>{toast.msg}</div>
      )}
    </div>
  );
}
