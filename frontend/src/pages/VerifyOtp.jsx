// Port of templates/verify_otp.html — WhatsApp OTP with countdown.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import OtpBoxes from '../components/OtpBoxes.jsx';
import { apiGet, apiPostForm } from '../api.js';

export default function VerifyOtp() {
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [secs, setSecs] = useState(600);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet('/verify-otp').then(r => {
      if (r.redirect && !r.phone) nav(r.redirect);
      else setPhone(r.phone || '');
    });
    const t = setInterval(() => setSecs(s => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (otp.length < 6) return;
    setBusy(true);
    const r = await apiPostForm('/verify-otp', { otp });
    setBusy(false);
    if (r.ok && r.redirect) {
      window.dispatchEvent(new Event('auth-changed'));
      nav(r.redirect);
    } else setFlash(r.flash || [{ category: 'error', message: r.error || 'Verification failed.' }]);
  }

  const m = Math.floor(secs / 60), s = String(secs % 60).padStart(2, '0');

  return (
    <AuthShell footerLinks={false} backHome={false}>
      <div className="auth-sub">Enter your OTP</div>
      <Flash messages={flash} />
      <div style={{ textAlign: 'center', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)', padding: '0.75rem', marginBottom: '0.5rem' }}>
        <small style={{ display: 'block', color: 'var(--gray-500)' }}>OTP sent to WhatsApp</small>
        <strong>+91 {phone}</strong>
      </div>
      <form onSubmit={submit}>
        <OtpBoxes value={otp} onChange={setOtp} />
        <button type="submit" className="btn btn-primary btn-full" disabled={busy || otp.length < 6}>Verify OTP →</button>
      </form>
      <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.85rem', color: 'var(--gray-500)' }}>
        {secs > 0
          ? <span>Resend in {m}:{s}</span>
          : <Link to="/login/phone" style={{ color: 'var(--navy)', fontWeight: 600 }}>Resend OTP</Link>}
      </div>
      <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.8125rem' }}>
        <Link to="/login/phone" style={{ color: 'var(--gray-400)' }}>← Change number</Link>
      </p>
    </AuthShell>
  );
}
