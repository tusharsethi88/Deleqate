// Shared auth-page layout: the .auth-box card, logo, flash alerts and
// footer links — same markup/styles as the original templates.
import { Link } from 'react-router-dom';

export function authStyles() {
  return `
  .auth-body{display:flex;align-items:center;justify-content:center;min-height:100vh;background:var(--surface-low);}
  .auth-box{background:var(--white);border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);padding:2.5rem;width:100%;max-width:420px;margin:1rem;}
  .auth-logo{display:flex;justify-content:center;margin-bottom:0.5rem;}
  .auth-logo img, .auth-logo video{height:94px;width:auto;display:block;mix-blend-mode:multiply;}
  .auth-sub{text-align:center;font-size:0.875rem;color:var(--gray-500);margin-bottom:1.25rem;}
  .role-badge{display:inline-flex;align-items:center;gap:0.4rem;border-radius:20px;padding:5px 14px;font-size:0.8rem;font-weight:700;letter-spacing:0.03em;margin-bottom:1.5rem;}
  .role-badge.client{background:var(--gold-pale);color:var(--gold-dark);border:1.5px solid var(--gold-container);}
  .role-badge.pilot{background:#EEF2FF;color:#3730A3;border:1.5px solid #C7D2FE;}
  .captcha-box{display:flex;align-items:center;gap:0.75rem;background:var(--surface-low);border-radius:var(--radius-md);padding:0.6rem 1rem;margin-bottom:0.25rem;}
  .captcha-q{font-size:1.1rem;font-weight:700;color:var(--navy);min-width:60px;}
  @media(max-width:480px){
    .auth-body{align-items:flex-start;padding-top:2rem;}
    .auth-box{padding:1.5rem 1.125rem !important;margin:.75rem !important;}
    .auth-logo img, .auth-logo video{height:78px;}
  }
  .auth-box .form-control,.auth-box input[type=email],.auth-box input[type=password],
  .auth-box input[type=tel],.auth-box input[type=text],.auth-box input[type=number]{font-size:1rem !important;}
  input[type=password]::-ms-reveal{display:none!important;}
  input[type=password]::-webkit-contacts-auto-fill-button{visibility:hidden!important;}
  input[type=password]::-webkit-credentials-auto-fill-button{visibility:hidden!important;}
  `;
}

export function Flash({ messages }) {
  if (!messages || !messages.length) return null;
  return messages.map((m, i) => {
    const cat = m.category === 'error' ? 'danger' : (m.category === 'success' ? 'success' : 'info');
    return <div key={i} className={`alert alert-${cat}`}>{m.message}</div>;
  });
}

export default function AuthShell({ children, maxWidth, footerLinks = true, backHome = true }) {
  return (
    <div className="auth-body">
      <style>{authStyles()}</style>
      <div className="auth-box" style={maxWidth ? { maxWidth } : undefined}>
        <div className="auth-logo"><img src="/img/logo.png" alt="Delegate" /></div>
        {children}
        {backHome && (
          <Link to="/" className="btn btn-full"
            style={{ marginTop: '0.75rem', background: 'none', border: '2px solid var(--gray-200)', color: 'var(--gray-600)' }}>
            &#8592; Back to Homepage
          </Link>
        )}
        {footerLinks && (
          <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.72rem', display: 'flex', justifyContent: 'center', gap: '0.9rem', flexWrap: 'wrap' }}>
            <Link to="/terms" style={{ color: 'var(--gray-500)' }}>Terms</Link>
            <Link to="/privacy" style={{ color: 'var(--gray-500)' }}>Privacy</Link>
            <Link to="/refund-policy" style={{ color: 'var(--gray-500)' }}>Refunds</Link>
            <Link to="/about" style={{ color: 'var(--gray-500)' }}>About</Link>
          </div>
        )}
      </div>
    </div>
  );
}
