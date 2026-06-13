// Order Wizard — renders the ORIGINAL pre-migration order_wizard.html verbatim
// (exact CSS, HTML and JavaScript) inside a self-contained iframe so the page
// looks and behaves identically to the Flask version. The only dynamic bits the
// template needed — CSRF token, the signed-in user's name/phone, the free-pass
// button (test account) and the API base — are injected here.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE, getCsrf, apiGet } from '../api.js';

import cssRaw from '../legacy/orderWizard.css?raw';
import bodyRaw from '../legacy/orderWizardBody.html?raw';
import jsRaw from '../legacy/orderWizard.js?raw';

const FONTS = 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700;800&display=swap';

export default function OrderWizard({ session }) {
  const nav = useNavigate();
  const frameRef = useRef(null);
  const [h, setH] = useState(900);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  const user = session?.user || {};
  const isTestClient = (user.phone || '') === '9876543210';

  // Admin can toggle the Voice Brief on/off; respect that flag (cache-busted).
  useEffect(() => {
    apiGet(`/order?_=${Date.now()}`).then(r => {
      if (typeof r.voice_brief_enabled === 'boolean') setVoiceEnabled(r.voice_brief_enabled);
    }).catch(() => {});
  }, []);

  const srcDoc = useMemo(() => {
    let body = bodyRaw
      .replaceAll('__NAME__', user.name || '')
      .replaceAll('__PHONE__', user.phone || '');

    // free-pass button: keep only for the test client
    if (isTestClient) {
      body = body.replace('<!--__FREEPASS_START__-->', '').replace('<!--__FREEPASS_END__-->', '');
    } else {
      body = body.replace(/<!--__FREEPASS_START__-->[\s\S]*?<!--__FREEPASS_END__-->/g, '');
    }

    const csrf = getCsrf() || '';
    return `<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="csrf-token" content="${csrf}">
<base target="_parent">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="${FONTS}" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<style>${cssRaw}</style>
${voiceEnabled ? '' : '<style>#voiceNoteSection{display:none !important;}</style>'}
</head><body>
${body}
<script>window.__API_BASE__=${JSON.stringify(API_BASE)};window.__VOICE_BRIEF_ENABLED__=${voiceEnabled ? 'true' : 'false'};</script>
<script>${jsRaw}</script>
<script>
(function(){
  function report(){ try{
    // Measure the real content bottom (wizard-wrap), NOT documentElement —
    // documentElement.scrollHeight can't shrink below the iframe's own height,
    // which leaves dead space under shorter SKUs.
    var wrap=document.querySelector('.wizard-wrap');
    var hh = wrap ? (wrap.offsetTop + wrap.offsetHeight + 16) : document.body.offsetHeight;
    parent.postMessage({__owHeight:hh},'*');
  }catch(_){} }
  window.addEventListener('load',report);
  if(window.ResizeObserver){ new ResizeObserver(report).observe(document.body); }
  setInterval(report,400);
})();
</script>
</body></html>`;
  }, [user.name, user.phone, isTestClient, voiceEnabled]);

  useEffect(() => {
    function onMsg(e) {
      if (e.data && typeof e.data.__owHeight === 'number') {
        setH(Math.max(600, Math.ceil(e.data.__owHeight)));
      }
    }
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, []);

  // If the session never loads (not signed in), send them to login.
  useEffect(() => {
    if (session && !session.user) nav('/login?next=%2Forder');
  }, [session]);

  return (
    <iframe
      key={`vb-${voiceEnabled}`}
      ref={frameRef}
      title="Place an Order"
      srcDoc={srcDoc}
      style={{ width: '100%', border: 'none', height: h, display: 'block' }}
    />
  );
}
