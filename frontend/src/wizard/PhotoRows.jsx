// Dynamic labeled photo rows (POV A + POV B + per-room moodboard) used by
// Virtual Staging and Property Reel — port of addVsPhotoRow / addPrPhotoRow.
import { useState } from 'react';
import { UploadBox, povBStyle, moodStyle } from './widgets.jsx';

export const VS_ROOM_OPTIONS = ['Living Room', 'Living + Dining (Combined)', 'Dining Area', 'Kitchen',
  'Master Bedroom', 'Master Bathroom', 'Bedroom 2', 'Bedroom 3', 'Bedroom 4', 'Bathroom', 'Balcony',
  'Terrace', 'Study / Home Office', 'Lobby / Entrance', 'Exterior / Facade', 'Amenity (Pool / Gym)', 'Other'];

export const PR_AREA_OPTIONS = ['Exterior / Facade', 'Living Room', 'Living + Dining (Combined)', 'Dining Area',
  'Kitchen', 'Master Bedroom', 'Master Bathroom', 'Bedroom 2', 'Bedroom 3', 'Bedroom 4', 'Bathroom', 'Balcony',
  'Terrace', 'Study / Home Office', 'Lobby / Entrance', 'Amenity (Pool / Gym / Clubhouse)', 'Other'];

const headRow = (col1, optionalB) => (
  <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr 1fr 1fr', gap: '0.5rem', marginBottom: '0.35rem', padding: '0 0.1rem' }}>
    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>{col1}</div>
    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>📷 POV A — Main angle</div>
    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase' }}>📐 POV B — Second angle <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>optional</span></div>
    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#6366f1', textTransform: 'uppercase' }}>🎨 Moodboard <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>optional</span></div>
  </div>
);

export default function PhotoRows({ kind, onCountChange }) {
  // kind: 'vs' (max 12, required POV A) | 'pr' (max 15)
  const vs = kind === 'vs';
  const options = vs ? VS_ROOM_OPTIONS : PR_AREA_OPTIONS;
  const max = vs ? 12 : 15;
  const [rows, setRows] = useState([0]);
  const [nextId, setNextId] = useState(1);

  function add() {
    if (rows.length >= max) return;
    const next = [...rows, nextId];
    setNextId(nextId + 1);
    setRows(next);
    onCountChange?.(next.length);
  }
  function remove(id) {
    const next = rows.filter(r => r !== id);
    setRows(next);
    onCountChange?.(next.length);
  }

  const labelName = vs ? 'room_labels[]' : 'property_photos_label[]';
  const aName = vs ? 'room_photos[]' : 'property_photos';
  const bName = vs ? 'room_photos_b[]' : 'property_photos_b';
  const mName = vs ? 'room_moodboards[]' : 'property_moodboards';

  return (
    <>
      {headRow(vs ? 'Room' : 'Area')}
      {rows.map((id, i) => (
        <div key={id} style={{ display: 'grid', gridTemplateColumns: i === 0 ? '160px 1fr 1fr 1fr' : '160px 1fr 1fr 1fr auto', gap: '0.5rem', marginBottom: '0.6rem', alignItems: 'start' }}>
          <select name={labelName} className="form-control" style={{ marginTop: 0 }} required={vs}>
            {options.map(o => <option key={o}>{o}</option>)}
          </select>
          <UploadBox name={aName} accept="image/*" icon="📷" label="Upload" compact
            required={vs} style={{ margin: 0 }} />
          <UploadBox name={bName} accept="image/*" icon="📐" label="Upload (optional)" compact
            style={povBStyle} labelStyle={{ color: '#92400e' }} />
          <UploadBox name={mName} accept="image/*,.pdf" icon="🎨" label="Upload Moodboard (optional)" compact
            style={moodStyle} labelStyle={{ color: '#4f46e5' }} />
          {i > 0 && (
            <button type="button" onClick={() => remove(id)} aria-label="Remove"
              style={{ marginTop: 6, background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1rem', lineHeight: 1 }}>✕</button>
          )}
        </div>
      ))}
      <button type="button" onClick={add}
        style={{ fontSize: '0.8rem', color: 'var(--navy)', border: '1px dashed var(--gray-300)', background: 'none', padding: '0.4rem 1rem', borderRadius: 20, cursor: 'pointer', marginTop: '0.25rem' }}>
        + Add another {vs ? 'room' : 'area'}
      </button>
    </>
  );
}
