// Port of templates/admin_login.html — secret admin login (/dq-control-7x9k).
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiPostForm } from '../api.js';

const css = `
.adl-body{display:flex;align-items:center;justify-content:center;min-height:100vh;background:#f8fafc;font-family:'Inter',sans-serif;}
.adl-box{background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);padding:2.5rem;width:100%;max-width:380px;}
.adl-logo{display:flex;justify-content:center;margin-bottom:2rem;}
.adl-logo img, .adl-logo video{height:94px;width:auto;display:block;mix-blend-mode:multiply;}
.adl-box label{display:block;font-size:0.8rem;font-weight:600;color:#6b7280;margin-bottom:0.3rem;margin-top:1rem;}
.adl-box input{width:100%;padding:0.6rem 0.9rem;border:1.5px solid #e5e7eb;border-radius:8px;font-size:1rem;outline:none;transition:border-color 0.15s;box-sizing:border-box;}
.adl-box input:focus{border-color:#C5A028;}
.adl-btn{width:100%;margin-top:1.5rem;padding:0.65rem;background:#1b1c1c;color:#fff;border:none;border-radius:8px;font-size:0.9375rem;font-weight:600;cursor:pointer;transition:background 0.2s;}
.adl-btn:hover{background:#2e2e2e;}
.adl-alert{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;border-radius:6px;padding:0.6rem 0.9rem;font-size:0.875rem;margin-bottom:1rem;}
input[type=password]::-ms-reveal{display:none!important;}
input[type=password]::-webkit-contacts-auto-fill-button{visibility:hidden!important;}
input[type=password]::-webkit-credentials-auto-fill-button{visibility:hidden!important;}
`;

function EyeOpen() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  );
}
function EyeOff() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

export default function AdminLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    const fd = new FormData();
    fd.append('email', email);
    fd.append('password', password);
    fd.append('website', '');
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
        <div className="adl-logo"><video src="/img/logo.mp4" autoPlay loop muted playsInline /></div>
        {error && <div className="adl-alert">{error}</div>}
        <form onSubmit={submit}>
          <input type="text" name="website" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />
          <label>Email</label>
          <input type="email" required autoFocus autoComplete="email" maxLength={254}
            value={email} onChange={e => setEmail(e.target.value)} />
          <label>Password</label>
          <div style={{ position: 'relative' }}>
            <input type={showPassword ? 'text' : 'password'} required autoComplete="current-password" maxLength={128}
              value={password} onChange={e => setPassword(e.target.value)}
              style={{ paddingRight: '2.5rem' }} />
            <button type="button" onClick={() => setShowPassword(v => !v)}
              style={{ position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#374151', display: 'flex', alignItems: 'center', padding: '4px', zIndex: 2 }}
              aria-label={showPassword ? 'Hide password' : 'Show password'} tabIndex={-1}>
              {showPassword ? <EyeOff /> : <EyeOpen />}
            </button>
          </div>
          <button type="submit" className="adl-btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
        </form>
        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.8rem' }}>
          <Link to="/forgot-password?role=admin" style={{ color: '#6b7280', textDecoration: 'underline' }}>Forgot password?</Link>
        </p>
      </div>
    </div>
  );
}
