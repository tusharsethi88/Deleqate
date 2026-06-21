// Port of templates/policy.html — About / Terms / Privacy / Refund / Shipping.
// Content embedded here (backend policy_data returns only title/desc/whatsapp).
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiGet } from '../api.js';

const css = `
.policy-wrap{max-width:820px;margin:0 auto;padding:2.5rem 1.5rem 4rem;}
.policy-card{background:#fff;border:1px solid var(--gray-200);border-radius:14px;padding:2.5rem;box-shadow:0 1px 6px rgba(26,58,92,0.06);}
.policy-card h1{font-family:var(--font-display);font-size:1.75rem;color:var(--navy);margin-bottom:0.4rem;}
.policy-updated{font-size:0.8rem;color:var(--gray-500);margin-bottom:1.75rem;}
.policy-card h2{font-size:1.05rem;color:var(--navy);margin:1.75rem 0 0.5rem;}
.policy-card p,.policy-card li{font-size:0.9375rem;color:var(--gray-600);line-height:1.7;}
.policy-card ul{padding-left:1.25rem;margin:0.5rem 0;}
.policy-legal{margin-top:2rem;padding-top:1.25rem;border-top:1px solid var(--gray-200);font-size:0.85rem;color:var(--gray-500);}
.policy-nav{display:flex;gap:1.25rem;flex-wrap:wrap;margin:1.5rem 0 0;font-size:0.85rem;}
.policy-nav a{color:var(--navy);font-weight:600;}
@media(max-width:600px){.policy-card{padding:1.5rem;}}
`;

const Mail = () => <a href="mailto:support@deleqate.com">support@deleqate.com</a>;

