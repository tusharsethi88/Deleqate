// api.js — single fetch wrapper for the Django backend.
// Session-cookie auth + CSRF token on every state-changing request,
// mirroring how the Flask templates submitted forms.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5051';

let csrfToken = null;

export async function bootstrapSession() {
  const r = await fetch(`${API_BASE}/api/session`, { credentials: 'include' });
  const d = await r.json();
  csrfToken = d.csrf_token;
  return d;
}

export function getCsrf() { return csrfToken; }

async function handle(r) {
  let d = {};
  try { d = await r.json(); } catch { /* non-JSON (file) responses */ }
  if (d.csrf_token) csrfToken = d.csrf_token;
  return { status: r.status, ...d };
}

export async function apiGet(path) {
  const r = await fetch(`${API_BASE}${path}`, { credentials: 'include' });
  return handle(r);
}

// JSON POST
export async function apiPost(path, data = {}) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(data),
  });
  return handle(r);
}

// multipart/form POST (file uploads, classic forms)
export async function apiPostForm(path, formData) {
  if (!(formData instanceof FormData)) {
    const fd = new FormData();
    Object.entries(formData).forEach(([k, v]) => fd.append(k, v));
    formData = fd;
  }
  const r = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  });
  return handle(r);
}

export function fileUrl(path) { return `${API_BASE}${path}`; }
