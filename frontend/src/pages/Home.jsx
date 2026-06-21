// Faithful port of templates/index.html — navbar, hero with before/after
// slider, marquee strip, 12 SKU cards in 4 clusters, how-it-works, FAQ, footer.
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, fileUrl } from '../api.js';

const heroCss = `
#heroSection{position:relative;width:100%;aspect-ratio:2752/1536;min-height:400px;overflow:hidden;background:#0c0a08;display:block;}
#heroText{position:absolute;bottom:0;left:0;right:0;z-index:3;padding:clamp(1.5rem,3vw,2.5rem) clamp(1.5rem,5vw,5rem) clamp(1.75rem,3.5vw,3rem);}
@media (max-width:767px){
  /* Match desktop: image fills the hero, text overlays the bottom over a gradient */
  #heroSection{aspect-ratio:unset;min-height:90vh;}
  #heroText{padding:2.25rem 1.5rem 2.5rem !important;}
  #heroGradient{display:block !important;background:linear-gradient(to top, rgba(5,3,1,0.94) 0%, rgba(5,3,1,0.82) 20%, rgba(5,3,1,0.5) 40%, rgba(5,3,1,0.12) 62%, transparent 78%) !important;}
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



const CLUSTERS = [
  ['Real Estate', [
    { key: 'virtual_staging', sla: '4h', icon: 'sofa', title: 'Virtual Staging', desc: 'Furnish empty rooms with photorealistic AI furniture. 4 rooms per order, multiple style options.', price: '₹799', note: '4-room staging pack', features: ['4 rooms per order included', 'Multiple interior styles', 'High-fidelity lighting blend', 'Self-QC comparison check'] },
    { key: 'property_reel', sla: '4h', icon: 'clapperboard', title: 'Property Marketing Reel', desc: 'Cinematic vertical video reel from your property photos. Hook, Standard, or Showcase tier.', price: 'from ₹999', note: 'per marketing reel', features: ['9:16 vertical layout', 'AI narrative voiceover', 'Cinematic drift effects', 'Viral-ready social hooks'] },
    { key: 'property_social_card', sla: '2h', icon: 'layers', title: 'Property Social Card Pack', desc: 'WhatsApp card + Instagram post + Story — brand-consistent and share-ready.', price: '₹499', note: '3-piece layout pack', features: ['WhatsApp broadcast card', 'Instagram feed/story post', 'Brand-aligned typography', 'Ready to share instantly'] },
  ]],
  ['E-commerce', [
    { key: 'bg_cleanup', sla: '1h', icon: 'scissors', title: 'Background Cleanup', desc: 'Professional product photo clipping and background removal. Flat rate up to 10 images.', price: '₹500', priceSmall: ' flat', note: 'for up to 10 images', features: ['Pure white backgrounds', 'Drop shadow addition', 'Professional clipping paths', 'High-resolution exports'] },
    { key: 'product_listing', sla: '2h', icon: 'tag', title: 'Product Listing Creation', desc: 'Keyword-rich product descriptions optimised for Amazon, Flipkart, and Shopify.', price: '₹199', note: 'per product description', features: ['SEO-optimised titles', 'Persuasive bullet points', 'Search backend keywords', 'Competitor tag analysis'] },
    { key: 'product_mockup', sla: '2h', icon: 'package', title: 'Product Lifestyle Mockup', desc: 'Place your product into photorealistic lifestyle scenes — 12 category-specific styles.', price: '₹299', priceSmall: '/img', note: 'per lifestyle mockup', features: ['Photorealistic placement', '12 custom design scenes', 'Natural shadow & lighting', 'Commercial usage license'] },
  ]],
  ['Social & Visual', [
    { key: 'instagram_carousel', sla: '3h', icon: 'image', title: 'Instagram Carousel Design', desc: 'High-converting multi-slide educational or promotional posts. 5–10 slides + captions.', price: '₹649', note: 'per carousel pack', features: ['5 to 10 visual slides', 'Full copy and captions', 'Figma source file access', 'Engagement-focused layouts'] },
    { key: 'brand_demo_video', sla: '4h', icon: 'video', title: 'Brand Demo Video', desc: 'Engaging promotional video optimised for Reels & TikTok — 5-beat DTC retention arc.', price: '₹1,249', note: 'per demo video', features: ['DTC engagement hook', 'Dynamic text overlays', 'Synced music & sound SFX', 'High-retention structure'] },
    { key: 'announcement_pack', sla: '3h', icon: 'megaphone', title: 'Announcement Pack', desc: 'Launch, offer, or event → Instagram Post + Story + WhatsApp card in one order.', price: '₹499', note: '3-piece promotional pack', features: ['Instagram feed post', 'Coordinated vertical story', 'WhatsApp broadcast format', 'Fast promotion launch'] },
  ]],
  ['Personal & Brand', [
    { key: 'brand_starter_kit', sla: '4h', icon: 'palette', title: 'Brand Starter Kit', desc: 'Complete visual identity — logo options, colour palette, typography, and brand guide.', price: '₹1,999', note: 'visual identity pack', features: ['3 unique vector logos', 'Cohesive colour palette', 'Font pairing hierarchy', 'PDF Brand Style Guide'] },
    { key: 'menu_design', sla: '4h', icon: 'clipboard-list', title: 'Menu Design', desc: 'Print-ready, typographically rich menus for restaurants and cafes. HTML/PDF output.', price: '₹799', note: 'per menu design', features: ['Print-ready PDF export', 'HTML interactive layout', 'Fully custom colors/fonts', 'Clean categorised grid'] },
    { key: 'podcast_reel', sla: '3h', icon: 'mic', title: 'Podcast Highlight Reel', desc: 'Viral short clips from your long-form podcast — karaoke captions, B-roll, optimised hook.', price: '₹649', note: 'per highlight reel', features: ['Karaoke-style captions', 'Tight edit, filler cuts', 'Topic hooks & B-rolls', 'Cleaned up studio sound'] },
  ]],
];

const FAQS = [
  ['What is Deleqate?', 'Deleqate is an AI micro-outsourcing platform. Clients purchase fixed-price creative services with guaranteed SLAs. Vetted AI Pilots execute these jobs using high-end AI tools, passing structured quality checks before delivery.'],
  ['How does preview and download work?', 'Once your order is ready, you receive a preview of the deliverable. Only after you review and explicitly approve it can you download the final files. If the delivery fails to match your brief, you can request unlimited revisions or a full refund.'],
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

function CardSlider({ beforeUrl, afterUrl }) {
  const containerRef = useRef(null);
  const [position, setPosition] = useState(50);

  const handleMove = (clientX) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0.5, Math.min(99.5, (x / rect.width) * 100));
    setPosition(pct);
  };

  const handleMouseMove = (e) => {
    handleMove(e.clientX);
  };

  const handleTouchMove = (e) => {
    if (e.touches[0]) {
      handleMove(e.touches[0].clientX);
    }
  };

  const handleMouseLeave = () => {
    setPosition(50);
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      onMouseLeave={handleMouseLeave}
      style={{
        position: 'relative',
        width: '100%',
        height: '150px',
        borderRadius: '6px',
        overflow: 'hidden',
        marginBottom: '1rem',
        background: '#1E2A39',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        cursor: 'ew-resize',
        userSelect: 'none',
        touchAction: 'none'
      }}
    >
      <img
        src={afterUrl}
        alt="After"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          pointerEvents: 'none'
        }}
      />
      <img
        src={beforeUrl}
        alt="Before"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          clipPath: `inset(0 ${100 - position}% 0 0)`,
          pointerEvents: 'none'
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: `${position}%`,
          width: '2px',
          background: 'rgba(255,255,255,0.95)',
          boxShadow: '0 0 5px rgba(0,0,0,0.5)',
          transform: 'translateX(-50%)',
          pointerEvents: 'none',
          zIndex: 3
        }}
      />
      <span style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.65)', color: '#9DB4C6', fontSize: '0.55rem', fontWeight: 700, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase', pointerEvents: 'none', zIndex: 4 }}>Before</span>
      <span style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(44,62,84,0.9)', color: '#F5F8FA', fontSize: '0.55rem', fontWeight: 700, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase', pointerEvents: 'none', zIndex: 4 }}>After</span>
    </div>
  );
}

function CardSlideshow({ images }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prevIndex) => (prevIndex + 1) % images.length);
    }, 2200);
    return () => clearInterval(timer);
  }, [images]);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '150px',
        borderRadius: '6px',
        overflow: 'hidden',
        marginBottom: '1rem',
        background: '#1E2A39',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        userSelect: 'none'
      }}
    >
      {images.map((imgUrl, i) => (
        <img
          key={imgUrl}
          src={imgUrl}
          alt={`Slide ${i}`}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: i === index ? 1 : 0,
            transition: 'opacity 0.6s ease-in-out',
            pointerEvents: 'none'
          }}
        />
      ))}
      <span style={{ position: 'absolute', bottom: 8, right: 8, background: 'rgba(0,0,0,0.65)', color: '#9DB4C6', fontSize: '0.55rem', fontWeight: 700, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase', zIndex: 4 }}>
        Carousel {index + 1}/{images.length}
      </span>
    </div>
  );
}

export default function Home({ session }) {
  const nav = useNavigate();
  const [data, setData] = useState({ inactive_tasks: [], hero_video_url: null });
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => {
    apiGet('/api/index-data').then(res => {
      setData(res);
      setTimeout(() => {
        if (window.lucide) {
          window.lucide.createIcons();
        }
      }, 100);
    });
  }, []);

  const user = session?.user;
  const inactive = data.inactive_tasks || [];
  const orderHref = (task) => user ? `/order?task=${task}` : `/login?next=${encodeURIComponent('/order?task=' + task)}`;

  return (
    <div>
      <style>{heroCss}</style>

      {/* NAVBAR */}
      <nav className="navbar">
        <Link to="/" className="navbar-brand"><video src="/img/logo.mp4" autoPlay loop muted playsInline /></Link>
        <button className={`nav-toggle ${navOpen ? 'open' : ''}`} aria-label="Open menu" aria-expanded={navOpen} onClick={() => setNavOpen(o => !o)}>
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
              {user.name && <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--gray-300)' }}>{user.name}</span>}
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
              <span style={{ color: '#9DB4C6' }}>Just Deleqate it.</span>
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
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}><span className="inline-icon"><i data-lucide="lock"></i></span><strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>Escrow</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}><span className="inline-icon"><i data-lucide="clock"></i></span><strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>SLA or refund</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem' }}><span className="inline-icon"><i data-lucide="check-circle"></i></span><strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>QC reviewed</strong></span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} /><strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>32 Pilots live</strong></span>
              </div>
            </div>
          </div>
        </div>
      </section>



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
                  <Link key={s.key} to={orderHref(s.key)} target="_blank" rel="noopener noreferrer" className="sku-card" style={{ display: 'block', textDecoration: 'none' }}>
                    <span className="sku-sla"><i data-lucide="clock" className="inline-icon" style={{width:"12px",height:"12px",marginRight:"3px"}}></i> {s.sla} SLA</span>
                    <div className="sku-icon" style={{ marginBottom: '0.85rem' }}><i data-lucide={s.icon}></i></div>
                    
                    {s.key === 'virtual_staging' && (
                      <CardSlider
                        beforeUrl="/img/task_holders/1/before.jpg"
                        afterUrl="/img/task_holders/1/After.png"
                      />
                    )}
                    {s.key === 'property_social_card' && (
                      <CardSlider
                        beforeUrl="/img/task_holders/3/before.jpeg"
                        afterUrl="/img/task_holders/3/A_professional_real-estate_marketing_social_202606210335.jpeg"
                      />
                    )}
                    {s.key === 'bg_cleanup' && (
                      <CardSlider
                        beforeUrl="/img/task_holders/4/download.png"
                        afterUrl="/img/task_holders/4/Photoroom/download.png"
                      />
                    )}
                    {s.key === 'product_mockup' && (
                      <CardSlider
                        beforeUrl="/img/task_holders/6/product lifestyle mockup before .jpeg"
                        afterUrl="/img/task_holders/6/product lifestyle mockup2 .jpeg"
                      />
                    )}
                    {s.key === 'instagram_carousel' && (
                      <CardSlideshow
                        images={[
                          "/img/task_holders/7/4.jpeg",
                          "/img/task_holders/7/car 1.png",
                          "/img/task_holders/7/car 2.png",
                          "/img/task_holders/7/car 3.png",
                          "/img/task_holders/7/car 4.png",
                          "/img/task_holders/7/car 5.png",
                          "/img/task_holders/7/car 6.png",
                          "/img/task_holders/7/car 7.png"
                        ]}
                      />
                    )}

                    <h4>{s.title}</h4>
                    <p>{s.desc}</p>
                    <div className="sku-price">{s.price}{s.priceSmall && <small style={{ fontSize: '.75rem' }}>{s.priceSmall}</small>}</div>
                    <div className="sku-price-note">{s.note}</div>
                    <ul className="sku-features">
                      {s.features.map(f => <li key={f}>{f}</li>)}
                    </ul>
                  </Link>
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
            {[['01', 'clipboard-edit', 'Submit Brief', 'Fill out our guided intake form and upload your raw files. Zero technical AI knowledge needed.'],
              ['02', 'zap', 'Vetted Pilot Executes', 'A qualified AI Pilot takes your job and executes it using professional AI tools within the SLA.'],
              ['03', 'shield-check', 'Preview & Download', 'Review your delivery. Satisfied? Approve and download your files. Else request a revision or refund.'],
            ].map(([num, icon, title, desc]) => (
              <div key={num} className="how-step-card">
                <div className="how-step-num">{num}</div>
                <span className="how-step-icon"><i data-lucide={icon}></i></span>
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
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>Dele<span style={{ color: 'var(--navy)' }}>qate</span></div>
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
