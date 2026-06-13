// Faithful port of templates/index.html — navbar, hero with before/after
// slider, marquee strip, 12 SKU cards in 4 clusters, how-it-works, FAQ, footer.
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, fileUrl } from '../api.js';

const heroCss = `
#heroSection{position:relative;width:100%;aspect-ratio:2752/1536;min-height:400px;overflow:hidden;background:#0c0a08;display:block;}
#heroText{position:absolute;bottom:0;left:0;right:0;z-index:3;padding:clamp(1.5rem,3vw,2.5rem) clamp(1.5rem,5vw,5rem) clamp(1.75rem,3.5vw,3rem);}
@media (max-width:767px){
  #heroSection{aspect-ratio:unset;min-height:unset;display:flex;flex-direction:column;}
  #heroSliderPanel{width:100% !important;aspect-ratio:2752/1536;position:relative !important;inset:auto !important;overflow:hidden;flex-shrink:0;order:2;}
  #heroSlider{position:absolute !important;inset:0 !important;}
  #heroGradient{display:none !important;}
  #heroText{position:relative !important;order:1;background:#0c0a08;padding:2rem 1.5rem 1.75rem !important;}
}
@keyframes pulse-dot{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.55;transform:scale(1.35);}}
#heroSlider{cursor:grab !important;}
#heroSlider:active,#hHandle:active{cursor:grabbing !important;}
.marquee-track{display:inline-block;animation:marquee-scroll 35s linear infinite;}
.marquee-track:hover{animation-play-state:paused;}
.marquee-item{display:inline-block;color:var(--gray-700);font-size:.875rem;font-weight:600;letter-spacing:.01em;padding:0 .5rem;}
.marquee-sep{display:inline-block;color:var(--gold);font-size:.75rem;padding:0 .75rem;opacity:.9;}
@keyframes marquee-scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}
`;

const MARQUEE = ['⚡ Fixed price. No surprises.', '🎯 Vetted AI Pilots only', '🔒 Pay only when you approve',
  '⏱ SLA guaranteed — or full refund', '🏡 Virtual Staging from ₹799', '📸 Product Visuals from ₹299',
  '🎬 Property Reels from ₹999', '🖼 Background Cleanup from ₹79', '🎨 Brand Starter Kit from ₹1,499',
  '📦 12 AI creative tasks available', '🕐 Available 10AM–10PM IST · All Days'];

