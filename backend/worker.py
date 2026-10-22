"""Background worker — a separate process from Gunicorn (S013 § 5.5; base pattern § Job queue).

Each loop, every WORKER_POLL_SECONDS:
  1. ensure_schema() until it succeeds — the worker may run the migrations itself, and never
     touches the queue before the schema is up to date; while the database is down it
     retries every 30 s (CLAUDE.md "DB may not exist");
  2. ping its one dedicated connection (a new one after an idle night, which re-runs the IST
     init_command) and make sure it holds the singleton lock LOCK_WORKER — after a
     reconnect the lock is gone with the old session and is taken again before any work;
  3. requeue stale claims, enqueue the scheduled tasks now due, and run due tasks until none
     is left.

Each task takes three transactions (S013 BR2-02): the claim (committed, so the attempt
counts), the handler with mark_done, and on an exception mark_failed after the rollback.

SIGTERM/SIGINT: the current transaction finishes and the worker exits; a long handler
checks should_stop() between batches.

Run with:  python worker.py   (container: .venv/bin/python worker.py)
"""

import logging
import signal
import time
from datetime import datetime, timedelta, timezone

import pymysql

from company_settings import WORKER_POLL_SECONDS
from config import DB_CONFIG
from db_helpers import transaction
from local_db import LOCK_WORKER, describe_error, ensure_schema, get_local_db, is_connection_lost
from scheduled_tasks import SCHEDULE, due_tasks
from task_handlers import BadTask, run_task
from task_queue import claim_next, enqueue, last_enqueued, mark_done, mark_failed, requeue_stale

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")

# A fixed +05:30, as equipment.py: India has no daylight saving, and ZoneInfo would need the
# tzdata package on Windows
IST = timezone(timedelta(hours=5, minutes=30))

# While another worker holds the lock, say so this often
WAITING_LOG_SECONDS = 60


def now_ist():
    """Naive IST now — agrees with the session's NOW(), which runs at +05:30 (S013 § 4)."""
    return datetime.now(IST).replace(tzinfo=None)


class Worker:
    """One worker's state: its connection, whether it holds the lock, the stop flag."""

    def __init__(self, config, lock_name=LOCK_WORKER, clock=now_ist):
        self._config = config
        self._lock_name = lock_name
        self._clock = clock
        self.conn = None
        self.stopping = False
        self._waiting_logged_at = None

    def stop(self):
        self.stopping = True

    def should_stop(self):
        return self.stopping

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except pymysql.MySQLError:
                pass   # already gone: the server dropped the lock with the session
            self.conn = None

    # -- connection and lock -------------------------------------------------

    def connect(self):
        """Open the dedicated connection, or ping it and open a new one if it died (an idle
        night).  A new connection, not ping(reconnect=True), which PyMySQL deprecates; either
        way the IST init_command runs again and the lock is gone with the old session."""
        if self.conn is not None:
            try:
                self.conn.ping()
                return
            except pymysql.MySQLError:
                logger.warning("Worker connection lost; reconnecting")
                self.close()
        self.conn = get_local_db(self._config)

    def holds_lock(self):
        """Take or confirm the singleton lock, never waiting (GET_LOCK(..., 0)).  Asked each
        loop, it is also the check that the lock survived: a reconnected session has a new
        connection id and holds nothing."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT IS_USED_LOCK(%s) = CONNECTION_ID() AS mine", (self._lock_name,))
            if cur.fetchone()["mine"] == 1:
                return True
            cur.execute("SELECT GET_LOCK(%s, 0) AS got", (self._lock_name,))
            if cur.fetchone()["got"] == 1:
                logger.info("Worker lock %s taken", self._lock_name)
                self._waiting_logged_at = None
                return True
        if self._waiting_logged_at is None or time.monotonic() - self._waiting_logged_at >= WAITING_LOG_SECONDS:
            logger.info("Waiting for the worker lock %s (another worker holds it)", self._lock_name)
            self._waiting_logged_at = time.monotonic()
        return False

    # -- work ------------------------------------------------------------------

    def enqueue_scheduled(self):
        """Enqueue every scheduled task due now; returns their types."""
        with transaction(self.conn), self.conn.cursor() as cur:
            due = due_tasks(SCHEDULE, last_enqueued(cur, [t for t, _ in SCHEDULE]), self._clock())
            for task_type in due:
                enqueue(cur, task_type)
        for task_type in due:
            logger.info("Scheduled task %s enqueued", task_type)
        return due

    def run_one(self):
        """Claim and run one due task -> its id, or None when nothing is due."""
        task = claim_next(self.conn)
        if task is None:
            return None
        try:
            with transaction(self.conn), self.conn.cursor() as cur:
                run_task(self.conn, task, self.should_stop)
                mark_done(cur, task["id"])
        except pymysql.err.OperationalError as exc:
            if self._connection_lost(exc):
                self._log_lost(task, exc)
                raise   # the claim is requeued (or failed) once its lock expires
            self._task_failed(task, exc)   # e.g. deadlock, lock wait timeout: the connection is fine
            return task["id"]
        except Exception as exc:   # noqa: BLE001 — a failing task never stops the worker
            if not self.conn.open:   # the rollback itself failed on a dead connection
                self._log_lost(task, exc)
                raise
            self._task_failed(task, exc)
            return task["id"]
        logger.info("Task %s (%s) done", task["id"], task["task_type"])
        return task["id"]

    def _connection_lost(self, exc):
        """True for a real loss: the connection is closed, a client-side error code (2xxx:
        gone away, lost, can't connect) or the server shutting it down / killing the session.
        PyMySQL's OperationalError also covers deadlock (1213) and lock wait timeout (1205)."""
        code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else 0
        return not self.conn.open or is_connection_lost(code)

    @staticmethod
    def _log_lost(task, exc):
        """Name the real cause: a failed rollback on a dead connection raises its own error
        (often 'error 0'), which would hide the original one chained as __context__."""
        logger.error("Task %s (%s): connection lost, left for requeue_stale", task["id"],
                     task["task_type"], exc_info=exc)

    def _task_failed(self, task, exc):
        status = mark_failed(self.conn, task["id"], f"{type(exc).__name__}: {exc}",
                             retry=not isinstance(exc, BadTask))
        logger.error("Task %s (%s) attempt %d failed, now %s: %s", task["id"], task["task_type"],
                     task["attempts"], status, exc)

    def run_once(self):
        """One loop.  Returns False when nothing could be done (DB down, lock held elsewhere)."""
        if ensure_schema(self._config):
            return False   # ensure_schema logged it, and tries again after 30 s
        self.connect()
        if not self.holds_lock():
            return False
        with self.conn.cursor() as cur:
            requeued = requeue_stale(cur)
        if requeued:
            logger.warning("%d stale task(s) set back to pending or failed", requeued)
        self.enqueue_scheduled()
        while not self.stopping and self.run_one() is not None:
            pass
        return True


def main():
    worker = Worker(DB_CONFIG)

    def _stop(signum, _frame):
        logger.info("Received signal %s, stopping after the current transaction", signum)
        worker.stop()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Worker started")
    while not worker.stopping:
        try:
            worker.run_once()
        except pymysql.MySQLError as exc:
            logger.error("Worker: database error (%s); reconnecting next loop", describe_error(exc))
            worker.close()
        except Exception:   # noqa: BLE001 — an unexpected error never ends the worker
            logger.exception("Worker loop failed; retrying next loop")
            worker.close()
        deadline = time.monotonic() + WORKER_POLL_SECONDS
        while not worker.stopping and time.monotonic() < deadline:
            time.sleep(0.5)
    worker.close()
    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
