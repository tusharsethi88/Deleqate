// Functional port of the pilot execution flow (templates/pilot_execute.html +
// pilot_sku_workflow.html). Covers the core pilot loop: review brief & client
// files, upload/delete deliverables, view edit requests, and submit for QC.
// GET /pilot/job/<id> (JSON) and posts to /api/pilot/*.
//
// NOTE: the SKU-specific AI sub-workflows in the original (spatial analysis,
// per-POV prompt A/B generation, moodboard prompts) are a large specialised
// subsystem and are intentionally not reproduced here — see README note.
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiGet, apiPost, apiPostForm, fileUrl } from '../api.js';

const IMG = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'avif'];
const ext = (fn) => (fn && fn.includes('.') ? fn.split('.').pop().toLowerCase() : '');
const isImg = (fn) => IMG.includes(ext(fn));
const title = (s) => (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const css = `
.pe-top{display:flex;align-items:center;gap:1rem;background:#fff;border-bottom:1px solid #DDE3EC;padding:0.85rem 1.5rem;}
.pe-logo{font-weight:800;color:#1A3A5C;text-decoration:none;}.pe-logo span{color:var(--gold);}
.pe-back{margin-left:auto;font-size:0.82rem;color:#1A3A5C;font-weight:600;text-decoration:none;}
.pe-wrap{max-width:980px;margin:0 auto;padding:1.5rem;}
.pe-card{background:#fff;border:1px solid #DDE3EC;border-radius:14px;padding:1.5rem;margin-bottom:1.25rem;}
.pe-card h2{font-size:0.95rem;color:#1A3A5C;margin:0 0 1rem;font-weight:800;}
.pe-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #EEF1F6;font-size:0.85rem;}
.pe-row-lbl{color:#8B9AAB;}.pe-row-val{color:#1A3A5C;font-weight:600;text-align:right;}
.att-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0.75rem;}
.att-grid img{width:100%;border-radius:8px;border:1px solid #DDE3EC;cursor:zoom-in;}
.del-row{display:flex;align-items:center;gap:0.75rem;border:1px solid #EEF1F6;border-radius:10px;padding:0.6rem 0.85rem;margin-bottom:0.5rem;}
.del-row img{width:54px;height:54px;object-fit:cover;border-radius:6px;}
.pe-input{padding:7px 10px;border:1.5px solid #DDE3EC;border-radius:8px;font-size:0.85rem;}
.pe-btn{background:#1A3A5C;color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:0.85rem;font-weight:700;cursor:pointer;}
.pe-btn.gold{background:#C9A84C;}.pe-btn.danger{background:#fff;color:#DC2626;border:1.5px solid #DC2626;}
.pe-btn.success{background:#16A34A;}
.pill{display:inline-flex;border-radius:20px;font-weight:700;font-size:0.72rem;padding:3px 10px;}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,0.85);display:none;align-items:center;justify-content:center;z-index:2000;padding:2rem;}
.lightbox.open{display:flex;}.lightbox img{max-width:95%;max-height:90%;border-radius:6px;}
`;

export default function PilotExecute() {
  const { orderId } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [room, setRoom] = useState('');
  const [pov, setPov] = useState('A');
  const [uploading, setUploading] = useState(false);
  const [lb, setLb] = useState(null);
  const [toast, setToast] = useState(null);
  const fileRef = useRef(null);

  const load = () => apiGet(`/pilot/job/${orderId}`).then(r => {
    if (r.redirect) { nav(r.redirect); return; }
    setD(r);
  });
  useEffect(() => { load(); }, [orderId]);
  function flash(msg, ok = true) { setToast({ msg, ok }); setTimeout(() => setToast(null), 2800); }

  async function upload(e) {
    e.preventDefault();
    const f = fileRef.current?.files?.[0];
    if (!f) { flash('Choose a file first.', false); return; }
    setUploading(true);
    const fd = new FormData();
    fd.set('order_id', orderId);
    fd.set('file', f);
    if (room.trim()) fd.set('room_label', room.trim());
    fd.set('pov', pov);
    const r = await apiPostForm('/api/pilot/upload-deliverable', fd);
    setUploading(false);
    if (r.success) { flash('Deliverable uploaded.'); fileRef.current.value = ''; setRoom(''); load(); }
    else flash(r.error || 'Upload failed', false);
  }
  async function del(deliverable_id) {
    if (!window.confirm('Delete this deliverable?')) return;
    const r = await apiPost('/api/pilot/delete-deliverable', { deliverable_id, order_id: Number(orderId) });
    if (r.success) { flash('Deleted.'); load(); } else flash(r.error || 'Error', false);
  }
  async function submitForQC() {
    if (!window.confirm('Submit this job for QC review?')) return;
    const r = await apiPost('/api/pilot/complete', { order_id: Number(orderId) });
    if (r.success) { flash('Submitted for QC.'); setTimeout(load, 1000); } else flash(r.error || 'Error', false);
  }

  if (!d) return null;
  const order = d.order || {};
  const intake = d.intake || {};
  const attachments = d.attachments || [];
  const deliverables = d.uploaded_deliverables || [];
  const editRequests = d.edit_requests || [];
  const imgAtts = attachments.filter(a => isImg(a.filename));
  const otherAtts = attachments.filter(a => !isImg(a.filename));

  return (
    <div>
      <style>{css}</style>
      <div className="pe-top">
        <Link to="/" className="pe-logo">Dele<span>qate</span></Link>
        <Link to="/pilot/dashboard" className="pe-back">← My Jobs</Link>
        <Link to="/logout" style={{ fontSize: '0.82rem', color: '#8B9AAB', textDecoration: 'none' }}>Logout</Link>
      </div>

      <div className="pe-wrap">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#1A3A5C' }}>Order #{order.id} · {d.task_label}</h1>
          <span className="pill" style={{ background: '#EEF4FB', color: '#1A3A5C' }}>{title(order.status)}</span>
        </div>

        {editRequests.length > 0 && (
          <div className="pe-card" style={{ borderColor: '#F0A0A0', background: '#FEF6F6' }}>
            <h2 style={{ color: '#8B1A1A' }}>✏️ Client Edit Requests</h2>
            {editRequests.map((er, i) => (
              <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px dashed #F0C9C9', fontSize: '0.85rem' }}>
                {er.remark || '(no remark)'}
                {er.attachment_filename && <> · <a href={fileUrl(`/uploads/${er.attachment_filename}`)} target="_blank" rel="noreferrer">attachment</a></>}
              </div>
            ))}
          </div>
        )}

        <div className="pe-card">
          <h2>Brief / Intake</h2>
          {Object.entries(intake).filter(([k]) => k !== 'rooms').map(([k, v]) => (
            <div className="pe-row" key={k}><span className="pe-row-lbl">{title(k)}</span><span className="pe-row-val">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span></div>
          ))}
          {Array.isArray(intake.rooms) && intake.rooms.length > 0 && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.82rem', color: '#1A3A5C' }}>
              <strong>Rooms:</strong> {intake.rooms.map((r, i) => r.label || r.room_label || `Room ${i + 1}`).join(', ')}
            </div>
          )}
        </div>

        <div className="pe-card">
          <h2>Client Files ({attachments.length})</h2>
          {imgAtts.length > 0 && (
            <div className="att-grid">
              {imgAtts.map(a => (
                <div key={a.id}>
                  <img src={fileUrl(`/uploads/${a.filename}`)} alt={a.file_label || a.attachment_type} onClick={() => setLb(fileUrl(`/uploads/${a.filename}`))} />
                  <div style={{ fontSize: '0.7rem', color: '#8B9AAB', marginTop: 3 }}>{a.file_label || a.attachment_type}</div>
                </div>
              ))}
            </div>
          )}
          {otherAtts.map(a => (
            <div key={a.id} className="pe-row">
              <span className="pe-row-lbl">{a.original_name || a.filename} <small>({a.attachment_type})</small></span>
              <a href={fileUrl(`/uploads/${a.filename}`)} target="_blank" rel="noreferrer" className="pe-row-val">View</a>
            </div>
          ))}
          {attachments.length === 0 && <div style={{ color: '#8B9AAB', fontSize: '0.85rem' }}>No client files.</div>}
        </div>

        <div className="pe-card">
          <h2>Deliverables ({deliverables.length})</h2>
          {deliverables.map(dv => (
            <div className="del-row" key={dv.id}>
              {isImg(dv.filename)
                ? <img src={fileUrl(`/api/preview-img/${dv.filename}`)} alt="" onClick={() => setLb(fileUrl(`/api/preview-img/${dv.filename}`))} style={{ cursor: 'zoom-in' }} />
                : <span style={{ fontSize: '1.4rem' }}>📄</span>}
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1A3A5C' }}>{dv.original_name || dv.filename}</div>
                <div style={{ fontSize: '0.72rem', color: '#8B9AAB' }}>{dv.file_label ? `${dv.file_label} · ` : ''}POV {dv.pov || 'A'} · {dv.img_status || 'pending'}</div>
              </div>
              <button className="pe-btn danger" onClick={() => del(dv.id)}>Delete</button>
            </div>
          ))}
          {deliverables.length === 0 && <div style={{ color: '#8B9AAB', fontSize: '0.85rem', marginBottom: '0.75rem' }}>No deliverables uploaded yet.</div>}

          <form onSubmit={upload} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: '1rem', borderTop: '1px solid #EEF1F6', paddingTop: '1rem' }}>
            <input ref={fileRef} type="file" className="pe-input" />
            <input className="pe-input" placeholder="Room / label (optional)" value={room} onChange={e => setRoom(e.target.value)} />
            <select className="pe-input" value={pov} onChange={e => setPov(e.target.value)}>
              <option value="A">POV A</option><option value="B">POV B</option>
            </select>
            <button className="pe-btn gold" type="submit" disabled={uploading}>{uploading ? 'Uploading…' : '↑ Upload deliverable'}</button>
          </form>
        </div>

        {deliverables.length > 0 && !['under_review', 'delivered', 'approved'].includes(order.status) && (
          <button className="pe-btn success" style={{ fontSize: '1rem', padding: '12px 28px' }} onClick={submitForQC}>✓ Submit for QC Review</button>
        )}
      </div>

      <div className={`lightbox ${lb ? 'open' : ''}`} onClick={() => setLb(null)}>{lb && <img src={lb} alt="" />}</div>
      {toast && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 3000, padding: '0.8rem 1.3rem', borderRadius: 10, fontWeight: 600, fontSize: '0.9rem', color: '#fff', background: toast.ok ? '#1B6B3A' : '#dc2626' }}>{toast.msg}</div>
      )}
    </div>
  );
}