const CLUSTERS = [
  ['Real Estate', [
    { key: 'virtual_staging', sla: '4h', icon: '🛋️', title: 'Virtual Staging', desc: 'Furnish empty rooms with photorealistic AI furniture. 4 rooms per order, multiple style options.', price: '₹799', note: '4-room staging pack', features: ['4 rooms per order included', 'Multiple interior styles', 'High-fidelity lighting blend', 'Self-QC comparison check'] },
    { key: 'property_reel', sla: '4h', icon: '🎬', title: 'Property Marketing Reel', desc: 'Cinematic vertical video reel from your property photos. Hook, Standard, or Showcase tier.', price: 'from ₹999', note: 'per marketing reel', features: ['9:16 vertical layout', 'AI narrative voiceover', 'Cinematic drift effects', 'Viral-ready social hooks'] },
    { key: 'property_social_card', sla: '2h', icon: '🃏', title: 'Property Social Card Pack', desc: 'WhatsApp card + Instagram post + Story — brand-consistent and share-ready.', price: '₹499', note: '3-piece layout pack', features: ['WhatsApp broadcast card', 'Instagram feed/story post', 'Brand-aligned typography', 'Ready to share instantly'] },
  ]],
  ['E-commerce', [
    { key: 'bg_cleanup', sla: '1h', icon: '✂️', title: 'Background Cleanup', desc: 'Professional product photo clipping and background removal. Min 5 images per order.', price: '₹79', priceSmall: '/img', note: 'per image (minimum 5)', features: ['Pure white backgrounds', 'Drop shadow addition', 'Professional clipping paths', 'High-resolution exports'] },
    { key: 'product_listing', sla: '2h', icon: '🏷️', title: 'Product Listing Creation', desc: 'Keyword-rich product descriptions optimised for Amazon, Flipkart, and Shopify.', price: '₹199', note: 'per product description', features: ['SEO-optimised titles', 'Persuasive bullet points', 'Search backend keywords', 'Competitor tag analysis'] },
    { key: 'product_mockup', sla: '2h', icon: '📦', title: 'Product Lifestyle Mockup', desc: 'Place your product into photorealistic lifestyle scenes — 12 category-specific styles.', price: '₹299', priceSmall: '/img', note: 'per lifestyle mockup', features: ['Photorealistic placement', '12 custom design scenes', 'Natural shadow & lighting', 'Commercial usage license'] },
  ]],
  ['Social & Visual', [
    { key: 'instagram_carousel', sla: '3h', icon: '🖼️', title: 'Instagram Carousel Design', desc: 'High-converting multi-slide educational or promotional posts. 5–10 slides + captions.', price: '₹649', note: 'per carousel pack', features: ['5 to 10 visual slides', 'Full copy and captions', 'Figma source file access', 'Engagement-focused layouts'] },
    { key: 'brand_demo_video', sla: '4h', icon: '🎥', title: 'Brand Demo Video', desc: 'Engaging promotional video optimised for Reels & TikTok — 5-beat DTC retention arc.', price: '₹1,249', note: 'per demo video', features: ['DTC engagement hook', 'Dynamic text overlays', 'Synced music & sound SFX', 'High-retention structure'] },
    { key: 'announcement_pack', sla: '3h', icon: '📣', title: 'Announcement Pack', desc: 'Launch, offer, or event → Instagram Post + Story + WhatsApp card in one order.', price: '₹499', note: '3-piece promotional pack', features: ['Instagram feed post', 'Coordinated vertical story', 'WhatsApp broadcast format', 'Fast promotion launch'] },
  ]],
  ['Personal & Brand', [
    { key: 'brand_starter_kit', sla: '4h', icon: '🎨', title: 'Brand Starter Kit', desc: 'Complete visual identity — logo options, colour palette, typography, and brand guide.', price: '₹1,999', note: 'visual identity pack', features: ['3 unique vector logos', 'Cohesive colour palette', 'Font pairing hierarchy', 'PDF Brand Style Guide'] },
    { key: 'menu_design', sla: '4h', icon: '📋', title: 'Menu Design', desc: 'Print-ready, typographically rich menus for restaurants and cafes. HTML/PDF output.', price: '₹799', note: 'per menu design', features: ['Print-ready PDF export', 'HTML interactive layout', 'Fully custom colors/fonts', 'Clean categorised grid'] },
    { key: 'podcast_reel', sla: '3h', icon: '🎙️', title: 'Podcast Highlight Reel', desc: 'Viral short clips from your long-form podcast — karaoke captions, B-roll, optimised hook.', price: '₹649', note: 'per highlight reel', features: ['Karaoke-style captions', 'Tight edit, filler cuts', 'Topic hooks & B-rolls', 'Cleaned up studio sound'] },
  ]],
];

const FAQS = [
  ['What is Deleqate?', 'Deleqate is an AI micro-outsourcing platform. Clients purchase fixed-price creative services with guaranteed SLAs. Vetted AI Pilots execute these jobs using high-end AI tools, passing structured quality checks before delivery.'],
  ['How does the escrow policy work?', 'When you make an order, the payment is held securely in escrow. It is only released to the AI Pilot after you review and explicitly approve the deliverable. If the delivery fails to match your brief, you can request unlimited revisions or a full refund.'],
  ['How is the quality of deliverables checked?', 'Every delivery is cross-checked against a rigorous, SKU-specific Quality Control (QC) checklist. AI Pilots check alignment, textures, lighting, spelling, formatting, and file exports. You also get an interactive slider on staging files to compare changes side-by-side.'],
  ['Can I request revisions?', 'Yes! If the output needs changes, click the "Request Revision" button and describe what you want modified. Our AI Pilots will execute the revisions promptly within a fast turnaround.'],
];

