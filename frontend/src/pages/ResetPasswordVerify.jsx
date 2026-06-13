// Port of templates/reset_password_verify.html
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell, { Flash } from '../components/AuthShell.jsx';
import OtpBoxes from '../components/OtpBoxes.jsx';
import { apiPostForm } from '../api.js';

export default function ResetPasswordVerify() {
  const [params] = useSearchParams();
  const email = params.get('email') || '';
  const role = ['client', 'pilot', 'admin'].includes(params.get('role')) ? params.get('role') : 'client';
  const nav = useNavigate();
  const [flash, setFlash] = useState([]);
  const [otp, setOtp] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (otp.length < 6) return;
    setBusy(true);
    const r = await apiPostForm(`/reset-password-verify?email=${encodeURIComponent(email)}&role=${role}`,
      { otp, email, role });
    setBusy(false);
    if (r.ok && r.redirect) nav(r.redirect);
    else setFlash(r.flash || [{ category: 'error', message: r.error || 'Verification failed.' }]);
  }

  return (
    <AuthShell footerLinks={false} backHome={false}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', margin: '1rem 0' }}>📧</div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--navy)', marginBottom: '0.4rem' }}>Enter your reset code</div>
        <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)', marginBottom: '0.25rem' }}>We sent a 6-digit code to</div>
        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '1.25rem' }}>{email}</div>
        <Flash messages={flash} />
        <form onSubmit={submit}>
          <OtpBoxes value={otp} onChange={setOtp} />
          <button type="submit" disabled={busy || otp.length < 6} className="btn btn-primary btn-full">Verify Code →</button>
        </form>
        <p style={{ marginTop: '1.25rem', fontSize: '0.8rem', color: 'var(--gray-400)' }}>
          Didn't receive it? Check spam or{' '}
          <Link to={`/forgot-password?role=${role}`} style={{ color: 'var(--navy)', fontWeight: 600 }}>try again</Link>.
        </p>
      </div>
    </AuthShell>
  );
}
