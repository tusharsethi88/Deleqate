// Port of templates/client_preview.html — client review/approve/edit/reject.
// GET /order/<id>/preview (JSON) → deliverables/attachments/edit_credits/has_paid_before.
// Actions POST (multipart) to /order/<id>/client-choice and follow {redirect}.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiGet, apiPostForm, getCsrf, fileUrl } from '../api.js';

const IMG = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'];
const ext = (fn) => (fn && fn.includes('.') ? fn.split('.').pop().toLowerCase() : '');
const isImg = (fn) => IMG.includes(ext(fn));

const css = `
.cp-top { display: flex; align-items: center; gap: 1rem; background: var(--surface-white, #fff); padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-soft, #E6ECF1); }
.cp-top .brand { display: block; }
.cp-top .brand img, .cp-top .brand video { height: 40px; width: auto; display: block; } /* Removed mix-blend-mode: multiply so the logo works normally */
.cp-top-order { color: var(--text-secondary, #5C7386); font-size: 0.9rem; font-weight: 600; margin-left: 1rem; }
.back-link { margin-left: auto; color: var(--text-secondary, #5C7386); font-size: 0.85rem; font-weight: 600; text-decoration: none; transition: color 0.2s; }
.back-link:hover { color: var(--gold-dark, #1E2A39); }

.cp-wrap { max-width: 900px; margin: 0 auto; padding: 3rem 1.5rem 5rem; }
.cp-wrap h1 { font-family: var(--font-display, 'Syne', sans-serif); font-size: 2rem; color: var(--text-primary, #0B0F14); margin-bottom: 1.5rem; letter-spacing: -0.02em; }

.cp-deliv { background: var(--surface-white, #fff); border: 1px solid var(--border, #D6DEE6); border-radius: var(--radius-xl, 12px); overflow: hidden; margin-bottom: 2rem; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05)); }
.cp-deliv-hd { display: flex; align-items: center; gap: 0.8rem; padding: 1rem 1.25rem; background: var(--surface-low, #E8EEF2); border-bottom: 1px solid var(--border, #D6DEE6); }
.cp-deliv-hd .lbl { background: var(--gold-dark, #1E2A39); color: #fff; border-radius: var(--radius, 4px); padding: 4px 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
.cp-deliv-hd .meta { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary, #5C7386); }

.cp-cmp { position: relative; line-height: 0; overflow: hidden; cursor: col-resize; user-select: none; }
.cp-cmp img { width: 100%; display: block; pointer-events: none; }
.cp-cmp .after { position: absolute; inset: 0; clip-path: inset(0 0 0 var(--split, 50%)); }
.cp-handle { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--gold, #D4AF37); left: var(--split, 50%); z-index: 10; }
.cp-handle::after { content: '⇆'; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--gold, #D4AF37); color: #fff; border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-weight: 900; box-shadow: var(--shadow, 0 4px 12px rgba(0,0,0,0.15)); border: 2px solid #fff; }

.action-wrap { margin-bottom: 2rem; }
.action-card { border: 1px solid var(--border, #D6DEE6); border-radius: var(--radius-xl, 12px); padding: 2rem; background: var(--surface-white, #fff); box-shadow: var(--shadow, 0 4px 12px rgba(0,0,0,0.05)); }
.tabs { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.tab-btn { font-family: var(--font-sans, 'Inter', sans-serif); font-size: 0.9rem; font-weight: 600; border: 1px solid var(--border, #D6DEE6); background: var(--surface-white, #fff); color: var(--text-secondary, #5C7386); padding: 10px 20px; border-radius: var(--radius-pill, 99px); cursor: pointer; transition: all 0.2s ease; }
.tab-btn:hover { border-color: var(--text-muted, #7E93A3); color: var(--text-primary, #0B0F14); }
.tab-btn.active { border-color: var(--gold-dark, #1E2A39); color: #fff; background: var(--gold-dark, #1E2A39); }
.tab-btn.danger.active { border-color: var(--danger, #ba1a1a); color: #fff; background: var(--danger, #ba1a1a); }

.btn-action-primary { font-family: var(--font-sans, 'Inter', sans-serif); background: var(--gold-dark, #1E2A39); color: #fff; border: none; border-radius: var(--radius-lg, 8px); padding: 14px 28px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; transition: background 0.2s; }
.btn-action-primary:hover { background: var(--gold-bright, #2C3E54); }
.btn-action-primary.btn-gold { background: var(--gold, #D4AF37); color: #000; }
.btn-action-primary.btn-gold:hover { background: #c39d2c; }
.btn-action-danger { background: var(--danger, #ba1a1a); color: #fff; border: none; border-radius: var(--radius-lg, 8px); padding: 14px 28px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; transition: opacity 0.2s; }
.btn-action-danger:hover { opacity: 0.9; }

.edit-textarea { width: 100%; border: 1px solid var(--border, #D6DEE6); border-radius: var(--radius-lg, 8px); padding: 12px 14px; font-size: 0.95rem; font-family: inherit; margin: 8px 0; outline: none; transition: border-color 0.2s; }
.edit-textarea:focus { border-color: var(--gold-dark, #1E2A39); }
.edit-row { border: 1px solid var(--border-soft, #E6ECF1); border-radius: var(--radius-lg, 8px); padding: 1rem; margin-bottom: 1rem; background: var(--surface, #F5F8FA); }

.btn-download-file { display: inline-flex; align-items: center; justify-content: center; background: var(--gold-dark, #1E2A39); color: #fff; font-weight: 600; text-decoration: none; border-radius: var(--radius-lg, 8px); padding: 12px 24px; font-size: 0.95rem; transition: background 0.2s; }
.btn-download-file:hover { background: var(--gold-bright, #2C3E54); color: #fff; }
`;

