// Order Wizard — renders the ORIGINAL pre-migration order_wizard.html verbatim
// (exact CSS, HTML and JavaScript) inside a self-contained iframe so the page
// looks and behaves identically to the Flask version. The only dynamic bits the
// template needed — CSRF token, the signed-in user's name/phone, the free-pass
// button (test account) and the API base — are injected here.
import { useEffect, useMemo, useRef, useState, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE, getCsrf, apiGet } from '../api.js';

import cssRaw from '../legacy/orderWizard.css?raw';
import bodyRaw from '../legacy/orderWizardBody.html?raw';
import jsRaw from '../legacy/orderWizard.js?raw';

const FONTS = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@800&display=swap';

export default function OrderWizard({ session }) {
  const nav = useNavigate();
  const frameRef = useRef(null);
  const [h, setH] = useState(900);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [inactiveTasks, setInactiveTasks] = useState([]);

  const user = session?.user || {};
  const isTestClient = (user.phone || '') === '9871722766';

  // Admin can toggle the Voice Brief on/off + disable SKUs; respect both (cache-busted).
  useEffect(() => {
    apiGet(`/order?_=${Date.now()}`).then(r => {
      if (typeof r.voice_brief_enabled === 'boolean') setVoiceEnabled(r.voice_brief_enabled);
      if (Array.isArray(r.inactive_tasks)) setInactiveTasks(r.inactive_tasks);
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
<script src="https://unpkg.com/lucide@latest"></script>
${voiceEnabled ? '' : '<style>#voiceNoteSection{display:none !important;}</style>'}
</head><body>
${body}
<script>window.__API_BASE__=${JSON.stringify(API_BASE)};window.__VOICE_BRIEF_ENABLED__=${voiceEnabled ? 'true' : 'false'};window.__INACTIVE_TASKS__=${JSON.stringify(inactiveTasks)};</script>
<script>${jsRaw}</script>
<script>
(function() {
  function replaceEmojis(root) {
    root = root || document.body;
    
    // 1. .upload-icon
    root.querySelectorAll('.upload-icon').forEach(el => {
      var iconMap = { '📦': 'package', '📷': 'camera', '🖼️': 'image', '🖼': 'image', '📸': 'camera', '📄': 'file-text', '🎙️': 'mic', '🎙': 'mic', '📐': 'ruler', '🎨': 'palette' };
      var txt = el.textContent.trim();
      if (iconMap[txt]) {
        el.innerHTML = '<i data-lucide=\"' + iconMap[txt] + '\" style=\"width:36px;height:36px;stroke-width:1.5;color:var(--text-secondary);\"></i>';
      }
    });

    // 2. .form-section-title
    root.querySelectorAll('.form-section-title').forEach(el => {
      var match = el.innerHTML.match(/^([^\\x00-\\x7f]\\ufe0f?)\\s*(.*)$/);
      if (match) {
        var emoji = match[1];
        var rest = match[2];
        var iconMap = { '📦': 'package', '🛒': 'shopping-cart', '🎨': 'palette', '📝': 'pen-tool', '🔢': 'hash', '💡': 'lightbulb', '📣': 'megaphone', '🚀': 'rocket', '🍽️': 'utensils', '🍽': 'utensils', '🎙️': 'mic', '🎙': 'mic', '📐': 'ruler', '👤': 'user', '🎠': 'layers', '🎉': 'party-popper', '✅': 'check-circle', '➕': 'plus', '🌅': 'sun' };
        var icon = iconMap[emoji];
        if (icon) {
          el.innerHTML = '<i data-lucide=\"' + icon + '\" style=\"width:18px;height:18px;margin-right:8px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">' + rest + '</span>';
        }
      }
    });

    // 3. .price-sla
    root.querySelectorAll('.price-sla').forEach(el => {
      var match = el.innerHTML.match(/^⏱\\s*(.*)$/);
      if (match) {
        el.innerHTML = '<i data-lucide=\"clock\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">' + match[1] + '</span>';
      }
    });

    // 4. lock notes
    root.querySelectorAll('#bg-lock-note, #submitNote').forEach(el => {
      var match = el.innerHTML.match(/^🔒\\s*(.*)$/);
      if (match) {
        el.innerHTML = '<i data-lucide=\"lock\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">' + match[1] + '</span>';
      }
    });

    // 5. chip labels
    root.querySelectorAll('.chip label').forEach(el => {
      var match = el.innerHTML.match(/^([^\\x00-\\x7f]\\ufe0f?)\\s*(.*)$/);
      if (match) {
        var emoji = match[1];
        var rest = match[2];
        var iconMap = { '📝': 'pen-tool', '🖼️': 'image', '🖼': 'image', '📸': 'camera', '📊': 'bar-chart-3', '🎨': 'palette' };
        var icon = iconMap[emoji];
        if (icon) {
          el.innerHTML = '<i data-lucide=\"' + icon + '\" style=\"width:13px;height:13px;margin-right:5px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">' + rest + '</span>';
        }
      }
    });
    
    // 6. Voice brief icon wrapper
    root.querySelectorAll('div[style*=\"font-size:1.75rem\"]').forEach(el => {
      if (el.textContent.trim() === '🎙️' || el.textContent.trim() === '🎙') {
        el.innerHTML = '<i data-lucide=\"mic\" style=\"width:36px;height:36px;color:var(--text-secondary);\"></i>';
      }
    });
    root.querySelectorAll('div[style*=\"font-size:1.5rem\"]').forEach(el => {
      if (el.textContent.trim() === '✅') {
        el.innerHTML = '<i data-lucide=\"check-circle\" style=\"width:36px;height:36px;color:var(--success);\"></i>';
      }
    });
    
    // 7. General button checks
    root.querySelectorAll('button').forEach(el => {
      if (el.textContent.trim() === '🎙 Start Recording') {
        el.innerHTML = '<i data-lucide=\"mic\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">Start Recording</span>';
      } else if (el.textContent.trim() === '⏹ Stop') {
        el.innerHTML = '<i data-lucide=\"square\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">Stop</span>';
      } else if (el.textContent.trim() === '🗑 Re-record') {
        el.innerHTML = '<i data-lucide=\"trash-2\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">Re-record</span>';
      } else if (el.textContent.trim() === 'Submit Order →') {
        el.innerHTML = '<span style=\"vertical-align:middle;\">Submit Order</span><i data-lucide=\"arrow-right\" style=\"width:14px;height:14px;margin-left:6px;vertical-align:middle;display:inline-block;\"></i>';
      } else if (el.textContent.trim() === '🎟 Use Free Pass') {
        el.innerHTML = '<i data-lucide=\"ticket\" style=\"width:14px;height:14px;margin-right:6px;vertical-align:middle;display:inline-block;\"></i><span style=\"vertical-align:middle;\">Use Free Pass</span>';
      }
    });
    
    // 8. File chip items in orderWizard.js
    root.querySelectorAll('.file-chip-item').forEach(el => {
      var nameEl = el.querySelector('.fc-name');
      if (nameEl && nameEl.innerHTML.indexOf('📎') > -1) {
        nameEl.innerHTML = nameEl.innerHTML.replace('📎', '<i data-lucide=\"paperclip\" style=\"width:12px;height:12px;margin-right:4px;vertical-align:middle;display:inline-block;\"></i>');
      }
    });
  }

  function init() {
    replaceEmojis();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Set up MutationObserver to handle dynamic additions like photo rows
  var observer = new MutationObserver(function(mutations) {
    var added = false;
    mutations.forEach(function(m) {
      if (m.addedNodes.length) {
        m.addedNodes.forEach(function(node) {
          if (node.nodeType === 1) { // ELEMENT_NODE
            added = true;
          }
        });
      }
    });
    if (added) {
      observer.disconnect();
      mutations.forEach(function(m) {
        if (m.addedNodes.length) {
          m.addedNodes.forEach(function(node) {
            if (node.nodeType === 1) { // ELEMENT_NODE
              replaceEmojis(node);
            }
          });
        }
      });
      if (window.lucide) {
        window.lucide.createIcons();
      }
      observer.observe(document.body, { childList: true, subtree: true });
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
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
  }, [user.name, user.phone, isTestClient, voiceEnabled, inactiveTasks]);

  useEffect(() => {
    function onMsg(e) {
      if (e.data && typeof e.data.__owHeight === 'number') {
        setH(Math.max(600, Math.ceil(e.data.__owHeight)));
      }
      if (e.data && typeof e.data.__owScrollToOffset === 'number') {
        if (frameRef.current) {
          const iframeTop = frameRef.current.getBoundingClientRect().top + window.scrollY;
          const target = iframeTop + e.data.__owScrollToOffset - 80;
          window.scrollTo({ top: target, behavior: 'smooth' });
        }
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
    <div style={{ width: '100%', height: h, overflow: 'hidden' }}>
      <OrderFrame srcDoc={srcDoc} voiceEnabled={voiceEnabled} frameRef={frameRef} />
    </div>
  );
}

const OrderFrame = memo(function OrderFrame({ srcDoc, voiceEnabled, frameRef }) {
  return (
    <iframe
      key={`vb-${voiceEnabled}`}
      ref={frameRef}
      title="Place an Order"
      srcDoc={srcDoc}
      style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
    />
  );
});
