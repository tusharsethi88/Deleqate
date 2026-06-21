// The full pilot execution workflow is the original, data-rich template
// (pilot_sku_workflow.html) rendered server-side by Django. We send the pilot
// straight to it on the API host, where its per-step actions (/api/pilot/*) run
// same-origin with the pilot's session. This restores the pre-migration UI 1:1.
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE } from '../api.js';

export default function PilotExecute() {
  const { orderId } = useParams();
  useEffect(() => {
    window.location.replace(`${API_BASE}/pilot/execute/${orderId}`);
  }, [orderId]);
  return (
    <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--gray-500)', fontFamily: 'Inter, sans-serif' }}>
      Opening job workflow…
    </div>
  );
}
