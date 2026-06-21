"""
autopilot/deleqate_client.py
────────────────────────────────────────────────────────────────────────────────
HTTP client for the Deleqate platform.
Logs in as the AutoPilot pilot, fetches orders, downloads attachments,
and uploads deliverables — all through the existing Flask routes.
────────────────────────────────────────────────────────────────────────────────
"""

import os
import logging
import requests
from pathlib import Path
from typing import Optional

from autopilot import config

logger = logging.getLogger('autopilot.deleqate_client')


class DeleqateClient:
    """
    Stateful HTTP client for the Deleqate platform.
    Maintains a session cookie after login so subsequent calls stay authenticated.
    """

    def __init__(self):
        self.base_url = config.DELEQATE_BASE_URL.rstrip('/')
        self.session  = requests.Session()
        self.session.headers.update({'User-Agent': 'DeleqateAutoPilot/1.0'})
        self._logged_in = False

    # ── Authentication ─────────────────────────────────────────────────────────

    def login(self) -> bool:
        """
        Log in to Deleqate as the AutoPilot pilot account.
        Must be called before any other method.
        """
        try:
            # First GET the login page to retrieve the CSRF token
            get_resp = self.session.get(f'{self.base_url}/login', timeout=15)
            import re
            m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', get_resp.text)
            if not m:
                m = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', get_resp.text)
            csrf_token = m.group(1) if m else ''

            resp = self.session.post(
                f'{self.base_url}/login',
                data={
                    'email':    config.AUTOPILOT_EMAIL,
                    'password': config.AUTOPILOT_PILOT_PASSWORD,
                    'login_type': 'pilot',
                    'csrf_token': csrf_token,
                },
                allow_redirects=True,
                timeout=15,
            )
            # After login, Flask redirects to /pilot_dashboard on success
            # or stays on /login on failure
            if '/pilot' in resp.url or resp.status_code == 200:
                # Verify by checking if we can hit the dashboard
                check = self.session.get(f'{self.base_url}/pilot/dashboard', timeout=10)
                if check.status_code == 200 and 'pilot' in check.text.lower():
                    self._logged_in = True
                    logger.info("🔑 Logged in to Deleqate as AutoPilot pilot")
                    return True

            logger.error("❌ Deleqate login failed — check AUTOPILOT_PILOT_PASSWORD")
            logger.error(f"   Response URL: {resp.url}, Status: {resp.status_code}")
            return False

        except requests.RequestException as e:
            logger.error(f"❌ Deleqate login network error: {e}")
            logger.error(f"   Is Deleqate running at {self.base_url}?")
            return False

    def _ensure_logged_in(self) -> bool:
        """Auto-login if session expired."""
        if not self._logged_in:
            return self.login()
        return True

    # ── Order data ─────────────────────────────────────────────────────────────

    def get_assigned_orders(self) -> list[dict]:
        """
        Fetch orders currently assigned to the AutoPilot pilot via the API.
        Uses the /api/autopilot/pending_orders endpoint (added to app.py).
        """
        if not self._ensure_logged_in():
            return []
        try:
            resp = self.session.get(
                f'{self.base_url}/api/autopilot/pending_orders',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get('orders', [])
            logger.warning(f"⚠  pending_orders returned {resp.status_code}: {resp.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching pending orders: {e}")
            return []

    def get_workflow(self, order_id: int) -> Optional[dict]:
        """
        Fetch the dashboard workflow for an order: per-room exact prompts and
        POV A / POV B / moodboard attachment mapping. Same content a human
        pilot sees on the Execute Job page.
        """
        if not self._ensure_logged_in():
            return None
        try:
            resp = self.session.get(
                f'{self.base_url}/api/autopilot/workflow/{order_id}',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"⚠  workflow endpoint returned {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching workflow for order {order_id}: {e}")
            return None

    def submit_spatial_analysis(self, order_id: int, room_label: str,
                                gemini_text: str, pov: str = 'A') -> Optional[str]:
        """
        Post Gemini's room reading back to the platform (workflow DB).
        Returns the refined final Flow prompt, or None on failure.
        """
        if not self._ensure_logged_in():
            return None
        try:
            resp = self.session.post(
                f'{self.base_url}/api/autopilot/spatial/{order_id}',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                json={'room_label': room_label, 'pov': pov, 'gemini_text': gemini_text},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get('prompt')
            logger.warning(f"⚠  spatial endpoint returned {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"❌ Error submitting spatial analysis: {e}")
            return None

    def get_order_details(self, order_id: int) -> Optional[dict]:
        """
        Fetch full order details including intake data, attachments, client info.
        """
        if not self._ensure_logged_in():
            return None
        try:
            resp = self.session.get(
                f'{self.base_url}/api/autopilot/order/{order_id}',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"❌ Order {order_id} details returned {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching order {order_id}: {e}")
            return None

    def download_attachment(self, order_id: int, filename: str,
                             dest_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Download an attachment (client upload) from the order.
        Saves to dest_dir (defaults to autopilot/downloads/<order_id>/).
        Returns the saved file Path or None on failure.
        """
        if not self._ensure_logged_in():
            return None

        if dest_dir is None:
            dest_dir = config.DOWNLOAD_DIR / str(order_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # filename may include a subfolder (e.g. "order_3_20260612/file.jpg");
        # save locally with just the base name, request with the full relative path.
        dest_path = dest_dir / Path(filename).name
        try:
            resp = self.session.get(
                f'{self.base_url}/api/autopilot/download/{order_id}/{filename}',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                stream=True,
                timeout=60,
                allow_redirects=False,
            )
            ctype = resp.headers.get('Content-Type', '')
            if resp.status_code == 200 and 'text/html' not in ctype:
                with open(dest_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.debug(f"   ⬇  Downloaded: {filename} → {dest_path}")
                return dest_path

            logger.error(f"❌ Download failed for {filename}: {resp.status_code} ({ctype})")
            return None
        except Exception as e:
            logger.error(f"❌ Download error for {filename}: {e}")
            return None

    def download_all_attachments(self, order_id: int, order_data: dict) -> list[Path]:
        """
        Download all attachments for an order.
        Returns list of local file Paths.
        """
        attachments = order_data.get('attachments', [])
        paths = []
        for att in attachments:
            filename = att.get('filename') or att.get('original_name', '')
            if filename:
                path = self.download_attachment(order_id, filename)
                if path:
                    paths.append(path)
        logger.info(f"   ⬇  Downloaded {len(paths)}/{len(attachments)} attachments for Order #{order_id}")
        return paths

    # ── Deliverable submission ──────────────────────────────────────────────────

    def submit_deliverable(self, order_id: int, file_path: Path,
                            notes: str = '', pov: str = 'A',
                            file_label: str = '') -> bool:
        """
        Upload a completed deliverable file to the order.
        Uses the autopilot deliver endpoint. file_label = room label
        (e.g. 'Living Room') so the dashboard maps the render to its room.
        """
        if not self._ensure_logged_in():
            return False

        if not file_path.exists():
            logger.error(f"❌ Deliverable file not found: {file_path}")
            return False

        try:
            with open(file_path, 'rb') as f:
                resp = self.session.post(
                    f'{self.base_url}/api/autopilot/deliver/{order_id}',
                    headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                    files={'file': (file_path.name, f, 'application/octet-stream')},
                    data={'notes': notes, 'pov': pov, 'file_label': file_label},
                    timeout=120,
                )

            if resp.status_code == 200:
                logger.info(f"   ✅ Deliverable uploaded for Order #{order_id}: {file_path.name}")
                return True
            else:
                logger.error(f"❌ Deliverable upload failed: {resp.status_code} — {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"❌ Deliverable upload error: {e}")
            return False

    def submit_multiple_deliverables(self, order_id: int,
                                      files: list, notes: str = '') -> bool:
        """Submit multiple deliverable files.
        Each item: (path, pov) or (path, pov, room_label)."""
        success_count = 0
        for i, item in enumerate(files):
            file_path, pov = item[0], item[1]
            label = item[2] if len(item) > 2 else ''
            pov_label = pov or chr(ord('A') + i)
            if self.submit_deliverable(order_id, file_path, notes=notes,
                                       pov=pov_label, file_label=label):
                success_count += 1
        logger.info(f"   📦 Submitted {success_count}/{len(files)} deliverables for Order #{order_id}")
        return success_count > 0

    def mark_qc_passed(self, order_id: int, qc_notes: str = '') -> bool:
        """Signal that QC passed — triggers client notification."""
        return self._post_status(f'/api/autopilot/qc_pass/{order_id}', {'notes': qc_notes})

    def mark_qc_failed(self, order_id: int, qc_notes: str = '') -> bool:
        """Signal QC failure — escalates to human pilot review."""
        return self._post_status(f'/api/autopilot/qc_fail/{order_id}', {'notes': qc_notes})

    def post_heartbeat(self) -> bool:
        """Post a heartbeat so admin can see the agent is alive."""
        return self._post_status('/api/autopilot/heartbeat', {
            'status': 'online',
            'email': config.AUTOPILOT_EMAIL,
        })

    def _post_status(self, path: str, data: dict) -> bool:
        if not self._ensure_logged_in():
            return False
        try:
            resp = self.session.post(
                f'{self.base_url}{path}',
                headers={'X-AutoPilot-Token': config.AUTOPILOT_API_TOKEN},
                json=data,
                timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"❌ POST {path} error: {e}")
            return False