function Body({ page, wa }) {
  switch (page) {
    case 'about':
      return (
        <>
          <h1>About Deleqate</h1>
          <div className="policy-updated">Who we are and what we do</div>
          <p>Deleqate is an AI-powered services platform operated by <strong>Deleqate, a sole proprietorship firm</strong>.</p>
          <p>Most businesses know AI can produce great creative work — but don't have the time to learn the tools, or the appetite to buy half a dozen subscriptions. Deleqate solves that. <em>You don't need to learn a single AI tool. Just Deleqate it.</em></p>
          <h2>What we deliver</h2>
          <p>We offer 12 fixed-price digital creative services across four areas:</p>
          <ul>
            <li><strong>Real estate</strong> — virtual staging of room photos (₹799 for 4 rooms), 30-second property marketing reels (₹1,200), and property social media card packs (₹499).</li>
            <li><strong>E-commerce</strong> — product photo background cleanup (from ₹79/image), marketplace listing creation (₹199/product), and product lifestyle mockups (₹299/image).</li>
            <li><strong>Business visual content</strong> — Instagram carousel design (₹649), brand demo videos (₹1,249), and AI professional headshots (₹399).</li>
            <li><strong>Brand &amp; personal</strong> — brand starter kits (₹1,999), restaurant/business menu design (₹799), and podcast highlight reels (₹649).</li>
          </ul>
          <h2>How it works</h2>
          <p>You place an order online with your photos and brief, at a fixed price shown upfront. A vetted AI specialist (we call them <strong>Pilots</strong>) executes your task following our standardised, quality-controlled workflow. Every deliverable passes a structured quality check before it reaches you. On your first order you review a watermarked preview before paying anything; your final files unlock on payment, and revisions are covered by edit credits. Typical delivery is within 1–6 hours depending on the task.</p>
          <h2>Contact us</h2>
          <p>Email: <Mail /><br />Phone/WhatsApp: +{wa}<br />Support hours: 10AM–10PM IST, all days</p>
        </>
      );
    case 'terms':
      return (
        <>
          <h1>Terms and Conditions</h1>
          <div className="policy-updated">Last updated: 11 June 2026</div>
          <p>These Terms and Conditions ("Terms") govern your use of www.deleqate.com (the "Website") and the services offered on it, operated by <strong>Deleqate, a sole proprietorship firm</strong> ("Deleqate", "we", "us"). By using the Website or placing an order, you agree to these Terms.</p>
          <h2>1. Services</h2>
          <p>Deleqate provides fixed-price digital creative services, including virtual staging of property images, property marketing reels, property social media assets, product photo background cleanup, marketplace product listings, product lifestyle mockups, Instagram carousel design, brand demo videos, AI professional headshots, brand starter kits, menu design and podcast highlight reels. All deliverables are digital files delivered through your account dashboard. Tasks are executed by vetted specialists ("Pilots") under our standardised workflows and quality checks.</p>
          <h2>2. Accounts</h2>
          <p>You must provide accurate information when creating an account. You are responsible for maintaining the confidentiality of your login credentials (including your PIN/OTP) and for all activity under your account.</p>
          <h2>3. Orders and pricing</h2>
          <p>Prices are displayed in Indian Rupees (INR) and are fixed per task as shown at the time of ordering (currently ranging from ₹79 to ₹1,999 depending on the service). The payable amount is calculated by us at checkout. Promotional pricing may change without notice, but never for an order already placed.</p>
          <h2>4. Payment</h2>
          <p>Payments are processed securely through PayU. On your first order, payment is collected after you review a watermarked preview of your deliverable; from your second order onwards, payment is collected upfront at checkout. Final, unwatermarked files are unlocked after successful payment, or on acceptance where a confirmed payment is already on file. We never store your card, UPI or banking details.</p>
          <h2>5. Revisions and edit credits</h2>
          <p>Eligible orders include free edit credits granted on your first successful payment. Additional credits may be purchased (currently ₹300 for 1 credit, ₹500 for 3). One credit is consumed per revision request. Revisions are scoped to the original brief — a change of brief constitutes a new order.</p>
          <h2>6. Content you upload</h2>
          <p>You confirm that you own, or have permission to use, all photos, floor plans, audio, logos and other material you upload, and that they contain nothing unlawful. You grant us a limited licence to process this material solely to fulfil your order, including sharing it with the Pilot assigned to your task.</p>
          <h2>7. Intellectual property</h2>
          <p>Upon full payment, ownership of the final deliverable transfers to you. We may showcase anonymised before/after samples for marketing unless you ask us not to in writing.</p>
          <h2>8. Service levels</h2>
          <p>Typical delivery is within 1–6 hours of order confirmation depending on the task; complex orders may take up to 24–48 hours. These are targets, not guarantees. Where we cannot deliver, you are protected by our Refund &amp; Cancellation Policy.</p>
          <h2>9. Acceptable use</h2>
          <p>You must not misuse the Website, attempt to access other users' data, or upload malicious files. We may suspend accounts that violate these Terms.</p>
          <h2>10. Limitation of liability</h2>
          <p>Our total liability for any claim relating to an order is limited to the amount you paid for that order. We are not liable for indirect or consequential losses.</p>
          <h2>11. Governing law</h2>
          <p>These Terms are governed by the laws of India.</p>
          <h2>12. Contact</h2>
          <p>Questions about these Terms: <Mail /> or +{wa}.</p>
        </>
      );
    case 'privacy':
      return (
        <>
          <h1>Privacy Policy</h1>
          <div className="policy-updated">Last updated: 11 June 2026</div>
          <p>This Privacy Policy explains how <strong>Deleqate, a sole proprietorship firm</strong> ("we", "us"), collects and uses your information when you use www.deleqate.com.</p>
          <h2>1. Information we collect</h2>
          <ul>
            <li><strong>Account data:</strong> name, mobile number, email address and a hashed PIN/password.</li>
            <li><strong>Order data:</strong> the photos, floor plans, product images, audio files and instructions you upload, and the deliverables we create for you.</li>
            <li><strong>Payment data:</strong> transaction references from our payment processor PayU — we never store your card, UPI or bank details.</li>
            <li><strong>Technical data:</strong> IP address and basic device information, used for security and rate limiting.</li>
          </ul>
          <h2>2. How we use it</h2>
          <p>To create and manage your account, fulfil your orders, process payments, provide customer support (including via WhatsApp where you contact us there), prevent fraud and abuse, and improve the service. We do not sell your personal data.</p>
          <h2>3. Sharing</h2>
          <p>Your order files are visible only to you, the vetted specialist assigned to your order, and our administrators. Payment information is shared with PayU solely to process your transaction. We disclose data to authorities only where required by law.</p>
          <h2>4. Storage and security</h2>
          <p>Data is stored on secured servers. Passwords and PINs are stored as cryptographic hashes. Access to uploaded files and deliverables is restricted to authenticated, authorised users only.</p>
          <h2>5. Retention</h2>
          <p>Order files and account data are retained while your account is active. You may request deletion of your account and associated files at any time by emailing us.</p>
          <h2>6. Cookies</h2>
          <p>We use only essential session cookies required for login and security (CSRF protection). We do not use advertising or third-party tracking cookies.</p>
          <h2>7. Your rights</h2>
          <p>You may request access to, correction of, or deletion of your personal data by writing to <Mail />. We respond within 30 days.</p>
          <h2>8. Grievance contact</h2>
          <p>Grievance Officer: Abhimanyu Dabas · <Mail /> · +{wa}</p>
        </>
      );
    case 'refund':
      return (
        <>
          <h1>Refund &amp; Cancellation Policy</h1>
          <div className="policy-updated">Last updated: 11 June 2026</div>
          <p>This policy applies to all orders placed on www.deleqate.com, operated by <strong>Deleqate, a sole proprietorship firm</strong>.</p>
          <h2>1. Cancellation before work begins</h2>
          <p>You may cancel an order free of charge any time before a specialist is assigned to it. If you paid upfront, the full amount will be refunded.</p>
          <h2>2. Cancellation after work begins</h2>
          <p>Once a specialist has started your order, cancellation is not available; however, you remain protected by the preview-first model below.</p>
          <h2>3. First-order preview protection</h2>
          <p>On your <strong>first order</strong> with Deleqate, you pay only after reviewing a watermarked preview of your deliverable. If you are not satisfied, you may request revisions or reject the deliverable with feedback at no charge — no payment is taken for rejected first-order work. From your second order onwards, payment is collected upfront at checkout; those orders remain protected by revision credits (clause 5) and the refund conditions in clause 4.</p>
          <h2>4. Refunds on paid orders</h2>
          <p>A full refund will be issued if:</p>
          <ul>
            <li>we fail to deliver your order;</li>
            <li>the deliverable is materially different from your brief and we cannot correct it within two revision cycles; or</li>
            <li>you were charged in error or charged twice (duplicate transactions are automatically prevented, and any confirmed duplicate is refunded in full).</li>
          </ul>
          <h2>5. Edit credit purchases</h2>
          <p>Unused purchased edit credits are refundable within 7 days of purchase on request. A credit consumed by a delivered revision is non-refundable.</p>
          <h2>6. How to request a refund</h2>
          <p>Email <Mail /> or WhatsApp +{wa} with your order ID. We respond within 2 business days.</p>
          <h2>7. Refund timeline</h2>
          <p>Approved refunds are processed to your original payment method via PayU within <strong>5–7 business days</strong> of approval.</p>
        </>
      );
    case 'shipping':
      return (
        <>
          <h1>Shipping &amp; Delivery Policy</h1>
          <div className="policy-updated">Last updated: 11 June 2026</div>
          <p><strong>Deleqate, a sole proprietorship firm</strong>, provides <strong>digital services only</strong>. No physical goods are shipped.</p>
          <h2>1. Delivery method</h2>
          <p>All deliverables — images, videos, design files and audio — are delivered electronically to your secure account dashboard on www.deleqate.com. Your order status updates in real time, and final files become downloadable once payment is confirmed.</p>
          <h2>2. Delivery timeline</h2>
          <p>Typical turnaround by service: background cleanup under 1 hour; social cards, listings and headshots 1–2 hours; carousels, mockups, menus and podcast reels 2–4 hours; virtual staging, reels and demo videos 3–5 hours; brand kits 4–6 hours. Complex or multi-room orders may take up to 24–48 hours. Revision deliveries follow the same timelines.</p>
          <h2>3. Delivery confirmation</h2>
          <p>An order is considered delivered when the deliverable appears in your dashboard with "Delivered" status. We may also notify you on WhatsApp.</p>
          <h2>4. Failed delivery</h2>
          <p>If a deliverable is not made available within the stated window, you may cancel for a full refund as per our Refund &amp; Cancellation Policy.</p>
          <h2>5. Questions</h2>
          <p><Mail /> · WhatsApp +{wa}</p>
        </>
      );
    default:
      return <h1>Not found</h1>;
  }
}

