// Port of templates/reset_password_new.html.
// Clients reset a 4-digit PIN; pilots/admins reset an 8+ char password.
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiGet, apiPostForm } from '../api.js';

const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
const labels = ['Weak', 'Fair', 'Good', 'Strong'];

export default function ResetPasswordNew() {
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [role, setRole] = useState('client');
  const [pw1, setPw1] = useState('');
  const [pw2, setPw2] = useState('');
  const [busy, setBusy] = useState(false);

  const isClient = role === 'client';

  useEffect(() => {
    apiGet('/reset-password-new').then(r => {
      if (r.redirect) { nav(r.redirect); return; }
      if (r.role) setRole(r.role);
    });
  }, []);

  // password strength (pilots only)
  let score = 0;
  if (pw1.length >= 8) score++;
  if (/[A-Z]/.test(pw1)) score++;
  if (/[0-9]/.test(pw1)) score++;
  if (/[^A-Za-z0-9]/.test(pw1)) score++;

  const valid = isClient ? /^\d{4}$/.test(pw1) : pw1.length >= 8;

  const setDigits = (setter) => (e) => setter(e.target.value.replace(/\D/g, '').slice(0, 4));

  async function submit(e) {
    e.preventDefault();
    if (!valid || pw1 !== pw2) return;
    setBusy(true);
    const r = await apiPostForm('/reset-password-new', { password: pw1, password2: pw2 });
    setBusy(false);
    if (r.ok && r.redirect) nav(r.redirect);
    else {
      setFlash(r.flash || [{ category: 'error', message: r.error || 'Reset failed.' }]);
      if (r.redirect) nav(r.redirect);
    }
  }

  const pinStyle = { fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center' };

  return (
    <AuthShell footerLinks={false} backHome={false}>
      <div style={{ textAlign: 'center', fontSize: '2rem', margin: '1rem 0' }}>🔒</div>
      <div style={{ textAlign: 'center', fontWeight: 700, fontSize: '1.1rem', color: 'var(--navy)', marginBottom: '0.4rem' }}>
        {isClient ? 'Set a new PIN' : 'Set a new password'}
      </div>
      <div style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--gray-500)', marginBottom: '1.75rem' }}>
        {isClient ? 'Choose a 4-digit PIN you’ll use to sign in.' : 'Must be at least 8 characters.'}
      </div>
      <Flash messages={flash} />
      <form onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">{isClient ? 'New PIN' : 'New Password'}</label>
          {isClient ? (
            <input type="password" className="form-control" placeholder="••••" required maxLength={4} minLength={4}
              inputMode="numeric" autoFocus autoComplete="new-password" style={pinStyle}
              value={pw1} onChange={setDigits(setPw1)} />
          ) : (
            <>
              <input type="password" className="form-control" placeholder="Min 8 characters" required minLength={8}
                maxLength={128} autoFocus autoComplete="new-password" value={pw1} onChange={e => setPw1(e.target.value)} />
              <div style={{ background: 'var(--gray-200)', borderRadius: 2, height: 4, marginTop: '0.5rem' }}>
                <div style={{ height: 4, borderRadius: 2, transition: 'all .2s', width: `${score * 25}%`, background: colors[score - 1] || '#e5e7eb' }} />
              </div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: colors[score - 1] || 'var(--gray-400)' }}>
                {score > 0 ? labels[score - 1] : ''}
              </div>
            </>
          )}
        </div>
        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">{isClient ? 'Confirm PIN' : 'Confirm Password'}</label>
          <input type="password" className="form-control"
            placeholder={isClient ? '••••' : 'Repeat password'}
            required minLength={isClient ? 4 : 8} maxLength={isClient ? 4 : 128}
            inputMode={isClient ? 'numeric' : undefined} autoComplete="new-password"
            style={isClient ? pinStyle : undefined}
            value={pw2} onChange={isClient ? setDigits(setPw2) : (e => setPw2(e.target.value))} />
          {pw2 && (
            <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: pw1 === pw2 ? '#22c55e' : '#ef4444' }}>
              {pw1 === pw2 ? (isClient ? '✓ PINs match' : '✓ Passwords match') : (isClient ? '✗ PINs do not match' : '✗ Passwords do not match')}
            </div>
          )}
        </div>
        <button type="submit" disabled={busy || !valid || pw1 !== pw2}
          className="btn btn-primary btn-full" style={{ marginTop: '1.25rem' }}>
          {isClient ? 'Update PIN →' : 'Update Password →'}
        </button>
      </form>
    </AuthShell>
  );
}
