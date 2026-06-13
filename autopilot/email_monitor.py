"""
autopilot/email_monitor.py
────────────────────────────────────────────────────────────────────────────────
Gmail IMAP monitor.
Watches the AutoPilot Gmail inbox for task assignment emails from admin,
parses order IDs and task types, and enqueues them for execution.
────────────────────────────────────────────────────────────────────────────────
"""

import imaplib
import email
import re
import logging
from email.header import decode_header
from datetime import datetime
from typing import Optional

from autopilot import config

logger = logging.getLogger('autopilot.email_monitor')


def _decode_str(value) -> str:
    """Decode email header bytes/string safely."""
    if not value:
        return ''
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ''.join(result)


def _get_body(msg) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                charset = part.get_content_charset() or 'utf-8'
                return part.get_payload(decode=True).decode(charset, errors='replace')
    else:
        charset = msg.get_content_charset() or 'utf-8'
        return msg.get_payload(decode=True).decode(charset, errors='replace')
    return ''


def parse_assignment_email(subject: str, body: str) -> Optional[dict]:
    """
    Parse a task assignment email from admin.
    Expected subject format:
        [Deleqate] New Order Assigned: #ORDER_ID — TASK_TYPE

    Returns dict with keys: order_id, task_type, priority
    Returns None if email doesn't match expected format.
    """
    # Match subject line
    subject_pattern = r'\[Deleqate\].*?#(\d+).*?(?:—|-)\s*(\w+)'
    subject_match = re.search(subject_pattern, subject, re.IGNORECASE)

    if not subject_match:
        # Fallback: look for order ID anywhere in subject
        id_match = re.search(r'order[:\s#]+(\d+)', subject, re.IGNORECASE)
        if not id_match:
            return None
        order_id = int(id_match.group(1))
        task_type = 'unknown'
    else:
        order_id = int(subject_match.group(1))
        task_type = subject_match.group(2).lower()

    # Try to extract task type from body if not in subject
    if task_type == 'unknown':
        task_match = re.search(r'task[:\s]+([a-z_]+)', body, re.IGNORECASE)
        if task_match:
            task_type = task_match.group(1).lower()

    # Extract deadline if present
    deadline = None
    deadline_match = re.search(r'deadline[:\s]+(.+?)(?:\n|$)', body, re.IGNORECASE)
    if deadline_match:
        deadline = deadline_match.group(1).strip()

    # Extract priority
    priority = 'normal'
    if 'urgent' in body.lower() or 'urgent' in subject.lower():
        priority = 'urgent'
    elif 'rush' in body.lower():
        priority = 'rush'

    return {
        'order_id': order_id,
        'task_type': task_type,
        'deadline': deadline,
        'priority': priority,
        'received_at': datetime.utcnow().isoformat(),
    }


class GmailMonitor:
    """
    Connects to Gmail via IMAP SSL and watches for new task assignment emails.
    Uses Gmail App Password for authentication (not the login password).
    """

    IMAP_HOST = 'imap.gmail.com'
    IMAP_PORT = 993

    def __init__(self):
        self.email = config.AUTOPILOT_EMAIL
        self.app_password = config.AUTOPILOT_APP_PASSWORD
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """Establish IMAP connection. Returns True on success."""
        try:
            self._conn = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT)
            self._conn.login(self.email, self.app_password)
            logger.info(f"📬 Gmail connected: {self.email}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"❌ Gmail login failed: {e}")
            logger.error("   Check AUTOPILOT_EMAIL and AUTOPILOT_APP_PASSWORD in autopilot/.env")
            return False
        except Exception as e:
            logger.error(f"❌ Gmail connection error: {e}")
            return False

    def disconnect(self):
        """Close IMAP connection gracefully."""
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def fetch_new_assignments(self) -> list[dict]:
        """
        Fetch unread emails from admin and parse task assignments.
        Marks parsed emails as read so they are not processed twice.
        Returns list of assignment dicts.
        """
        if not self._conn:
            if not self.connect():
                return []

        assignments = []
        try:
            self._conn.select('INBOX')

            # Search for UNSEEN emails from admin
            search_criteria = f'(UNSEEN FROM "{config.ADMIN_EMAIL}")'
            status, data = self._conn.search(None, search_criteria)

            if status != 'OK' or not data[0]:
                return []

            msg_ids = data[0].split()
            logger.info(f"📬 Found {len(msg_ids)} new email(s) from admin")

            for msg_id in msg_ids:
                try:
                    # Fetch full message
                    status, msg_data = self._conn.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    subject = _decode_str(msg.get('Subject', ''))
                    body = _get_body(msg)

                    logger.debug(f"   Processing email: {subject}")

                    # Parse assignment
                    assignment = parse_assignment_email(subject, body)
                    if assignment:
                        assignments.append(assignment)
                        logger.info(f"   ✅ Parsed: Order #{assignment['order_id']} — {assignment['task_type']}")

                        # Mark as read (SEEN)
                        self._conn.store(msg_id, '+FLAGS', '\\Seen')
                    else:
                        logger.debug(f"   ⏭  Not an assignment email, skipping")

                except Exception as e:
                    logger.error(f"   ❌ Error processing email {msg_id}: {e}")
                    continue

        except imaplib.IMAP4.abort:
            # Connection dropped — reconnect next poll cycle
            logger.warning("⚠  IMAP connection dropped, will reconnect next cycle")
            self._conn = None
        except Exception as e:
            logger.error(f"❌ IMAP fetch error: {e}")

        return assignments

    def send_completion_report(self, order_id: int, task_type: str,
                                status: str, notes: str, deliverable_path: str = ''):
        """
        Send a completion report email to admin using Gmail SMTP.
        status: 'completed', 'qc_failed', 'error'
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        emoji_map = {
            'completed': '✅',
            'qc_failed': '⚠️',
            'error': '❌',
        }
        emoji = emoji_map.get(status, '📋')

        subject = f"[AutoPilot] {emoji} Order #{order_id} — {status.upper()} ({task_type})"

        body = f"""AutoPilot Task Report
{'=' * 50}

Order ID:   #{order_id}
Task Type:  {task_type}
Status:     {status.upper()}
Completed:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Notes:
{notes}

{'Deliverable: ' + deliverable_path if deliverable_path else ''}

---
This is an automated report from the Deleqate AutoPilot agent.
"""

        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = config.ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.email, self.app_password)
                smtp.sendmail(self.email, config.ADMIN_EMAIL, msg.as_string())
            logger.info(f"📤 Sent completion report to admin for Order #{order_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send completion email: {e}")
