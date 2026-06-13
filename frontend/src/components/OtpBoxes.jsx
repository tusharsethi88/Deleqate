// 6-digit OTP input with auto-advance / backspace / paste — same behavior
// as the inline JS in verify_otp.html and reset_password_verify.html.
import { useRef } from 'react';

const otpCss = `
.otp-inputs{display:flex;gap:0.5rem;justify-content:center;margin:1rem 0 1.25rem;}
.otp-inputs input{width:2.6rem;height:3.1rem;text-align:center;font-size:1.4rem;font-weight:700;
  border:1.5px solid var(--gray-200);border-radius:var(--radius-md);}
.otp-inputs input:focus{border-color:var(--gold);outline:none;}
`;

export default function OtpBoxes({ value, onChange }) {
  const refs = useRef([]);
  const digits = (value || '').padEnd(6).slice(0, 6).split('');

  function setDigit(i, ch) {
    const arr = (value || '').padEnd(6, ' ').slice(0, 6).split('');
    arr[i] = ch;
    onChange(arr.join('').replace(/\s/g, ''));
  }

  return (
    <div className="otp-inputs">
      <style>{otpCss}</style>
      {[0, 1, 2, 3, 4, 5].map(i => (
        <input key={i} type="text" maxLength={1} inputMode="numeric" pattern="[0-9]"
          autoFocus={i === 0}
          ref={el =>

 (refs.current[i] = el)}
          value={digits[i]?.trim() || ''}
          onChange={e => {
            const ch = e.target.value.replace(/\D/g, '').slice(-1);
            setDigit(i, ch || ' ');
            if (ch && i < 5) refs.current[i + 1]?.focus();
          }}
          onKeyDown={e => {
            if (e.key === 'Backspace' && !digits[i]?.trim() && i > 0) refs.current[i - 1]?.focus();
          }}
          onPaste={e => {
            e.preventDefault();
            const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
            onChange(paste);
            refs.current[Math.min(paste.length, 5)]?.focus();
          }} />
      ))}
    </div>
  );
}
