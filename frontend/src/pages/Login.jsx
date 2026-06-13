// Port of templates/login.html — client (phone+PIN) and pilot (email+password) login.
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiPostForm } from '../api.js';

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
  // pilot fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData();
    fd.append('login_type', lt);
    fd.append('website', '');           // honeypot stays empty
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
          ? <span className="role-badge pilot">🚀 AI Pilot Login</span>
          : <span className="role-badge client">✦ Customer Sign In</span>}
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
            <input type="password" className="form-control" placeholder="Your password" required
              autoComplete="current-password" maxLength={128} value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <button type="submit" disabled={busy} className="btn btn-full"
            style={{ marginTop: '1rem', background: '#4F46E5', color: '#fff' }}>Sign In →</button>
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
              <input type="password" className="form-control" placeholder="●●●●" required maxLength={4} minLength={4}
                inputMode="numeric" autoComplete="current-password"
                style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center' }}
                value={pin} onChange={e => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))} />
            </div>
            <button type="submit" disabled={busy} className="btn btn-full"
              style={{ marginTop: '1rem', background: 'var(--gold)', color: '#fff' }}>Sign In →</button>
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
          ? <>Placing an order? <Link to="/login?type=client" style={{ color: 'var(--navy)', fontWeight: 600 }}>Customer Sign In</Link></>
          : <>Are you a Pilot? <Link to="/login?type=pilot" style={{ color: 'var(--navy)', fontWeight: 600 }}>Pilot Login</Link></>}
      </div>
    </AuthShell>
  );
}
