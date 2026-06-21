// Shared order-wizard widgets — direct ports of the template's chip groups,
// upload boxes (with drag-drop + paste), qty rows and price cards.
import { useEffect, useRef, useState } from 'react';

export function FormSection({ title, sub, children }) {
  return (
    <div className="form-section">
      <div className="form-section-title">{title} {sub && <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--gray-500)' }}>{sub}</span>}</div>
      {children}
    </div>
  );
}

let _chipSeq = 0;

// Radio chip group — `options` = [value, label][] or strings
export function Chips({ name, options, def, onChange, required }) {
  const base = useState(() => `chip${++_chipSeq}`)[0];
  return (
    <div className="chips">
      {options.map((o, i) => {
        const [value, label] = Array.isArray(o) ? o : [o, o];
        const id = `${base}-${i}`;
        return (
          <div className="chip" key={value}>
            <input type="radio" name={name} value={value} id={id} required={required && i === 0}
              defaultChecked={value === def} onChange={onChange ? e => onChange(e.target.value) : undefined} />
            <label htmlFor={id}>{label}</label>
          </div>
        );
      })}
    </div>
  );
}

// Checkbox chip group
export function CheckChips({ name, options, defs = [], onChange }) {
  const base = useState(() => `cchip${++_chipSeq}`)[0];
  return (
    <div className="check-chips">
      {options.map((o, i) => {
        const [value, label] = Array.isArray(o) ? o : [o, o];
        const id = `${base}-${i}`;
        return (
          <div className="check-chip" key={value}>
            <input type="checkbox" name={name} value={value} id={id}
              defaultChecked={defs.includes(value)}
              onChange={onChange ? e => onChange(value, e.target.checked) : undefined} />
            <label htmlFor={id}>{label}</label>
          </div>
        );
      })}
    </div>
  );
}

function injectFiles(input, files, multiple) {
  const accept = (input.getAttribute('accept') || '').toLowerCase();
  const filtered = Array.from(files).filter(f =>
    !(accept.indexOf('image/*') > -1 && !f.type.startsWith('image/')));
  if (!filtered.length) return false;
  const dt = new DataTransfer();
  if (multiple) Array.from(input.files || []).forEach(f => dt.items.add(f));
  filtered.forEach(f => dt.items.add(f));
  input.files = dt.files;
  return true;
}

// Upload box — single or multiple; drag-drop + clipboard paste like the original
export function UploadBox({ name, accept, icon, label, hint, required, multiple,
  style, labelStyle, compact }) {
  const inputRef = useRef(null);
  const [names, setNames] = useState([]);
  const [drag, setDrag] = useState(false);

  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }, [names]);

  function refresh() {
    const files = Array.from(inputRef.current?.files || []);
    setNames(files.map(f => f.name));
  }
  function onDrop(e) {
    e.preventDefault(); setDrag(false);
    const files = e.dataTransfer.files?.length ? e.dataTransfer.files
      : Array.from(e.dataTransfer.items || []).filter(i => i.kind === 'file').map(i => i.getAsFile());
    if (files && files.length && injectFiles(inputRef.current, files, multiple)) refresh();
  }
  function onPaste(e) {
    const items = (e.clipboardData || window.clipboardData)?.items || [];
    const files = [];
    for (const it of items) if (it.type.startsWith('image/')) { const f = it.getAsFile(); if (f) files.push(f); }
    if (files.length && injectFiles(inputRef.current, files, multiple)) { e.preventDefault(); refresh(); }
  }

  return (
    <div className={`upload-box ${names.length ? 'has-file' : ''} ${drag ? 'drag-over' : ''}`}
      style={style} tabIndex={0} onPaste={onPaste}
      onDragEnter={e => { e.preventDefault(); setDrag(true); }}
      onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; setDrag(true); }}
      onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget)) setDrag(false); }}
      onDrop={onDrop}>
      <input ref={inputRef} type="file" name={name} accept={accept} required={required}
        multiple={multiple} onChange={refresh} />
      <div className="upload-icon" style={compact ? { fontSize: '0.9rem', margin: 0 } : undefined}>{icon}</div>
      <div className="upload-label" style={{ ...(compact ? { fontSize: '0.75rem' } : {}), ...(labelStyle || {}) }}>{label}</div>
      {hint && <div className="upload-hint">{hint}</div>}
      {multiple ? (
        <div className="multi-file-list">
          {names.map((n, i) => (
            <span key={i} className="file-chip-item">
              <span className="fc-name" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <i data-lucide="paperclip" style={{ width: 12, height: 12 }}></i>
                <span>{n.length > 22 ? n.slice(0, 20) + '…' : n}</span>
              </span>
            </span>
          ))}
        </div>
      ) : (
        names[0] && <div className="file-shown" style={{ display: 'flex', alignItems: 'center', gap: '4px', ...(compact ? { fontSize: '0.68rem' } : {}) }}><i data-lucide="check" style={{ width: 12, height: 12, color: 'var(--success)' }}></i> {names[0]}</div>
      )}
      <div className="upload-drag-hint">drag &amp; drop or paste from clipboard</div>
    </div>
  );
}

// POV B / Moodboard styled upload variants used by VS & PR photo rows
export const povBStyle = { margin: 0, borderStyle: 'dashed', borderColor: '#f59e0b', background: '#fffbeb' };
export const moodStyle = { margin: 0, borderStyle: 'dashed', borderColor: '#6366f1', background: '#f5f3ff' };

export function QtyRow({ value, min, onChange, suffix }) {
  return (
    <div className="qty-row">
      <button type="button" className="qty-btn" onClick={() => onChange(Math.max(min, value - 1))}>−</button>
      <div className="qty-val">{value}</div>
      <button type="button" className="qty-btn" onClick={() => onChange(value + 1)}>+</button>
      <span style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>{suffix}</span>
    </div>
  );
}

export function PriceCard({ amount, breakdown, sla }) {
  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }, [sla]);
  return (
    <div className="price-card">
      <div className="price-amount">{amount}</div>
      <div className="price-breakdown">{breakdown}</div>
      <div className="price-sla" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <i data-lucide="clock" style={{ width: 14, height: 14 }}></i>
        <span>{sla}</span>
      </div>
    </div>
  );
}

export function FormGroup({ label, required, optional, hint, children, style }) {
  return (
    <div className="form-group" style={style}>
      {label && (
        <label className="form-label">
          {label} {required && <span className="required" style={{ color: 'var(--gold)' }}>*</span>}
          {optional && <span style={{ fontSize: '0.72rem', color: 'var(--gray-400)' }}> Optional</span>}
        </label>
      )}
      {children}
      {hint && <div style={{ fontSize: '0.72rem', color: 'var(--gray-400)', marginTop: '0.3rem' }}>{hint}</div>}
    </div>
  );
}
