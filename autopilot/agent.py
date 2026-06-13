"""
autopilot/agent.py
────────────────────────────────────────────────────────────────────────────────
Deleqate AutoPilot — Main Orchestration Loop

This is the heart of the AutoPilot agent. Run it and it will:
1. Check Gmail every 5 minutes for new task assignments from admin
2. Fetch order details from the Deleqate platform
3. Download client uploads (photos, briefs)
4. Execute the task using the right executor (bg_cleanup, virtual_staging, etc.)
5. Run QC on all outputs
6. Upload deliverables to the platform
7. Email admin with a completion report
8. Post a heartbeat so admin can see the agent is alive

Usage:
    python -m autopilot.agent           # run forever
    python -m autopilot.agent --once    # process one task then exit
    python -m autopilot.agent --test    # test connectivity only
────────────────────────────────────────────────────────────────────────────────
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import argparse
import logging
import logging.handlers
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

# ── Setup logging before any other imports ────────────────────────────────────
def setup_logging(level=logging.INFO):
    from autopilot import config

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    # Rotating file handler (10MB per file, keep 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        str(config.LOG_FILE),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)


setup_logging()
logger = logging.getLogger('autopilot.agent')


# ── Now import everything else ─────────────────────────────────────────────────
from autopilot import config, task_queue
from autopilot.email_monitor import GmailMonitor
from autopilot.deleqate_client import DeleqateClient
from autopilot.browser_driver import BrowserDriver
from autopilot.qc import qc_engine


# ── Executor registry ──────────────────────────────────────────────────────────
def _get_executor(task_type: str):
    """Return the executor module for a given task type."""
    from autopilot.executors import bg_cleanup, virtual_staging, product_listing
    EXECUTORS = {
        'bg_cleanup':       bg_cleanup,
        'background_cleanup': bg_cleanup,
        'virtual_staging':  virtual_staging,
        'staging':          virtual_staging,
        'product_listing':  product_listing,
        'product':          product_listing,
    }
    return EXECUTORS.get(task_type.lower())


# ── Core task execution ────────────────────────────────────────────────────────

class AutoPilotAgent:
    """
    Main AutoPilot agent class.
    Manages the full lifecycle of task detection → execution → delivery.
    """

    def __init__(self):
        self.gmail    = GmailMonitor()
        self.deleqate = DeleqateClient()
        self.browser  = BrowserDriver()
        self._browser_started = False
        self._deleqate_logged_in = False

    def startup(self) -> bool:
        """Initialize all connections. Returns True if ready to work."""
        logger.info("=" * 60)
        logger.info("🤖 Deleqate AutoPilot starting up")
        logger.info(f"   Agent email:    {config.AUTOPILOT_EMAIL}")
        logger.info(f"   Deleqate URL:   {config.DELEQATE_BASE_URL}")
        logger.info(f"   Poll interval:  {config.EMAIL_POLL_INTERVAL}s")
        logger.info("=" * 60)

        # Validate config
        config_ok = config.validate()
        if not config_ok:
            logger.warning("⚠  Some config values missing — agent may have limited functionality")

        # Init task queue DB
        task_queue.init_queue()
        logger.info("✅ Task queue initialized")

        # Connect to Deleqate
        if self.deleqate.login():
            self._deleqate_logged_in = True
            logger.info("✅ Deleqate platform connected")
        else:
            logger.warning("⚠  Deleqate login failed — will retry on first task")

        # Start browser (non-headless so user can see and intervene)
        if self.browser.start(headless=False):
            self._browser_started = True
            logger.info("✅ Chrome browser started")

            # Ensure signed into Google
            if config.AUTOPILOT_EMAIL:
                self.browser.ensure_google_signed_in()
        else:
            logger.warning("⚠  Browser failed to start — tasks requiring browser will be skipped")

        return True

    def shutdown(self):
        """Clean up all connections."""
        logger.info("🛑 AutoPilot shutting down...")
        if self._browser_started:
            self.browser.stop()
        self.gmail.disconnect()
        logger.info("👋 AutoPilot stopped")

    def check_for_new_tasks(self) -> int:
        """Check Gmail and Deleqate API for new assignments and enqueue them. Returns count added."""
        assignments = []
        
        # 1. Check Gmail (if app password is set)
        if config.AUTOPILOT_APP_PASSWORD and config.AUTOPILOT_APP_PASSWORD != 'FILL_THIS_IN' and config.AUTOPILOT_APP_PASSWORD != '':
            logger.info("📬 Checking Gmail for new assignments...")
            assignments = self.gmail.fetch_new_assignments()
        else:
            logger.debug("📬 Gmail IMAP checking skipped (App Password not set in autopilot/.env)")
            
        # 2. Check Deleqate API directly
        logger.info("🔌 Checking Deleqate API for assigned orders...")
        try:
            api_orders = self.deleqate.get_assigned_orders()
            for o in api_orders:
                # Avoid duplicates: only add if not already in assignments list
                if not any(a['order_id'] == o['id'] for a in assignments):
                    assignments.append({
                        'order_id': o['id'],
                        'task_type': o['task_type'],
                        'priority': 'normal',
                        'deadline': o.get('deadline'),
                        'metadata': o,
                    })
        except Exception as e:
            logger.error(f"❌ Failed to check Deleqate API for assigned orders: {e}")

        count = 0
        for assignment in assignments:
            if task_queue.enqueue(
                order_id  = assignment['order_id'],
                task_type = assignment['task_type'],
                priority  = assignment['priority'],
                deadline  = assignment['deadline'],
                metadata  = assignment,
            ):
                count += 1

        if count:
            logger.info(f"📥 {count} new task(s) queued")
        else:
            logger.debug("   No new tasks")

        return count

    def process_next_task(self) -> bool:
        """
        Pop and execute the next queued task.
        Returns True if a task was processed, False if queue was empty.
        """
        task = task_queue.pop_next()
        if not task:
            return False

        order_id  = task['order_id']
        task_type = task['task_type']
        queue_id  = task['id']

        logger.info(f"\n{'─'*60}")
        logger.info(f"🚀 Executing task: Order #{order_id} — {task_type}")
        logger.info(f"{'─'*60}")

        try:
            # Fetch full order details
            order_data = self.deleqate.get_order_details(order_id)
            if not order_data:
                raise RuntimeError(f"Could not fetch order data for #{order_id}")

            # Fetch the dashboard workflow (exact per-room prompts + image roles)
            workflow = self.deleqate.get_workflow(order_id)
            if workflow and workflow.get('rooms'):
                order_data['workflow'] = workflow
                logger.info(f"   📋 Dashboard workflow loaded: {len(workflow['rooms'])} room(s)")
            # Give the executor access to the platform client (for the
            # Gemini room-reading → workflow DB → refined prompt loop)
            order_data['_deleqate_client'] = self.deleqate

            # Download all client uploads
            downloaded = self.deleqate.download_all_attachments(order_id, order_data)
            logger.info(f"   📁 Downloaded {len(downloaded)} file(s)")

            # Find the right executor
            executor = _get_executor(task_type)
            if not executor:
                raise RuntimeError(f"No executor for task type: {task_type}")

            # Output directory for this order's deliverables
            output_dir = config.OUTPUT_DIR / str(order_id)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Execute the task
            browser = self.browser if self._browser_started else None
            results = executor.execute(
                order_id=order_id,
                order_data=order_data,
                downloaded_files=downloaded,
                output_dir=output_dir,
                browser=browser,
            )

            if not results:
                raise RuntimeError("Executor produced no output files")

            logger.info(f"   📦 {len(results)} deliverable(s) produced")

            # Run QC on each deliverable
            qc_passed = True
            qc_notes_parts = []
            for item in results:
                file_path, pov_label = item[0], item[1]
                qc_result = qc_engine.run_qc(
                    file_path=file_path,
                    task_type=task_type,
                    order_data=order_data,
                    browser=browser,
                )
                qc_notes_parts.append(f"[{pov_label}] {qc_result.to_notes_string()}")
                if not qc_result.passed:
                    qc_passed = False
                    logger.warning(f"   ⚠  QC failed for {pov_label}: {qc_result.issues}")

            qc_notes = '\n'.join(qc_notes_parts)

            if not qc_passed:
                # QC failed — escalate to human pilot
                logger.warning(f"⚠  QC failed for Order #{order_id} — escalating")
                self.deleqate.mark_qc_failed(order_id, qc_notes)
                task_queue.mark_qc_failed(queue_id, qc_notes)
                self.gmail.send_completion_report(
                    order_id=order_id,
                    task_type=task_type,
                    status='qc_failed',
                    notes=f"QC failed — needs human review.\n\n{qc_notes}",
                )
                return True

            # Upload all deliverables — pass through (path, pov[, room label])
            delivery_pairs = list(results)
            upload_ok = self.deleqate.submit_multiple_deliverables(
                order_id=order_id,
                files=delivery_pairs,
                notes=executor.generate_notes(order_data, results),
            )

            if upload_ok:
                # Mark QC passed (triggers client notification)
                self.deleqate.mark_qc_passed(order_id, qc_notes)
                task_queue.mark_completed(queue_id, qc_notes)

                # Email admin
                self.gmail.send_completion_report(
                    order_id=order_id,
                    task_type=task_type,
                    status='completed',
                    notes=executor.generate_notes(order_data, results),
                    deliverable_path=', '.join(f.name for f, _ in results),
                )
                logger.info(f"✅ Order #{order_id} COMPLETE")
            else:
                raise RuntimeError("Failed to upload deliverables to platform")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"❌ Task failed: Order #{order_id} — {e}")
            logger.debug(f"   Full traceback:\n{traceback.format_exc()}")

            task_queue.mark_error(queue_id, error_msg[:500])

            # Email admin about the failure
            self.gmail.send_completion_report(
                order_id=order_id,
                task_type=task_type,
                status='error',
                notes=f"Error during execution:\n{str(e)[:500]}",
            )

        return True

    def run_forever(self):
        """Main loop — runs until interrupted."""
        self.startup()

        last_email_check = 0
        last_heartbeat   = 0

        logger.info("🟢 AutoPilot is ONLINE. Waiting for tasks...")
        logger.info(f"   Press Ctrl+C to stop gracefully")

        try:
            while True:
                now = time.time()

                # Heartbeat
                if now - last_heartbeat >= config.HEARTBEAT_INTERVAL:
                    self.deleqate.post_heartbeat()
                    stats = task_queue.get_queue_stats()
                    logger.info(f"💓 Heartbeat | Queue: {stats}")
                    last_heartbeat = now

                # Email check
                if now - last_email_check >= config.EMAIL_POLL_INTERVAL:
                    self.check_for_new_tasks()
                    last_email_check = now

                # Process tasks (drain queue)
                while self.process_next_task():
                    pass  # Keep processing until queue is empty

                # Sleep before next poll
                time.sleep(30)

        except KeyboardInterrupt:
            logger.info("\n⏹  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.shutdown()

    def run_once(self):
        """Process one task then exit."""
        self.startup()
        self.check_for_new_tasks()
        self.process_next_task()
        self.shutdown()

    def test_connectivity(self):
        """Test all connections and report status."""
        self.startup()
        logger.info("\n🧪 Connectivity Test Results:")
        logger.info(f"   Gmail:     {'✅' if self.gmail.connect() else '❌'}")
        logger.info(f"   Deleqate:  {'✅' if self.deleqate.login() else '❌'}")
        logger.info(f"   Browser:   {'✅' if self._browser_started else '❌'}")
        time.sleep(3)
        self.shutdown()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deleqate AutoPilot Agent')
    parser.add_argument('--once', action='store_true',
                        help='Process one task then exit')
    parser.add_argument('--test', action='store_true',
                        help='Test connectivity only')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    agent = AutoPilotAgent()

    if args.test:
        agent.test_connectivity()
    elif args.once:
        agent.run_once()
    else:
        agent.run_forever()
