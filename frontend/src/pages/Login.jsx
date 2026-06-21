// Port of templates/login.html — client (phone+PIN) and pilot (email+password) login.
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiPostForm } from '../api.js';

const eyeBtnStyle = {
  position: 'absolute', right: '0', top: '50%', transform: 'translateY(-50%)',
  background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280',
  display: 'flex', alignItems: 'center', padding: '4px', zIndex: 2,
  lineHeight: 1,
};

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

export default function Login() {
  const [params] = useSearchParams();
  const lt = params.get('type') === 'pilot' ? 'pilot' : 'client';
  const next = params.get('next') || '';
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [busy, setBusy] = useState(false);

  // client fields
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  // pilot fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }, [lt]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData();
    fd.append('login_type', lt);
    fd.append('website', '');
    if (lt === 'client') { fd.append('phone', phone); fd.append('pin', pin); }
    else { fd.append('email', email); fd.append('password', password); }
    const r = await apiPostForm(`/login?type=${lt}${next ? `&next=${encodeURIComponent(next)}` : ''}`, fd);
    setBusy(false);
    if (r.ok && r.redirect) {
      window.dispatchEvent(new Event('auth-changed'));
      nav(r.redirect.replace(/^https?:\/\/[^/]+/, ''));
    } else {
      setFlash(r.flash || [{ category: 'error', message: r.error || 'Login failed.' }]);
    }
  }

  return (
    <AuthShell>
      <div className="auth-sub">Welcome back</div>
      <div style={{ textAlign: 'center' }}>
        {lt === 'pilot'
          ? <span className="role-badge pilot" style={{ display: 'inline-flex', alignItems: 'center' }}><i data-lucide="rocket" style={{ width: 13, height: 13, marginRight: 5 }}></i> AI Pilot Login</span>
          : <span className="role-badge client" style={{ display: 'inline-flex', alignItems: 'center' }}><i data-lucide="sparkles" style={{ width: 13, height: 13, marginRight: 5 }}></i> Customer Sign In</span>}
      </div>
      <Flash messages={flash} />

      {lt === 'pilot' ? (
        <form onSubmit={submit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" className="form-control" placeholder="pilot@email.com" required autoFocus
              autoComplete="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginTop: '0.75rem' }}>
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input type={showPassword ? 'text' : 'password'} className="form-control" placeholder="Your password" required
                autoComplete="current-password" maxLength={128} value={password} onChange={e => setPassword(e.target.value)}
                style={{ paddingRight: '2rem' }} />
              <button type="button" onClick={() => setShowPassword(v => !v)}
                style={eyeBtnStyle}
                aria-label={showPassword ? 'Hide password' : 'Show password'} tabIndex={-1}>
                {showPassword ? <EyeOff /> : <EyeOpen />}
              </button>
            </div>
          </div>
          <button type="submit" disabled={busy} className="btn btn-full"
            style={{ marginTop: '1rem', background: '#4F46E5', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>Sign In <i data-lucide="arrow-right" style={{ width: 14, height: 14 }}></i></button>
          <div style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--gray-400)' }}>
            Pilot accounts are set up by the admin only.
          </div>
        </form>
      ) : (
        <>
          <form onSubmit={submit}>
            <div className="form-group">
              <label className="form-label">Mobile Number</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--gray-600)', fontSize: '1rem', padding: '0.55rem 0.6rem', border: '1.5px solid var(--gray-200)', borderRadius: 'var(--radius-md)', background: 'var(--surface-low)', whiteSpace: 'nowrap' }}>+91</span>
                <input type="tel" className="form-control" placeholder="10-digit number" required autoFocus
                  maxLength={10} pattern="[6-9][0-9]{9}" inputMode="numeric" autoComplete="tel" style={{ flex: 1 }}
                  value={phone} onChange={e => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))} />
              </div>
            </div>
            <div className="form-group" style={{ marginTop: '0.75rem' }}>
              <label className="form-label">4-digit PIN</label>
              <div style={{ position: 'relative' }}>
                <input type={showPin ? 'text' : 'password'} className="form-control" placeholder="••••" required maxLength={4} minLength={4}
                  inputMode="numeric" autoComplete="current-password"
                  style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center', paddingRight: '2rem' }}
                  value={pin} onChange={e => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))} />
                <button type="button" onClick={() => setShowPin(v => !v)}
                  style={eyeBtnStyle}
                  aria-label={showPin ? 'Hide PIN' : 'Show PIN'} tabIndex={-1}>
                  {showPin ? <EyeOff /> : <EyeOpen />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={busy} className="btn btn-full"
              style={{ marginTop: '1rem', background: 'var(--gold)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>Sign In <i data-lucide="arrow-right" style={{ width: 14, height: 14 }}></i></button>
          </form>
          <div style={{ textAlign: 'center', marginTop: '0.85rem', fontSize: '0.85rem' }}>
            <Link to="/forgot-password?role=client" style={{ color: 'var(--navy)', textDecoration: 'none', fontWeight: 600 }}>Forgot PIN?</Link>
          </div>
          <div style={{ textAlign: 'center', marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
            New here? <Link to="/signup" style={{ color: 'var(--navy)', textDecoration: 'none', fontWeight: 700 }}>Create Account</Link>
          </div>
        </>
      )}

      <div style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--gray-400)' }}>
        {lt === 'pilot'
          ? <><Link to="/login?type=client" style={{ color: 'var(--navy)', fontWeight: 600 }}>Customer Sign In</Link></>
          : <>Are you a Pilot? <Link to="/login?type=pilot" style={{ color: 'var(--navy)', fontWeight: 600 }}>Pilot Login</Link></>}
      </div>
    </AuthShell>
  );
}