// ── Before/After slider — direct port of the inline hero JS ──
function HeroSlider() {
  const sliderRef = useRef(null), beforeRef = useRef(null), divRef = useRef(null), handleRef = useRef(null);

  useEffect(() => {
    const slider = sliderRef.current, imgB = beforeRef.current, divLine = divRef.current, handle = handleRef.current;
    if (!slider || !imgB || !divLine) return;

    let cur = 99.5, dragging = false, autoOn = true, resumeTimer = null;
    let phase = 'holdR', holdFrames = 80, raf;
    const HOLD_FRAMES = 90, SPEED = 0.22;

    function applyPos(p) {
      p = Math.max(0.5, Math.min(99.5, p)); cur = p;
      imgB.style.clipPath = 'inset(0 ' + (100 - p).toFixed(2) + '% 0 0)';
      divLine.style.left = p.toFixed(2) + '%';
    }
    function animStep() {
      if (!dragging && autoOn) {
        if (phase === 'holdR') { if (--holdFrames <= 0) phase = 'sweepL'; }
        else if (phase === 'sweepL') { cur -= SPEED; if (cur <= 0.5) { cur = 0.5; phase = 'holdL'; holdFrames = HOLD_FRAMES; } applyPos(cur); }
        else if (phase === 'holdL') { if (--holdFrames <= 0) phase = 'sweepR'; }
        else { cur += SPEED; if (cur >= 99.5) { cur = 99.5; phase = 'holdR'; holdFrames = HOLD_FRAMES; } applyPos(cur); }
      }
      raf = requestAnimationFrame(animStep);
    }
    const pctFromX = x => { const r = slider.getBoundingClientRect(); return Math.max(0.5, Math.min(99.5, (x - r.left) / r.width * 100)); };
    function onDragStart(p) {
      dragging = true; autoOn = false; clearTimeout(resumeTimer); applyPos(p);
      handle.style.transform = 'translate(-50%,-50%) scale(1.15)';
      handle.style.boxShadow = '0 4px 28px rgba(0,0,0,0.5),0 0 0 2px rgba(255,255,255,0.7)';
    }
    const onDragMove = p => { if (dragging) applyPos(p); };
    function onDragEnd() {
      if (!dragging) return; dragging = false;
      handle.style.transform = 'translate(-50%,-50%) scale(1)';
      handle.style.boxShadow = '0 2px 24px rgba(0,0,0,0.4),0 0 0 2px rgba(255,255,255,0.65)';
      resumeTimer = setTimeout(() => { phase = cur > 50 ? 'sweepL' : 'sweepR'; autoOn = true; }, 2800);
    }
    const md = e => { onDragStart(pctFromX(e.clientX)); e.preventDefault(); };
    const mm = e => onDragMove(pctFromX(e.clientX));
    let txS = 0, tyS = 0, isH = null;
    const ts = e => { txS = e.touches[0].clientX; tyS = e.touches[0].clientY; isH = null; onDragStart(pctFromX(txS)); };
    const tm = e => {
      if (!dragging) return;
      const dx = Math.abs(e.touches[0].clientX - txS), dy = Math.abs(e.touches[0].clientY - tyS);
      if (isH === null && (dx > 5 || dy > 5)) isH = dx >= dy;
      if (isH) { e.preventDefault(); onDragMove(pctFromX(e.touches[0].clientX)); }
    };
    slider.addEventListener('mousedown', md);
    window.addEventListener('mousemove', mm);
    window.addEventListener('mouseup', onDragEnd);
    slider.addEventListener('touchstart', ts, { passive: false });
    slider.addEventListener('touchmove', tm, { passive: false });
    slider.addEventListener('touchend', onDragEnd);
    window.addEventListener('touchend', onDragEnd);
    applyPos(99.5);
    raf = requestAnimationFrame(animStep);
    return () => {
      cancelAnimationFrame(raf); clearTimeout(resumeTimer);
      slider.removeEventListener('mousedown', md);
      window.removeEventListener('mousemove', mm);
      window.removeEventListener('mouseup', onDragEnd);
      slider.removeEventListener('touchstart', ts);
      slider.removeEventListener('touchmove', tm);
      slider.removeEventListener('touchend', onDragEnd);
      window.removeEventListener('touchend', onDragEnd);
    };
  }, []);

  return (
    <div id="heroSlider" ref={sliderRef} style={{ position: 'absolute', inset: 0, cursor: 'grab', userSelect: 'none', touchAction: 'none' }}>
      <img id="hAfter" src="/img/hero_after.png"
        alt="Empty room transformed with AI virtual staging — furnished, styled interior render by Deleqate"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center center', display: 'block', transform: 'translateZ(0)' }} />
      <img id="hBefore" ref={beforeRef} src="/img/hero_before.png"
        alt="Original unstaged room photo before AI virtual staging"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center center', display: 'block', clipPath: 'inset(0 0.5% 0 0)', willChange: 'clip-path', transform: 'translateZ(0)' }} />
      <div ref={divRef} style={{ position: 'absolute', top: 0, bottom: 0, left: '99.5%', width: 2, background: 'rgba(255,255,255,0.95)', boxShadow: '0 0 0 1px rgba(0,0,0,0.18),0 0 20px 6px rgba(255,255,255,0.22)', transform: 'translateX(-50%)', zIndex: 3, pointerEvents: 'none' }}>
        <div id="hHandle" ref={handleRef} style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 48, height: 48, borderRadius: '50%', background: 'white', boxShadow: '0 2px 24px rgba(0,0,0,0.4),0 0 0 2px rgba(255,255,255,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.12s ease,box-shadow 0.12s ease', pointerEvents: 'auto', cursor: 'grab' }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M6 10H1M1 10L3.5 7.5M1 10L3.5 12.5" stroke="#1a1a2e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M14 10H19M19 10L16.5 7.5M19 10L16.5 12.5" stroke="#1a1a2e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <span style={{ position: 'absolute', top: 20, left: 20, background: 'rgba(0,0,0,0.58)', backdropFilter: 'blur(8px)', color: 'white', fontSize: '0.6rem', fontWeight: 700, padding: '5px 14px', borderRadius: 20, letterSpacing: '0.13em', zIndex: 4, pointerEvents: 'none', textTransform: 'uppercase' }}>Before</span>
      <span style={{ position: 'absolute', top: 20, right: 20, background: 'rgba(34,197,94,0.88)', backdropFilter: 'blur(8px)', color: 'white', fontSize: '0.6rem', fontWeight: 700, padding: '5px 14px', borderRadius: 20, letterSpacing: '0.13em', zIndex: 4, pointerEvents: 'none', textTransform: 'uppercase' }}>AI Staged</span>
    </div>
  );
}

