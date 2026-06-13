"""
autopilot/task_queue.py
────────────────────────────────────────────────────────────────────────────────
SQLite-based task queue for the AutoPilot.
Persists tasks between restarts so nothing is lost if the agent crashes.
────────────────────────────────────────────────────────────────────────────────
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from autopilot import config

logger = logging.getLogger('autopilot.queue')

# Task status values
STATUS_QUEUED     = 'queued'
STATUS_PROCESSING = 'processing'
STATUS_COMPLETED  = 'completed'
STATUS_QC_FAILED  = 'qc_failed'
STATUS_ERROR      = 'error'
STATUS_ESCALATED  = 'escalated'  # Handed off to human pilot


def _get_conn():
    conn = sqlite3.connect(config.QUEUE_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_queue():
    """Create the task queue table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS task_queue (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id      INTEGER NOT NULL UNIQUE,
                task_type     TEXT NOT NULL,
                priority      TEXT DEFAULT 'normal',
                deadline      TEXT,
                status        TEXT DEFAULT 'queued',
                retry_count   INTEGER DEFAULT 0,
                max_retries   INTEGER DEFAULT 2,
                error_msg     TEXT,
                qc_notes      TEXT,
                metadata      TEXT,   -- JSON blob with extra data
                queued_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at    TIMESTAMP,
                completed_at  TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON task_queue(status)
        ''')


def enqueue(order_id: int, task_type: str, priority: str = 'normal',
            deadline: str = None, metadata: dict = None) -> bool:
    """
    Add a task to the queue. Returns True if added, False if already queued.
    """
    try:
        with _get_conn() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO task_queue
                    (order_id, task_type, priority, deadline, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, task_type, priority, deadline,
                  json.dumps(metadata or {})))
            if conn.total_changes > 0:
                logger.info(f"   📥 Queued: Order #{order_id} — {task_type} [{priority}]")
                return True
            else:
                logger.debug(f"   ⏭  Order #{order_id} already in queue")
                return False
    except Exception as e:
        logger.error(f"❌ Queue error enqueuing Order #{order_id}: {e}")
        return False


def pop_next() -> Optional[dict]:
    """
    Get the next task to process (highest priority first, then oldest).
    Returns the task as a dict, or None if queue is empty.
    Marks the task as 'processing'.
    """
    priority_order = {'urgent': 0, 'rush': 1, 'normal': 2}

    with _get_conn() as conn:
        rows = conn.execute('''
            SELECT * FROM task_queue
            WHERE status = 'queued' AND retry_count <= max_retries
            ORDER BY queued_at ASC
        ''').fetchall()

        if not rows:
            return None

        # Sort by priority
        rows_sorted = sorted(rows, key=lambda r: priority_order.get(r['priority'], 2))
        task = dict(rows_sorted[0])

        # Mark as processing
        conn.execute('''
            UPDATE task_queue
            SET status = 'processing', started_at = ?
            WHERE id = ?
        ''', (datetime.utcnow().isoformat(), task['id']))

        task['metadata'] = json.loads(task.get('metadata') or '{}')
        logger.info(f"   🔄 Processing: Order #{task['order_id']} — {task['task_type']}")
        return task


def mark_completed(queue_id: int, qc_notes: str = ''):
    """Mark a task as successfully completed."""
    with _get_conn() as conn:
        conn.execute('''
            UPDATE task_queue
            SET status = 'completed', completed_at = ?, qc_notes = ?
            WHERE id = ?
        ''', (datetime.utcnow().isoformat(), qc_notes, queue_id))


def mark_error(queue_id: int, error_msg: str, retry: bool = True):
    """Mark a task as failed. If retry=True and retries remain, re-queues it."""
    with _get_conn() as conn:
        task = conn.execute('SELECT * FROM task_queue WHERE id = ?', (queue_id,)).fetchone()
        if not task:
            return

        new_retry_count = task['retry_count'] + 1
        if retry and new_retry_count <= task['max_retries']:
            # Re-queue with incremented retry count
            conn.execute('''
                UPDATE task_queue
                SET status = 'queued', retry_count = ?, error_msg = ?
                WHERE id = ?
            ''', (new_retry_count, error_msg, queue_id))
            logger.warning(f"   ♻  Retry {new_retry_count}/{task['max_retries']} for Order #{task['order_id']}")
        else:
            conn.execute('''
                UPDATE task_queue
                SET status = 'error', error_msg = ?, completed_at = ?
                WHERE id = ?
            ''', (error_msg, datetime.utcnow().isoformat(), queue_id))
            logger.error(f"   ❌ Task failed permanently: Order #{task['order_id']} — {error_msg}")


def mark_qc_failed(queue_id: int, qc_notes: str):
    """Mark QC as failed — escalate to human pilot."""
    with _get_conn() as conn:
        conn.execute('''
            UPDATE task_queue
            SET status = 'escalated', qc_notes = ?, completed_at = ?
            WHERE id = ?
        ''', (qc_notes, datetime.utcnow().isoformat(), queue_id))


def get_queue_stats() -> dict:
    """Return queue statistics for the heartbeat/admin dashboard."""
    with _get_conn() as conn:
        stats = {}
        for status in [STATUS_QUEUED, STATUS_PROCESSING, STATUS_COMPLETED,
                       STATUS_ERROR, STATUS_QC_FAILED, STATUS_ESCALATED]:
            count = conn.execute(
                'SELECT COUNT(*) FROM task_queue WHERE status = ?', (status,)
            ).fetchone()[0]
            stats[status] = count
        return stats


def get_active_tasks() -> list[dict]:
    """Return tasks currently being processed."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM task_queue WHERE status = 'processing'"
        ).fetchall()
        return [dict(r) for r in rows]
