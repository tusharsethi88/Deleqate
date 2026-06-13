// Port of templates/signup.html — phone + name + 4-digit PIN + math captcha.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import { apiGet, apiPostForm } from '../api.js';

export default function Signup() {
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [captchaQ, setCaptchaQ] = useState('…');
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ name: '', phone: '', email: '', pin: '', pin_confirm: '', captcha_answer: '' });

  useEffect(() => {
    apiGet('/signup').then(r => {
      if (r.redirect) nav(r.redirect);
      else setCaptchaQ(r.captcha_question || '');
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
      <div style={{ textAlign: 'center' }}><span className="role-badge client">✦ Customer Sign Up</span></div>
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
          <input type="password" className="form-control" placeholder="••••" required maxLength={4} minLength={4}
            inputMode="numeric" autoComplete="new-password"
            style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center' }}
            value={f.pin} onChange={setDigits('pin', 4)} />
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.3rem' }}>You'll use this PIN every time you sign in.</div>
        </div>

        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label className="form-label">Confirm PIN <span style={{ color: 'var(--gold)' }}>*</span></label>
          <input type="password" className="form-control" placeholder="••••" required maxLength={4} minLength={4}
            inputMode="numeric" autoComplete="new-password"
            style={{ fontSize: '1.5rem', letterSpacing: '0.4em', textAlign: 'center' }}
            value={f.pin_confirm} onChange={setDigits('pin_confirm', 4)} />
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
          style={{ marginTop: '1.25rem', background: 'var(--gold)', color: '#fff' }}>
          Create Account →
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.875rem', color: 'var(--gray-500)' }}>
        Already have an account? <Link to="/login?type=client" style={{ color: 'var(--navy)', fontWeight: 600 }}>Sign In</Link>
      </p>
    </AuthShell>
  );
}