export default function Policy({ page, session }) {
  const [wa, setWa] = useState('');
  const [title, setTitle] = useState('');
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    const path = { about: '/about', terms: '/terms', privacy: '/privacy', refund: '/refund-policy', shipping: '/shipping-policy' }[page];
    apiGet(path).then(r => {
      if (r.support_whatsapp) setWa(r.support_whatsapp);
      if (r.page_title) { setTitle(r.page_title); document.title = `${r.page_title} — Deleqate`; }
    }).catch(() => {});
  }, [page]);

  const user = session?.user;
  const btnStyle = { fontSize: '0.8125rem', fontWeight: 600, color: 'var(--navy)', border: '2px solid var(--navy)', borderRadius: 20, padding: '0.35rem 1rem' };

  return (
    <div>
      <style>{css}</style>
      <nav className="navbar">
        <Link to="/" className="navbar-brand"><video src="/img/logo.mp4" autoPlay loop muted playsInline /></Link>
        <button className={`nav-toggle ${navOpen ? 'open' : ''}`} aria-label="Open menu" aria-expanded={navOpen} onClick={() => setNavOpen(o => !o)}>
          <span></span><span></span><span></span>
        </button>
        <div className="navbar-nav" style={navOpen ? { display: 'flex' } : undefined}>
          <Link to="/order" className="btn-nav">+ New Order</Link>
          {user ? (
            <>
              {user.name && <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--gray-600)' }}>{user.name}</span>}
              <Link to="/logout" style={btnStyle}>Logout</Link>
            </>
          ) : (
            <Link to="/login" style={btnStyle}>Login</Link>
          )}
        </div>
      </nav>

      <div className="policy-wrap">
        <div className="policy-card">
          <Body page={page} wa={wa} />
          <div className="policy-legal">
            Operated by <strong>Deleqate, a sole proprietorship firm</strong> · <Mail /> · +{wa}
          </div>
          <nav className="policy-nav" aria-label="Policy pages">
            <Link to="/about">About Us</Link>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/refund-policy">Refund &amp; Cancellation</Link>
            <Link to="/shipping-policy">Shipping &amp; Delivery</Link>
          </nav>
        </div>
      </div>

      <footer className="footer">
        <div className="container">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>© 2026 Deleqate — a sole proprietorship firm · All rights reserved</div>
        </div>
      </footer>
    </div>
  );
}
