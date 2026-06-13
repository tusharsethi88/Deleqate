// Port of templates/admin_login.html — secret admin login (/dq-control-7x9k).
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiPostForm } from '../api.js';

const css = `
.adl-body{display:flex;align-items:center;justify-content:center;min-height:100vh;background:#f8fafc;font-family:'Inter',sans-serif;}
.adl-box{background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);padding:2.5rem;width:100%;max-width:380px;}
.adl-logo{font-size:1.25rem;font-weight:800;color:#1b1c1c;text-align:center;margin-bottom:2rem;letter-spacing:-0.02em;}
.adl-logo span{color:#C5A028;}
.adl-box label{display:block;font-size:0.8rem;font-weight:600;color:#6b7280;margin-bottom:0.3rem;margin-top:1rem;}
.adl-box input{width:100%;padding:0.6rem 0.9rem;border:1.5px solid #e5e7eb;border-radius:8px;font-size:1rem;outline:none;transition:border-color 0.15s;}
.adl-box input:focus{border-color:#C5A028;}
.adl-btn{width:100%;margin-top:1.5rem;padding:0.65rem;background:#1b1c1c;color:#fff;border:none;border-radius:8px;font-size:0.9375rem;font-weight:600;cursor:pointer;transition:background 0.2s;}
.adl-btn:hover{background:#2e2e2e;}
.adl-alert{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;border-radius:6px;padding:0.6rem 0.9rem;font-size:0.875rem;margin-bottom:1rem;}
`;

export default function AdminLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    const fd = new FormData();
    fd.append('email', email);
    fd.append('password', password);
    fd.append('website', '');   // honeypot
    const r = await apiPostForm('/dq-control-7x9k', fd);
    setBusy(false);
    if (r.ok && r.redirect) {
      window.dispatchEvent(new Event('auth-changed'));
      nav(r.redirect.replace(/^https?:\/\/[^/]+/, ''));
    } else {
      setError((r.flash && r.flash[0] && r.flash[0].message) || r.error || 'Invalid credentials.');
    }
  }

  return (
    <div className="adl-body">
      <style>{css}</style>
      <div className="adl-box">
        <div className="adl-logo">Dele<span>qate</span></div>
        {error && <div className="adl-alert">{error}</div>}
        <form onSubmit={submit}>
          <input type="text" name="website" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />
          <label>Email</label>
          <input type="email" required autoFocus autoComplete="email" maxLength={254}
            value={email} onChange={e => setEmail(e.target.value)} />
          <label>Password</label>
          <input type="password" required autoComplete="current-password" maxLength={128}
            value={password} onChange={e => setPassword(e.target.value)} />
          <button type="submit" className="adl-btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
        </form>
        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.8rem' }}>
          <Link to="/forgot-password?role=admin" style={{ color: '#6b7280', textDecoration: 'underline' }}>Forgot password?</Link>
        </p>
      </div>
    </div>
  );
}
