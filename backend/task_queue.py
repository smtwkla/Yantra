"""The job queue — a task_queue table drained by worker.py (S013 § 5.5; base pattern § DB-backed queue).

- enqueue(cur, ...)        — add a task in the caller's transaction
- claim_next(conn)         — claim the next due task; its own committed transaction
- mark_done(cur, id)       — in the handler's transaction, committed with its work
- mark_failed(conn, ...)   — its own transaction: retry later with backoff, or failed
- requeue_stale(cur)       — running tasks whose lock expired (a dead worker) become pending, or failed
                              when their attempts are used up

Times are the session's IST NOW(), as every table (S013 § 4).
"""

import json

from company_settings import TASK_LOCK_MINUTES, TASK_RETRY_BACKOFF_MINUTES
from db_helpers import transaction

DEFAULT_MAX_ATTEMPTS = 3
# last_error is TEXT; a traceback-sized message is cut to this
_ERROR_CHARS = 2000


def enqueue(cur, task_type, payload=None, scheduled_for=None, max_attempts=DEFAULT_MAX_ATTEMPTS):
    """Add a task with the caller's cursor, so it commits or rolls back with the data that
    caused it.  ``scheduled_for`` None = due now.  Returns the task id."""
    cur.execute(
        "INSERT INTO task_queue (task_type, payload, scheduled_for, max_attempts) "
        "VALUES (%s, %s, COALESCE(%s, NOW()), %s)",
        (task_type, None if payload is None else json.dumps(payload), scheduled_for, max_attempts))
    return cur.lastrowid


def claim_next(conn):
    """Claim the oldest due pending task -> {id, task_type, payload, attempts, max_attempts},
    or None.  Committed on its own, so the attempt counts even if the handler then fails
    (S013 BR2-02).  SKIP LOCKED needs MariaDB 10.6 or later."""
    with transaction(conn), conn.cursor() as cur:
        cur.execute("SELECT id, task_type, payload, attempts, max_attempts FROM task_queue "
                    "WHERE status = 'pending' AND scheduled_for <= NOW() "
                    "ORDER BY scheduled_for, id LIMIT 1 FOR UPDATE SKIP LOCKED")
        task = cur.fetchone()
        if task is None:
            return None
        cur.execute("UPDATE task_queue SET status = 'running', attempts = attempts + 1, "
                    "locked_until = NOW() + INTERVAL %s MINUTE WHERE id = %s", (TASK_LOCK_MINUTES, task["id"]))
    task["attempts"] += 1
    if isinstance(task["payload"], str):
        task["payload"] = json.loads(task["payload"])
    return task


def mark_done(cur, task_id):
    cur.execute("UPDATE task_queue SET status = 'done', completed_at = NOW(), locked_until = NULL, "
                "last_error = NULL WHERE id = %s", (task_id,))


def mark_failed(conn, task_id, error, retry=True):
    """Store the error; back to pending after TASK_RETRY_BACKOFF_MINUTES x attempts while
    attempts < max_attempts (and ``retry``), else failed.  Works from the committed
    attempts, so a failing task can't retry for ever.  Returns the new status."""
    with transaction(conn), conn.cursor() as cur:
        cur.execute("SELECT attempts, max_attempts FROM task_queue WHERE id = %s FOR UPDATE", (task_id,))
        row = cur.fetchone()
        message = str(error)[:_ERROR_CHARS]
        if retry and row["attempts"] < row["max_attempts"]:
            cur.execute("UPDATE task_queue SET status = 'pending', locked_until = NULL, last_error = %s, "
                        "scheduled_for = NOW() + INTERVAL %s MINUTE WHERE id = %s",
                        (message, TASK_RETRY_BACKOFF_MINUTES * row["attempts"], task_id))
            return "pending"
        cur.execute("UPDATE task_queue SET status = 'failed', locked_until = NULL, last_error = %s, "
                    "completed_at = NOW() WHERE id = %s", (message, task_id))
        return "failed"


def requeue_stale(cur):
    """A running task whose lock has passed belongs to a worker that died mid-task: it is
    pending again, or failed when its attempts are used up (so a task that kills the worker
    every time can't retry for ever).  Returns how many tasks were touched."""
    cur.execute("UPDATE task_queue SET status = 'failed', locked_until = NULL, completed_at = NOW(), "
                "last_error = 'worker lost the task; attempts used up' "
                "WHERE status = 'running' AND locked_until < NOW() AND attempts >= max_attempts")
    failed = cur.rowcount
    cur.execute("UPDATE task_queue SET status = 'pending', locked_until = NULL "
                "WHERE status = 'running' AND locked_until < NOW()")
    return failed + cur.rowcount


def last_enqueued(cur, task_types):
    """{task_type: the last created_at, or None} — what the scheduler decides from."""
    result = dict.fromkeys(task_types)
    if task_types:
        cur.execute(f"SELECT task_type, MAX(created_at) AS last FROM task_queue "
                    f"WHERE task_type IN ({', '.join(['%s'] * len(task_types))}) GROUP BY task_type",
                    list(task_types))
        result.update({r["task_type"]: r["last"] for r in cur.fetchall()})
    return result