function Slider({ before, after }) {
  const ref = useRef(null);
  const [split, setSplit] = useState(50);
  const move = (clientX) => {
    const el = ref.current; if (!el) return;
    const r = el.getBoundingClientRect();
    setSplit(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  };
  return (
    <div className="cp-cmp" ref={ref} style={{ '--split': `${split}%` }}
      onMouseMove={e => e.buttons === 1 && move(e.clientX)}
      onClick={e => move(e.clientX)}
      onTouchMove={e => move(e.touches[0].clientX)}>
      <img src={before} alt="Before" />
      <img className="after" src={after} alt="After" />
      <div className="cp-handle" />
    </div>
  );
}

// Loads a deliverable through the authenticated fetch path (same one used for
// JSON, so CORS/cookies already work) and renders it as a same-origin blob.
// Direct cross-origin <iframe src> loads of the backend PDF were failing with
// ERR_CONNECTION_REFUSED in some browsers; blob URLs avoid that entirely.
function MediaFrame({ url, kind }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let active = true; let made = null;
    setBlobUrl(null); setErr(null);
    fetch(url, { credentials: 'include' })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.blob(); })
      .then(b => { if (!active) return; made = URL.createObjectURL(b); setBlobUrl(made); })
      .catch(e => active && setErr(e.message || 'Failed to load'));
    return () => { active = false; if (made) URL.revokeObjectURL(made); };
  }, [url]);
  if (err) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5C7386' }}>Preview unavailable ({err}).</div>;
  if (!blobUrl) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5C7386' }}>Loading preview…</div>;
  return <iframe src={blobUrl} title={kind === 'pdf' ? 'PDF Preview' : 'HTML Preview'}
    style={{ width: '100%', height: '800px', border: 'none', background: '#fff' }}
    {...(kind === 'html' ? { sandbox: 'allow-same-origin allow-scripts' } : {})} />;
}

