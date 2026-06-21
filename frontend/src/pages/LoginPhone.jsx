// Port of templates/login_phone.html — client email + password login.
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiPostForm } from '../api.js';

function EyeOpen() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  );
}
function EyeOff() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

export default function LoginPhone() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get('next') || '';
  const [flash, setFlash] = useState([]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData();
    fd.append('email', email);
    fd.append('password', password);
    fd.append('website', '');   // honeypot
    const r = await apiPostForm(`/login/phone${next ? `?next=${encodeURIComponent(next)}` : ''}`, fd);
    setBusy(false);
    if (r.ok && r.redirect) {
      window.dispatchEvent(new Event('auth-changed'));
      nav(r.redirect.replace(/^https?:\/\/[^/]+/, ''));
    } else setFlash(r.flash || [{ category: 'error', message: r.error || 'Login failed.' }]);
  }

  return (
    <AuthShell footerLinks={false} backHome={false}>
      <div className="auth-sub">Sign in to place your order</div>
      <Flash messages={flash} />
      <form onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Email address</label>
          <input type="email" className="form-control" placeholder="you@example.com" required autoFocus
            autoComplete="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label className="form-label">Password</label>
          <div style={{ position: 'relative' }}>
            <input type={showPassword ? 'text' : 'password'} className="form-control" placeholder="Your password" required
              autoComplete="current-password" maxLength={128} value={password} onChange={e => setPassword(e.target.value)}
              style={{ paddingRight: '2.5rem' }} />
            <button type="button" onClick={() => setShowPassword(v => !v)}
              style={{ position: 'absolute', right: '0.65rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)', display: 'flex', alignItems: 'center', padding: 0 }}
              aria-label={showPassword ? 'Hide password' : 'Show password'} tabIndex={-1}>
              {showPassword ? <EyeOff /> : <EyeOpen />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={busy} className="btn btn-primary btn-full" style={{ marginTop: '1.25rem' }}>Sign In →</button>
      </form>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '1.25rem 0', color: 'var(--gray-400)', fontSize: '0.8rem' }}>
        <div style={{ flex: 1, height: 1, background: 'var(--gray-200)' }} />or<div style={{ flex: 1, height: 1, background: 'var(--gray-200)' }} />
      </div>
      <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
        Don't have an account? <Link to="/signup" style={{ color: 'var(--navy)', fontWeight: 700 }}>Sign Up</Link>
      </p>
      <p style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.8125rem' }}>
        <Link to="/" style={{ color: 'var(--gray-400)' }}>← Back to Deleqate</Link>
      </p>
    </AuthShell>
  );
}
