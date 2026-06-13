// The pilot's experience (dashboard + job workflow) is the original, data-rich
// set of templates rendered server-side by Django on the API host. We send the
// pilot there so they get the exact pre-migration UI, with all actions running
// same-origin against their session.
import { useEffect } from 'react';
import { API_BASE } from '../api.js';

export default function PilotDashboard() {
  useEffect(() => {
    window.location.replace(`${API_BASE}/pilot/dashboard`);
  }, []);
  return (
    <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--gray-500)', fontFamily: 'Inter, sans-serif' }}>
      Opening your dashboard…
    </div>
  );
}
