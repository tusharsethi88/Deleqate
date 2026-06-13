// Port of templates/order_success.html
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { apiGet } from '../api.js';

export default function OrderSuccess() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const id = params.get('id') || '';
  const [d, setD] = useState(null);

  useEffect(() => {
    apiGet(`/order/success?id=${id}`).then(r => {
      if (!r.ok && r.redirect) nav(r.redirect);
      else setD(r);
    });
  }, [id]);

  if (!d) return null;
  const ca = d.client_action;

  const Row = ({ icon, children }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.875rem' }}>{icon} <span>{children}</span></div>
  );

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--surface-low)', padding: '1.5rem' }}>
      <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)', padding: '3rem 2.5rem', maxWidth: 500, width: '100%', textAlign: 'center' }}>
        {ca === 'paid_upfront' ? (
          <>
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🎉</div>
            <h2 style={{ marginBottom: '0.5rem' }}>Order Confirmed!</h2>
            <p style={{ color: 'var(--gray-600)', marginBottom: '1.5rem' }}>
              Payment received for order <strong>#{d.order_id}</strong>. An AI Pilot will be assigned within{' '}
              <strong>15 minutes</strong> and your delivery is SLA-guaranteed.
            </p>
            <div style={{ background: 'var(--cream)', borderRadius: 'var(--radius-lg)', padding: '1.25rem', marginBottom: '2rem', textAlign: 'left' }}>
              <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--navy)', marginBottom: '0.75rem' }}>What happens next:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                <Row icon="✅"><strong>Payment confirmed</strong> — you're all set</Row>
                <Row icon="⚡">AI Pilot assigned within <strong>15 min</strong></Row>
                <Row icon="🎯">Delivery in under 2 hours, SLA guaranteed</Row>
                <Row icon="⬇">Download unlocked immediately on delivery</Row>
              </div>
            </div>
          </>
        ) : (
          <>
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>✅</div>
            <h2 style={{ marginBottom: '0.5rem' }}>Payment Confirmed!</h2>
            <p style={{ color: 'var(--gray-600)', marginBottom: '1.5rem' }}>
              {ca === 'pay_edit'
                ? <>Payment received for order <strong>#{d.order_id}</strong>. Your edit request has been sent to the pilot — they will revise and redeliver shortly.</>
                : <>Payment received for order <strong>#{d.order_id}</strong>. Your clean files are now unlocked and ready to download.</>}
            </p>
            <div style={{ background: 'var(--cream)', borderRadius: 'var(--radius-lg)', padding: '1.25rem', marginBottom: '2rem', textAlign: 'left' }}>
              <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--navy)', marginBottom: '0.75rem' }}>What happens next:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {ca === 'pay_edit' ? (
                  <>
                    <Row icon="✏️">Pilot is working on your revision</Row>
                    <Row icon="🔔">You'll be notified when the revised delivery is ready</Row>
                    <Row icon="⬇">Return to your orders to download when done</Row>
                  </>
                ) : (
                  <>
                    <Row icon="✅"><strong>Files unlocked</strong> — download now, no expiry</Row>
                    <Row icon="🔒">Clean originals, no watermark</Row>
                    <Row icon="🙏">Thanks for using Deleqate!</Row>
                  </>
                )}
              </div>
            </div>
          </>
        )}

        <Link to="/client/orders" className="btn btn-primary btn-full" style={{ marginBottom: '0.75rem' }}>
          {ca && ca !== 'pay_download' ? 'Track My Orders' : 'Go to My Orders & Download'}
        </Link>
        <Link to="/order" className="btn btn-outline btn-full">Place Another Order</Link>
        <Link to="/logout" className="btn btn-outline btn-full" style={{ marginTop: '0.75rem', background: 'none', border: '2px solid var(--gray-200)', color: 'var(--gray-600)' }}>Logout</Link>
      </div>
    </div>
  );
}
