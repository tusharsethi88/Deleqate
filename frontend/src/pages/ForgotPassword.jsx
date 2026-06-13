// Port of templates/forgot_password.html
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiPostForm } from '../api.js';

export default function ForgotPassword() {
  const [params] = useSearchParams();
  const role = ['client', 'pilot', 'admin'].includes(params.get('role')) ? params.get('role') : 'client';
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const r = await apiPostForm(`/forgot-password?role=${role}`, { email, role });
    setBusy(false);
    if (r.ok && r.redirect) nav(r.redirect);
    else setFlash(r.flash || [{ category: 'error', message: r.error || 'Request failed.' }]);
  }

  return (
    <AuthShell footerLinks={false}>
      <div style={{ textAlign: 'center', fontSize: '2rem', margin: '1rem 0' }}>🔑</div>
      <div style={{ textAlign: 'center', fontWeight: 700, fontSize: '1.1rem', color: 'var(--navy)', marginBottom: '0.4rem' }}>Reset your password</div>
      <div style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--gray-500)', marginBottom: '1.5rem' }}>
        Enter your email and we'll send a 6-digit reset code.
      </div>
      <div style={{ textAlign: 'center' }}>
        {role === 'pilot'
          ? <span className="role-badge pilot">🚀 AI Pilot</span>
          : <span className="role-badge client">✦ Customer</span>}
      </div>
      <Flash messages={flash} />
      <form onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Email address</label>
          <input type="email" className="form-control" placeholder="you@email.com" required autoFocus
            autoComplete="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <button type="submit" disabled={busy} className="btn btn-full"
          style={{ marginTop: '1.25rem', background: role === 'pilot' ? '#4F46E5' : 'var(--gold)', color: '#fff' }}>
          Send Reset Code →
        </button>
      </form>
      <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
        Remembered it? <Link to={`/login?type=${role}`} style={{ color: 'var(--navy)', fontWeight: 600 }}>Sign in</Link>
      </p>
    </AuthShell>
  );
}
