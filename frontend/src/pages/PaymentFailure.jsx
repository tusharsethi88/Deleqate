// Port of templates/payment_failure.html — backend redirects here with
// error/status/order_id in the query string.
import { Link, useSearchParams } from 'react-router-dom';

export default function PaymentFailure() {
  const [params] = useSearchParams();
  const error = params.get('error');
  const orderId = params.get('order_id');
  const supportWa = params.get('support_whatsapp') || '919999999999';

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--surface-low)', padding: '1.5rem' }}>
      <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)', padding: '3rem 2.5rem', maxWidth: 460, width: '100%', textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>❌</div>
        <h2 style={{ marginBottom: '0.5rem' }}>Payment Not Completed</h2>
        <p style={{ color: 'var(--gray-600)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
          No money was charged. You can try again — your order is saved.
        </p>
        {error && (
          <div style={{ background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 'var(--radius-lg)', padding: '1rem 1.25rem', margin: '1.25rem 0 2rem', fontSize: '0.875rem', color: '#c53030' }}>
            {error}
          </div>
        )}
        {orderId && (
          <p style={{ color: 'var(--gray-400)', fontSize: '0.8rem', marginBottom: '1.5rem' }}>Order #{orderId} · Status: pending</p>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {orderId && (
            <Link to={`/payment/initiate?order_id=${orderId}`} className="btn btn-primary">Try Payment Again</Link>
          )}
          <Link to="/client/orders" className="btn btn-outline">View My Orders</Link>
          <a href={`https://wa.me/${supportWa}?text=Hi%2C+I+had+a+payment+issue+for+Order+%23${orderId || ''}`}
            className="btn" style={{ background: 'var(--cream)', color: 'var(--navy)' }} target="_blank" rel="noreferrer">
            💬 WhatsApp Support
          </a>
        </div>
      </div>
    </div>
  );
}
