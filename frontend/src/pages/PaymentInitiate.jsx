// Port of templates/payment_initiate.html — fetches PayU form fields from the
// backend, renders the hidden form and auto-submits to PayU after 1.5s.
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiGet } from '../api.js';

const css = `
.pi-card{background:var(--white);border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);padding:3rem 2.5rem;max-width:460px;width:100%;text-align:center;}
.pi-spinner{width:48px;height:48px;border:4px solid var(--gray-200);border-top-color:var(--gold);border-radius:50%;animation:pi-spin .9s linear infinite;margin:0 auto 1.5rem;}
@keyframes pi-spin{to{transform:rotate(360deg);}}
.pi-amount{font-size:2rem;font-weight:800;color:var(--navy);margin:.75rem 0 1.5rem;}
.pi-row{display:flex;justify-content:space-between;font-size:.82rem;color:var(--gray-500);padding:.4rem 0;border-bottom:1px solid var(--gray-100);}
.pi-row:last-child{border-bottom:none;}
.pi-box{background:var(--cream);border-radius:var(--radius-lg);padding:1rem 1.25rem;margin:1.25rem 0 2rem;text-align:left;}
.mode-badge{display:inline-block;border-radius:100px;font-size:.7rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:4px 14px;margin-bottom:.75rem;}
.mode-upfront{background:#EEF2FF;color:#4338CA;}
.mode-review{background:#F0FDF4;color:#15803D;}
.mode-edit{background:#FFFBEB;color:#B45309;}
`;

export default function PaymentInitiate() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const orderId = params.get('order_id');
  const [d, setD] = useState(null);
  const formRef = useRef(null);

  useEffect(() => {
    apiGet(`/payment/initiate?order_id=${orderId}`).then(r => {
      if (!r.ok) { nav(r.redirect || '/client/orders'); return; }
      setD(r);
    });
  }, [orderId]);

  // auto-submit to PayU 1.5s after form fields are ready (parity with template)
  useEffect(() => {
    if (!d) return;
    const t = setTimeout(() => formRef.current?.submit(), 1500);
    return () => clearTimeout(t);
  }, [d]);

  if (!d) return null;
  const ca = d.client_action;

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--surface-low)', padding: '1.5rem' }}>
      <style>{css}</style>
      <div className="pi-card">
        <div className="pi-spinner" />
        {ca === 'pay_upfront' ? (
          <>
            <span className="mode-badge mode-upfront">Upfront Payment</span>
            <h2 style={{ marginBottom: '0.25rem' }}>Confirm Your Order</h2>
            <p style={{ color: 'var(--gray-500)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Pay now to confirm your order. An AI Pilot will be assigned as soon as payment clears.
            </p>
          </>
        ) : ca === 'pay_edit' ? (
          <>
            <span className="mode-badge mode-edit">Pay &amp; Edit</span>
            <h2 style={{ marginBottom: '0.25rem' }}>Paying &amp; Submitting Edits</h2>
            <p style={{ color: 'var(--gray-500)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Your payment locks in the order. The pilot will act on your edit notes and redeliver.
            </p>
          </>
        ) : (
          <>
            <span className="mode-badge mode-review">Approve &amp; Download</span>
            <h2 style={{ marginBottom: '0.25rem' }}>Unlocking Your Files</h2>
            <p style={{ color: 'var(--gray-500)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Clean watermark-free files will be available for download immediately after payment.
            </p>
          </>
        )}

        <div className="pi-amount">₹{d.amount}</div>

        <div className="pi-box">
          <div className="pi-row"><span>Order</span><span><strong>#{d.order_id}</strong></span></div>
          <div className="pi-row"><span>Service</span><span>{d.productinfo}</span></div>
          <div className="pi-row"><span>Transaction ID</span><span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{d.txnid}</span></div>
        </div>

        <p style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginBottom: '1.5rem' }}>
          🔒 Secured by PayU · 256-bit SSL encryption
        </p>

        {/* Hidden PayU form — full-page POST to the gateway */}
        <form ref={formRef} action={d.payu_url} method="POST" style={{ display: 'none' }}>
          <input type="hidden" name="key" value={d.key} />
          <input type="hidden" name="txnid" value={d.txnid} />
          <input type="hidden" name="amount" value={d.amount} />
          <input type="hidden" name="productinfo" value={d.productinfo} />
          <input type="hidden" name="firstname" value={d.firstname} />
          <input type="hidden" name="email" value={d.email} />
          <input type="hidden" name="phone" value={d.phone} />
          <input type="hidden" name="surl" value={d.surl} />
          <input type="hidden" name="furl" value={d.furl} />
          <input type="hidden" name="hash" value={d.pay_hash} />
          <input type="hidden" name="service_provider" value="payu_paisa" />
          <input type="hidden" name="udf1" value="" />
          <input type="hidden" name="udf2" value="" />
          <input type="hidden" name="udf3" value="" />
          <input type="hidden" name="udf4" value="" />
          <input type="hidden" name="udf5" value="" />
        </form>

        <button onClick={() => formRef.current?.submit()} className="btn btn-primary" style={{ width: '100%' }}>
          Pay ₹{d.amount} Now →
        </button>
      </div>
    </div>
  );
}
