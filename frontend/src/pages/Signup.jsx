// Port of templates/signup.html — phone + name + 4-digit PIN + math captcha.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiGet, apiPostForm } from '../api.js';

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

export default function Signup() {
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [captchaQ, setCaptchaQ] = useState('…');
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ name: '', phone: '', email: '', pin: '', pin_confirm: '', captcha_answer: '' });
  const [showPin, setShowPin] = useState(false);
  const [showPinConfirm, setShowPinConfirm] = useState(false);

  useEffect(() => {
    apiGet('/signup').then(r => {
      if (r.redirect) nav(r.redirect);
      else {
        setCaptchaQ(r.captcha_question || '');
        setTimeout(() => {
          if (window.lucide) window.lucide.createIcons();
        }, 50);
      }
    });
  }, []);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setDigits = (k, n) => (e) => setF({ ...f, [k]: e.target.value.replace(/\D/g, '').slice(0, n) });

  async function submit(e) {
    e.preventDefault();
    if (!/^\d{4}$/.test(f.pin)) { alert('PIN must be exactly 4 digits.'); return; }
    if (f.pin !== f.pin_confirm) { alert('PINs do not match. Please re-enter.'); return; }
    setBusy(true);
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => fd.append(k, v));
    fd.append('website', '');   // honeypot
    const r = await apiPostForm('/signup', fd);
    setBusy(false);
    if (r.ok && r.redirect) {
      window.dispatchEvent(new Event('auth-changed'));
      nav(r.redirect);
    } else {
      setFlash(r.flash || [{ category: 'error', message: r.error || 'Sign-up failed.' }]);
      if (r.captcha_question) setCaptchaQ(r.captcha_question);
      setF({ ...f, captcha_answer: '' });
    }
  }

  return (
    <AuthShell maxWidth="440px">
      <div style={{ textAlign: 'center', marginBottom: '1.25rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>Create your account</div>
      <div style={{ textAlign: 'center' }}><span className="role-badge client" style={{ display: 'inline-flex', alignItems: 'center' }}><i data-lucide="sparkles" style={{ width: 13, height: 13, marginRight: 5 }}></i> Customer Sign Up</span></div>
      <Flash messages={flash} />

      <form onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Full Name <span style={{ color: 'var(--gold)' }}>*</span></label>
          <input type="text" className="form-control" placeholder="Your full name" required autoFocus maxLength={100}
            value={f.name} onChange={set('name')} />
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Mobile Number <span style={{ color: 'var(--gold)' }}>*</span></label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--gray-600)', fontSize: '1rem', padding: '0.55rem 0.5rem', border: '1.5px solid var(--gray-200)', borderRadius: 'var(--radius-md)', background: 'var(--surface-low)' }}>+91</span>
            <input type="tel" className="form-control" placeholder="10-digit number" required maxLength={10}
              pattern="[6-9][0-9]{9}" inputMode="numeric" style={{ flex: 1 }}
              value={f.phone} onChange={setDigits('phone', 10)} />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.3rem' }}>Indian mobile number — used to sign in.</div>
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Email Address <span style={{ color: 'var(--gold)' }}>*</span></label>
          <input type="email" className="form-control" placeholder="you@email.com" required maxLength={254}
            autoComplete="email" value={f.email} onChange={set('email')} />
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.3rem' }}>Used to recover your PIN if you forget it.</div>
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Set a 4-digit PIN <span style={{ color: 'var(--gold)' }}>*</span></label>
          <div style={{ position: 'relative' }}>
            <input type={showPin ? 'text' : 'password'} className="form-control" placeholder="••••" required maxLength={4} minLength={4}
              inputMode="numeric" autoComplete="new-password"
              style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center', paddingRight: '2.5rem' }}
              value={f.pin} onChange={setDigits('pin', 4)} />
            <button type="button" onClick={() => setShowPin(v => !v)}
              style={{ position: 'absolute', right: '0.65rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)', display: 'flex', alignItems: 'center', padding: 0 }}
              aria-label={showPin ? 'Hide PIN' : 'Show PIN'} tabIndex={-1}>
              {showPin ? <EyeOff /> : <EyeOpen />}
            </button>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.3rem' }}>You'll use this PIN every time you sign in.</div>
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Confirm PIN <span style={{ color: 'var(--gold)' }}>*</span></label>
          <div style={{ position: 'relative' }}>
            <input type={showPinConfirm ? 'text' : 'password'} className="form-control" placeholder="••••" required maxLength={4} minLength={4}
              inputMode="numeric" autoComplete="new-password"
              style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center', paddingRight: '2.5rem' }}
              value={f.pin_confirm} onChange={setDigits('pin_confirm', 4)} />
            <button type="button" onClick={() => setShowPinConfirm(v => !v)}
              style={{ position: 'absolute', right: '0.65rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)', display: 'flex', alignItems: 'center', padding: 0 }}
              aria-label={showPinConfirm ? 'Hide PIN' : 'Show PIN'} tabIndex={-1}>
              {showPinConfirm ? <EyeOff /> : <EyeOpen />}
            </button>
          </div>
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Quick Check <span style={{ color: 'var(--gold)' }}>*</span></label>
          <div className="captcha-box">
            <span className="captcha-q">{captchaQ} = ?</span>
            <input type="number" className="form-control" placeholder="Answer" required inputMode="numeric"
              min={0} max={99} style={{ width: '5.5rem' }}
              value={f.captcha_answer} onChange={set('captcha_answer')} />
          </div>
        </div>

        <button type="submit" disabled={busy} className="btn btn-full"
          style={{ marginTop: '1.25rem', background: 'var(--gold)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
          Create Account <i data-lucide="arrow-right" style={{ width: 14, height: 14 }}></i>
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
        Already have an account? <Link to="/login?type=client" style={{ color: 'var(--navy)', fontWeight: 600 }}>Sign In</Link>
      </p>
    </AuthShell>
  );
}