export default function ClientPreview() {
  const { orderId } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [tab, setTab] = useState(null);
  const [busy, setBusy] = useState(false);
  const [remarks, setRemarks] = useState({});
  const [files, setFiles] = useState({});
  const [reject, setReject] = useState('');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    apiGet(`/order/${orderId}/preview`).then(r => {
      if (r.redirect) { nav(r.redirect); return; }
      setD(r);
      setTab(r.has_paid_before ? 'accept' : 'pay');
    });
  }, [orderId]);

  useEffect(() => {
    if (d && window.lucide) {
      window.lucide.createIcons();
    }
  }, [d, tab]);

  const order = d?.order;
  const deliverables = d?.deliverables || [];
  const attachments = d?.attachments || [];
  const imgAtts = useMemo(() => attachments.filter(a => isImg(a.filename)), [attachments]);

  const beforeFor = (dv, idx) => {
    if (dv.file_label) {
      const m = imgAtts.find(a => a.file_label === dv.file_label && !(a.attachment_type || '').endsWith('_b'));
      if (m) return m;
    }
    return imgAtts[idx] || null;
  };

  function flash(msg, ok = true) { setToast({ msg, ok }); setTimeout(() => setToast(null), 3000); }

  async function submitAction(action, withEdits) {
    setBusy(true);
    const fd = new FormData();
    fd.set('action', action);
    fd.set('csrf_token', getCsrf() || '');
    if (action === 'reject') fd.set('rejection_remark', reject);
    if (withEdits) {
      deliverables.forEach(dv => {
        const rk = (remarks[dv.id] || '').trim();
        const f = files[dv.id];
        if (rk || f) {
          fd.append('deliverable_id[]', dv.id);
          fd.append('edit_remark[]', rk);
          fd.append('edit_attachment[]', f || new Blob([]));
        }
      });
    }
    try {
      const r = await apiPostForm(`/order/${orderId}/client-choice`, fd);
      if (r.redirect) { nav(r.redirect); return; }
      if (r.success === false) { flash(r.error || 'Something went wrong.', false); setBusy(false); }
    } catch { flash('Network error. Please try again.', false); setBusy(false); }
  }

  if (!d || !order) return null;
  const credits = d.edit_credits || 0;
  const totalRupees = `₹${(order.total_price / 100).toString().replace(/\.0$/, '')}`;

  const EditRows = ({ idPrefix }) => (
    <>
      {deliverables.map(dv => (
        <div className="edit-row" key={`${idPrefix}-${dv.id}`}>
          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#1A3A5C', marginBottom: 4 }}>{dv.file_label || dv.original_name || dv.filename}</div>
          <textarea className="edit-textarea" rows="2" placeholder="Describe what needs to change — be specific"
            value={remarks[dv.id] || ''} onChange={e => setRemarks(r => ({ ...r, [dv.id]: e.target.value }))} />
          <input type="file" accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.docx,.txt,.mp4,.mov,.zip"
            onChange={e => setFiles(f => ({ ...f, [dv.id]: e.target.files[0] }))} />
        </div>
      ))}
    </>
  );

  return (
    <div>
      <style>{css}</style>
      <div className="cp-top">
        <Link to="/" className="brand"><img src="/img/logo.png" alt="Delegate" /></Link>
        <span className="cp-top-order">Order #{order.id} · {d.task_label}</span>
        <Link to="/client/orders" className="back-link" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <i data-lucide="arrow-left" style={{ width: 14, height: 14 }}></i> Back to My Orders
        </Link>
      </div>

      <div className="cp-wrap">
        <h1>Review your {d.task_label}</h1>

        {deliverables.map((dv, idx) => {
          const before = beforeFor(dv, idx);
          const afterUrl = fileUrl(`/api/preview-img/${dv.filename}`);
          const showSlider = isImg(dv.filename) && before && isImg(before.filename);
          return (
            <div className="cp-deliv" key={dv.id}>
              <div className="cp-deliv-hd">
                {dv.file_label && <span className="lbl">{dv.file_label}</span>}
                <span className="meta">{idx + 1} of {deliverables.length} · {dv.original_name || dv.filename}</span>
              </div>
              {showSlider
                ? <Slider before={fileUrl(`/uploads/${before.filename}`)} after={afterUrl} />
                : isImg(dv.filename)
                  ? <img src={afterUrl} alt="Deliverable" style={{ width: '100%', display: 'block' }} />
                  : (dv.filename.endsWith('.html') || dv.filename.endsWith('.htm') || dv.filename.endsWith('.pdf'))
                    ? <MediaFrame url={afterUrl} kind={dv.filename.endsWith('.pdf') ? 'pdf' : 'html'} />
                  : <div style={{ padding: '1.5rem', textAlign: 'center' }}>
                      <a href={fileUrl(`/deliverables/${dv.filename}?download=1`)} download
                         style={{ color: '#C9A84C', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <i data-lucide="download" style={{ width: 16, height: 16 }}></i> {dv.original_name || dv.filename}
                      </a>
                    </div>}

              {order.status === 'approved' && (
                <div style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                  <a className="btn-download-file"
                     href={fileUrl(`/deliverables/${dv.filename}?download=1`)} download
                     style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                    <i data-lucide="download" style={{ width: 14, height: 14 }}></i> Download
                  </a>
                </div>
              )}
            </div>
          );
        })}

        {/* ── Action panels ── */}
        {order.status === 'approved' && (
          <div className="action-wrap"><div className="action-card" style={{ borderColor: '#16A34A' }}>
            <h3 style={{ color: '#16A34A', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <i data-lucide="check-circle" style={{ width: 18, height: 18 }}></i>
              <span>Approved</span>
            </h3>
            <p style={{ marginTop: '6px' }}>You've approved this delivery. <Link to={`/order/success?id=${order.id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>Download your files <i data-lucide="arrow-right" style={{ width: 14, height: 14 }}></i></Link></p>
          </div></div>
        )}
        {order.status === 'rejected_by_client' && (
          <div className="action-wrap"><div className="action-card" style={{ borderColor: '#DC2626' }}>
            <h3 style={{ color: '#DC2626', margin: 0 }}>Rejection submitted</h3>
            {order.rejection_remark && <p>{order.rejection_remark}</p>}
          </div></div>
        )}

        {order.status === 'delivered' && !d.has_paid_before && (
          <div className="action-wrap">
            <div className="tabs">
              <button className={`tab-btn ${tab === 'pay' ? 'active' : ''}`} onClick={() => setTab('pay')} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <i data-lucide="check-circle" style={{ width: 13, height: 13 }}></i> Pay &amp; Download
              </button>
              <button className={`tab-btn ${tab === 'edit' ? 'active' : ''}`} onClick={() => setTab('edit')} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <i data-lucide="edit-3" style={{ width: 13, height: 13 }}></i> Pay with Edit
              </button>
              <button className={`tab-btn danger ${tab === 'reject' ? 'active' : ''}`} onClick={() => setTab('reject')}>Not happy? Reject</button>
            </div>
            {tab === 'pay' && (
              <div className="action-card" style={{ borderColor: '#2E6B2E' }}>
                <p>Pay securely and unlock your full-resolution files instantly.</p>
                <button className="btn-action-primary" disabled={busy} onClick={() => submitAction('pay_download', false)} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <i data-lucide="credit-card" style={{ width: 16, height: 16 }}></i> Pay {totalRupees} &amp; Download
                </button>
              </div>
            )}
            {tab === 'edit' && (
              <div className="action-card" style={{ borderColor: '#C9A84C' }}>
                <p>Request changes, then pay — the pilot will revise and redeliver.</p>
                <EditRows idPrefix="pe" />
                <button className="btn-action-primary btn-gold" disabled={busy} onClick={() => submitAction('pay_edit', true)} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <i data-lucide="edit-3" style={{ width: 16, height: 16 }}></i> Submit Edits &amp; Pay {totalRupees}
                </button>
              </div>
            )}
            {tab === 'reject' && (
              <div className="action-card" style={{ borderColor: '#7F1D1D' }}>
                <p>Tell us clearly what was wrong. No payment is taken for rejected first-order work.</p>
                <textarea className="edit-textarea" rows="4" placeholder="Explain clearly what was wrong…" value={reject} onChange={e => setReject(e.target.value)} />
                <button className="btn-action-danger" disabled={busy} onClick={() => { if (!reject.trim()) { flash('Please enter a reason.', false); return; } if (window.confirm('Submit rejection?')) submitAction('reject', false); }} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <i data-lucide="x-circle" style={{ width: 16, height: 16 }}></i> Submit Rejection
                </button>
              </div>
            )}
          </div>
        )}

        {order.status === 'delivered' && d.has_paid_before && (
          <div className="action-wrap">
            <div className="tabs">
              <button className={`tab-btn ${tab === 'accept' ? 'active' : ''}`} onClick={() => setTab('accept')} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <i data-lucide="check-circle" style={{ width: 13, height: 13 }}></i> Accept &amp; Download
              </button>
              <button className={`tab-btn ${tab === 'cedit' ? 'active' : ''}`} onClick={() => setTab('cedit')} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <i data-lucide="edit-3" style={{ width: 13, height: 13 }}></i> Request Edit{credits > 0 ? ` (${credits} free)` : ''}
              </button>
            </div>
            {tab === 'accept' && (
              <div className="action-card" style={{ borderColor: '#2E6B2E' }}>
                <p>Your payment is already on file — accept to unlock your final files.</p>
                <button className="btn-action-primary" disabled={busy} onClick={() => submitAction('accept', false)} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <i data-lucide="check" style={{ width: 16, height: 16 }}></i> Accept &amp; Download
                </button>
              </div>
            )}
            {tab === 'cedit' && (
              <div className="action-card" style={{ borderColor: '#C9A84C' }}>
                {credits > 0
                  ? <p>You have <strong style={{ color: '#C9A84C' }}>{credits} free edit credit{credits !== 1 ? 's' : ''}</strong> remaining.</p>
                  : <p>No free credits remaining — an edit will use a purchased credit.</p>}
                <EditRows idPrefix="ce" />
                <button className="btn-action-primary btn-gold" disabled={busy} onClick={() => submitAction('edit_free', true)} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <i data-lucide="edit-3" style={{ width: 16, height: 16 }}></i> Submit Edit Request
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 3000, padding: '0.8rem 1.3rem', borderRadius: 10, fontWeight: 600, fontSize: '0.9rem', color: '#fff', background: toast.ok ? '#1B6B3A' : '#dc2626' }}>{toast.msg}</div>
      )}
    </div>
  );
}