export default function Home({ session }) {
  const nav = useNavigate();
  const [data, setData] = useState({ inactive_tasks: [], hero_video_url: null });
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => { apiGet('/api/index-data').then(setData); }, []);

  const user = session?.user;
  const inactive = data.inactive_tasks || [];
  const orderHref = (task) => user ? `/order?task=${task}` : `/login?next=${encodeURIComponent('/order?task=' + task)}`;

  return (
    <div>
      <style>{heroCss}</style>

      {/* NAVBAR */}
      <nav className="navbar">
        <Link to="/" className="navbar-brand">Dele<span>qate</span></Link>
        <button className="nav-toggle" aria-label="Open menu" aria-expanded={navOpen} onClick={() => setNavOpen(o => !o)}>
          <span></span><span></span><span></span>
        </button>
        <div className="navbar-nav" style={navOpen ? { display: 'flex' } : undefined}>
          <a href="#tasks">Solutions</a>
          <a href="#how">How it Works</a>
          {user && user.role !== 'admin' ? (
            <>
              {user.role === 'pilot'
                ? <Link to="/pilot/dashboard" className="btn-nav">My Jobs</Link>
                : <Link to="/client/orders" className="btn-nav">My Orders</Link>}
              <Link to="/logout" style={{ fontSize: '.8125rem' }}>Logout</Link>
            </>
          ) : (
            <>
              <Link to="/login?type=pilot" className="btn-nav-pilot">Pilot Login</Link>
              <Link to="/login?type=client" className="btn-nav">Customer Login</Link>
            </>
          )}
        </div>
      </nav>

      {/* HERO */}
      <section id="heroSection" tabIndex={-1}>
        <div id="heroSliderPanel" style={{ position: 'absolute', inset: 0 }}>
          {data.hero_video_url
            ? <video src={fileUrl(data.hero_video_url)} autoPlay muted loop playsInline
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
            : <HeroSlider />}
        </div>
        <div id="heroGradient" style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(5,3,1,0.88) 0%, rgba(5,3,1,0.6) 12%, rgba(5,3,1,0.25) 24%, transparent 40%)', zIndex: 2, pointerEvents: 'none' }} />
        <div id="heroText">
          <div style={{ maxWidth: 'min(680px, 90vw)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap', marginBottom: '1.1rem' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(197,160,40,0.2)', border: '1px solid rgba(197,160,40,0.45)', color: '#e8c86a', padding: '0.28rem 0.8rem', borderRadius: 999, fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em' }}>✦ Now in Beta</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.35)', borderRadius: 999, padding: '0.28rem 0.9rem', fontSize: '0.7rem', color: '#86efac' }}>
                <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0, animation: 'pulse-dot 2s ease-in-out infinite' }} />
                <strong>Available 10AM–10PM IST</strong>&nbsp;· All Days
              </span>
            </div>
            <h1 style={{ fontSize: 'clamp(1.75rem,3.5vw,3.25rem)', lineHeight: 1.1, letterSpacing: '-0.025em', color: 'white', marginBottom: '0.85rem', fontFamily: 'var(--font-display)', textShadow: '0 2px 20px rgba(0,0,0,0.5)' }}>
              You don't need to learn every AI tool.<br />
              <span style={{ color: 'var(--gold)' }}>Just Deleqate it.</span>
            </h1>
            <p style={{ fontSize: 'clamp(0.875rem,1.4vw,1.0625rem)', color: 'rgba(255,255,255,0.75)', lineHeight: 1.65, marginBottom: '1.5rem', maxWidth: 520, textShadow: '0 1px 8px rgba(0,0,0,0.5)' }}>
              Upload your brief. Pay a fixed price. Get a guaranteed AI-powered result — delivered by a vetted AI Pilot in under 4 hours.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem 2rem' }}>
              <div style={{ display: 'flex', gap: '0.875rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <Link to={user ? '/order' : '/login?next=%2Forder'} className="btn btn-primary btn-lg" style={{ fontSize: '0.9375rem', padding: '0.8125rem 1.875rem' }}>Place an Order →</Link>
                <a href="#how" style={{ color: 'rgba(255,255,255,0.78)', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '1px solid rgba(255,255,255,0.3)', paddingBottom: 2 }}>See how it works</a>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem 1.25rem' }}>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}>🔒 <strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>Escrow</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}>⏱ <strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>SLA or refund</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}>✅ <strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>QC reviewed</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} /><strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>32 Pilots live</strong></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MARQUEE STRIP */}
      <div style={{ overflow: 'hidden', background: 'var(--gold-pale)', borderTop: '1px solid var(--gold-container)', borderBottom: '1px solid var(--gold-container)', padding: '0.7rem 0', whiteSpace: 'nowrap' }}>
        <div className="marquee-track">
          {[...MARQUEE, ...MARQUEE].map((m, i) => (
            <span key={i}>
              <span className="marquee-item">{m}</span>
              <span className="marquee-sep">✦</span>
            </span>
          ))}
        </div>
      </div>

      {/* TASKS */}
      <section className="section" id="tasks">
        <div className="container">
          <div className="text-center mb-4">
            <div className="label-caps" style={{ marginBottom: '.75rem' }}>Precision-Grade SKUs</div>
            <h2>What can you Deleqate?</h2>
            <p style={{ maxWidth: 480, margin: '.75rem auto 0' }}>12 fixed-price AI tasks across 4 categories. Fixed SLA. No subscriptions. No surprises.</p>
          </div>
          {CLUSTERS.map(([cluster, skus]) => (
            <div key={cluster}>
              <div className="cluster-label">{cluster}</div>
              <div className="grid-3 mb-4">
                {skus.filter(s => !inactive.includes(s.key)).map(s => (
                  <div key={s.key} className="sku-card" onClick={() => nav(orderHref(s.key))}>
                    <span className="sku-sla">⏱ {s.sla} SLA</span>
                    <div className="sku-icon">{s.icon}</div>
                    <h4>{s.title}</h4>
                    <p>{s.desc}</p>
                    <div className="sku-price">{s.price}{s.priceSmall && <small style={{ fontSize: '.75rem' }}>{s.priceSmall}</small>}</div>
                    <div className="sku-price-note">{s.note}</div>
                    <ul className="sku-features">
                      {s.features.map(f => <li key={f}>{f}</li>)}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section" id="how" style={{ borderTop: '1px solid var(--border-soft)', background: 'var(--surface-low)' }}>
        <div className="container">
          <div className="text-center mb-4">
            <div className="label-caps" style={{ marginBottom: '.75rem' }}>Guaranteed Delivery Flow</div>
            <h2>Simple. Standardised. Transparent.</h2>
            <p style={{ maxWidth: 480, margin: '.75rem auto 0' }}>No complex tools to learn. No freelancer negotiations. 3 simple steps.</p>
          </div>
          <div className="grid-3">
            {[['01', '📋', 'Submit Brief', 'Fill out our guided intake form and upload your raw files. Zero technical AI knowledge needed.'],
              ['02', '⚡', 'Vetted Pilot Executes', 'A qualified AI Pilot takes your job and executes it using professional AI tools within the SLA.'],
              ['03', '✅', 'Approve & Release', 'Review your delivery. Satisfied? Approve to release payment from escrow. Else request a revision or refund.'],
            ].map(([num, icon, title, desc]) => (
              <div key={num} className="how-step-card">
                <div className="how-step-num">{num}</div>
                <span className="how-step-icon">{icon}</span>
                <h4 className="how-step-title">{title}</h4>
                <p className="how-step-desc">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="section" id="faq">
        <div className="container" style={{ maxWidth: 800 }}>
          <div className="text-center mb-4">
            <div className="label-caps" style={{ marginBottom: '.75rem' }}>Got Questions?</div>
            <h2>Frequently Asked Questions</h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {FAQS.map(([q, a]) => (
              <details key={q} style={{ background: 'var(--surface-white)', border: '1px solid var(--border-soft)', borderRadius: 'var(--radius-lg)', padding: '1rem 1.25rem', cursor: 'pointer' }}>
                <summary style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>{q}</summary>
                <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <div className="container">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>Dele<span style={{ color: 'var(--gold)' }}>qate</span></div>
          <p style={{ maxWidth: 640, margin: '0 auto 1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
            Deleqate is an AI-powered services platform. We deliver fixed-price digital creative tasks —
            virtual staging, property reels, product visuals, brand kits, menus and social media assets — executed by
            vetted AI specialists and quality-checked before delivery. Preview first, pay only to unlock your final files.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <a href="#tasks">Solutions</a>
            <a href="#how">How it Works</a>
            <Link to="/login">Login</Link>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.25rem', marginBottom: '1.5rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
            <Link to="/about">About Us</Link>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/refund-policy">Refund &amp; Cancellation</Link>
            <Link to="/shipping-policy">Shipping &amp; Delivery</Link>
            <a href="mailto:support@deleqate.com">Contact</a>
          </div>
          <div style={{ marginBottom: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'var(--gold-pale)', border: '1px solid var(--gold-container)', borderRadius: 999, padding: '0.35rem 1rem', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
            <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: 'var(--success)', flexShrink: 0 }} />
            <strong>Available 10AM–10PM IST</strong>&nbsp;· All Days
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>© 2026 Deleqate · Built with pride in India · All rights reserved</div>
        </div>
      </footer>
    </div>
  );
}
