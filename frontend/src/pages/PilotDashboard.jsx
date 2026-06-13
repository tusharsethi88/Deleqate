// Port of templates/pilot_dashboard.html — pilot's job queues.
// GET /pilot/dashboard (JSON) → active_jobs / completed_jobs / rejected_jobs.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet } from '../api.js';

const title = (s) => (s || 'Order').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const payout = (paise) => `₹${Number((paise || 0) / 100).toLocaleString('en-IN')}`;

const css = `
.pd-wrap{max-width:960px;margin:0 auto;padding:2rem 1.5rem 4rem;}
.pd-wrap h2{font-size:1.5rem;color:#1A3A5C;margin-bottom:0.25rem;}
.pd-wrap h3{margin:1.75rem 0 1rem;color:#1A3A5C;}
.job-card{background:#fff;border:1px solid #DDE3EC;border-radius:14px;padding:1.25rem 1.5rem;margin-bottom:1rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;}
.job-card.fix{border-color:#F0A0A0;background:#FEF6F6;}
.job-task{font-size:1.05rem;font-weight:700;color:#1A3A5C;}
.job-meta{font-size:0.8125rem;color:#8B9AAB;margin-top:0.25rem;}
.job-right{margin-left:auto;text-align:right;}
.badge{display:inline-block;border-radius:20px;font-weight:700;font-size:0.72rem;padding:3px 11px;margin-bottom:0.5rem;}
.badge-assigned,.badge-in_progress{background:#EEF4FB;color:#1A3A5C;}
.badge-submitted,.badge-under_review{background:#FFF0E6;color:#8B3D00;}
.badge-rejected{background:#FDECEA;color:#8B1A1A;}
.btn-gold{background:#C9A84C;color:#fff;border:none;border-radius:8px;padding:8px 18px;font-size:0.85rem;font-weight:700;text-decoration:none;cursor:pointer;}
.btn-fix{background:#DC2626;color:#fff;border:none;border-radius:8px;padding:8px 18px;font-size:0.85rem;font-weight:700;text-decoration:none;cursor:pointer;}
.ptable{width:100%;border-collapse:collapse;background:#fff;border:1px solid #DDE3EC;border-radius:12px;overflow:hidden;}
.ptable th,.ptable td{text-align:left;padding:0.7rem 0.9rem;font-size:0.85rem;border-bottom:1px solid #EEF1F6;}
.ptable th{background:#F7F9FC;color:#8B9AAB;font-size:0.78rem;text-transform:uppercase;}
.empty{background:#fff;border:1px dashed #DDE3EC;border-radius:14px;padding:2rem;text-align:center;color:#8B9AAB;}
`;

export default function PilotDashboard() {
  const nav = useNavigate();
  const [d, setD] = useState(null);

  useEffect(() => {
    apiGet('/pilot/dashboard').then(r => {
      if (r.redirect) { nav(r.redirect); return; }
      setD(r);
    });
  }, []);

  if (!d) return null;
  const active = (d.active_jobs || []).filter(o => !['rejected'].includes(o.status));
  const rejected = d.rejected_jobs || [];
  const completed = d.completed_jobs || [];

  return (
    <div>
      <style>{css}</style>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">Dele<span>qate</span></Link>
        <div className="navbar-nav">
          <Link to="/logout" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--navy)', border: '2px solid var(--navy)', borderRadius: 20, padding: '0.35rem 1rem' }}>Logout</Link>
        </div>
      </nav>

      <div className="pd-wrap">
        <h2>My Jobs</h2>
        <div style={{ color: '#8B9AAB', fontSize: '0.875rem' }}>{d.active_count || active.length} active · {d.done_count || completed.length} completed</div>

        {rejected.length > 0 && (
          <>
            <h3 style={{ color: '#DC2626' }}>⚠ Needs Fixing</h3>
            {rejected.map(o => (
              <div className="job-card fix" key={o.id}>
                <div>
                  <div className="job-task">{o.task_label || title(o.task)}</div>
                  <div className="job-meta">{o.render_count || 1} unit(s) · {payout(o.pilot_payout)} payout · Fix and resubmit ASAP to protect your rating.</div>
                </div>
                <div className="job-right">
                  <Link to={`/pilot/execute/${o.id}`} className="btn-fix">Fix &amp; Resubmit →</Link>
                </div>
              </div>
            ))}
          </>
        )}

        <h3>Active Jobs</h3>
        {active.length === 0 ? (
          <div className="empty"><h4>No active jobs right now</h4></div>
        ) : active.map(o => (
          <div className="job-card" key={o.id}>
            <div>
              <div className="job-task">{o.task_label || title(o.task)}</div>
              <div className="job-meta">{o.render_count || 1} unit(s) · {payout(o.pilot_payout)} payout · SLA: {o.deadline || 'ASAP'}</div>
            </div>
            <div className="job-right">
              <span className={`badge badge-${o.status || 'assigned'}`}>{title(o.status || 'assigned')}</span>
              <div><Link to={`/pilot/execute/${o.id}`} className="btn-gold">Execute Job →</Link></div>
            </div>
          </div>
        ))}

        <h3>Completed Jobs</h3>
        {completed.length === 0 ? (
          <div className="empty">No completed jobs yet.</div>
        ) : (
          <table className="ptable">
            <thead><tr><th>#</th><th>Task</th><th>Status</th><th>Payout</th></tr></thead>
            <tbody>
              {completed.map(o => (
                <tr key={o.id}>
                  <td><Link to={`/order/${o.id}`}>#{o.id}</Link></td>
                  <td>{o.task_label || title(o.task)}</td>
                  <td>{title(o.status)}</td>
                  <td style={{ fontWeight: 700, color: '#1B6B3A' }}>{payout(o.pilot_payout)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
