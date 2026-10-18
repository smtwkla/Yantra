"""Task handlers — task_type -> handler(conn, payload, should_stop) (S013 § 5.5, § 5.6).

A handler runs inside the worker's transaction and commits nothing itself: the worker
commits its work together with mark_done, or rolls it back.  The one exception is a
batched delete such as the purge, which commits each batch (S013 § 5.6: one transaction
per batch, so stopping between batches loses nothing).  ``should_stop()`` is True once the
worker was asked to stop; a long handler checks it between batches.

Only internal, idempotent tasks retry automatically (base pattern); the purge is one.
"""

import logging

from company_settings import ACCESS_LOG_RETENTION_DAYS, DONE_TASK_RETENTION_DAYS, PURGE_BATCH_ROWS

logger = logging.getLogger(__name__)


class BadTask(Exception):
    """The task can't be run as given (unknown type, bad payload): failed at once, no retry."""


def _expect_no_payload(task_type, payload):
    if payload not in (None, {}):
        raise BadTask(f"{task_type} takes no payload, got {payload!r}")


def purge_access_log(conn, payload, should_stop):
    """Delete access-log rows older than ACCESS_LOG_RETENTION_DAYS, PURGE_BATCH_ROWS at a time,
    then done queue rows older than DONE_TASK_RETENTION_DAYS, keeping the last row of each
    task type (the scheduler reads it).  Failed rows are kept until someone handles them."""
    _expect_no_payload("purge_access_log", payload)
    deleted = 0
    while True:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM access_log WHERE ts < NOW() - INTERVAL %s DAY LIMIT %s",
                        (ACCESS_LOG_RETENTION_DAYS, PURGE_BATCH_ROWS))
            batch = cur.rowcount
        conn.commit()
        deleted += batch
        if batch < PURGE_BATCH_ROWS:
            break
        if should_stop():
            logger.info("purge_access_log: stopped after %d rows; the next run continues", deleted)
            return
    logger.info("purge_access_log: %d access-log rows older than %d days deleted", deleted, ACCESS_LOG_RETENTION_DAYS)

    with conn.cursor() as cur:
        # The ids to keep are read through a derived table, so they are worked out once
        cur.execute("DELETE FROM task_queue WHERE status = 'done' AND created_at < NOW() - INTERVAL %s DAY "
                    "AND id NOT IN (SELECT id FROM (SELECT MAX(id) AS id FROM task_queue GROUP BY task_type) AS keep)",
                    (DONE_TASK_RETENTION_DAYS,))
        logger.info("purge_access_log: %d done tasks older than %d days deleted", cur.rowcount,
                    DONE_TASK_RETENTION_DAYS)


HANDLERS = {
    "purge_access_log": purge_access_log,
}


def run_task(conn, task, should_stop):
    """Dispatch one claimed task to its handler.  An unknown type is a BadTask."""
    handler = HANDLERS.get(task["task_type"])
    if handler is None:
        raise BadTask(f"Unknown task type {task['task_type']!r}")
    handler(conn, task["payload"], should_stop)
