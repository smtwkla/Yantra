"""Task handlers — task_type -> handler(conn, payload, should_stop) (S013 § 5.5, § 5.6).

A handler runs inside the worker's transaction and commits nothing itself: the worker
commits its work together with mark_done, or rolls it back.  The one exception is a
batched delete such as the purge, which commits each batch (S013 § 5.6: one transaction
per batch, so stopping between batches loses nothing).  ``should_stop()`` is True once the
worker was asked to stop; a long handler checks it between batches.

Only internal, idempotent tasks retry automatically (base pattern); the purge is one, and so
are the alert tasks (S021).

How a task reports its outcome (S021 § 5.1, decision 9; S023's telegram_send would follow it
too): a task that must keep a failure record on its own row (push_send: the subscription's
last_error) writes it and commits before it raises — the only write before the raise, on
every failed attempt, so it needs no attempt number.  That commit is the second documented
exception, beside the purge's.  The exception raised says what happens next: BadTask (the
task itself is malformed) and NoRetry (the other side refused it as given) fail at once;
RetryLater retries after its own delay (capped by mark_failed); any other exception retries
with the back-off.
"""

import logging

import alerts
import push_sender
from alerts_core import ASSIGNED, ESCALATION, KINDS, message, should_escalate, should_send
from company_settings import ACCESS_LOG_RETENTION_DAYS, DONE_TASK_RETENTION_DAYS, PURGE_BATCH_ROWS
from push_core import (
    ALERT_TTL_SECONDS, GONE, REFUSED, RETRY_LATER, SENT, push_data, refused_host, send_outcome, send_task_payload,
)
from task_queue import enqueue

logger = logging.getLogger(__name__)


class BadTask(Exception):
    """The task can't be run as given (unknown type, bad payload): failed at once, no retry."""


class NoRetry(Exception):
    """The other side refused the request as given (a push service's 400, 403, 413): failed at
    once, no retry."""


class RetryLater(Exception):
    """Retry after ``after_seconds`` instead of the back-off (a 429 with Retry-After).  It still
    counts against max_attempts; on the last attempt the task fails and the delay is ignored."""

    def __init__(self, message, after_seconds):
        super().__init__(message)
        self.after_seconds = after_seconds


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


# ---------------------------------------------------------------------------
# Alerts (S021 § 5.1): ticket_alert fans out, ticket_escalate checks then fans out, push_send
# sends to one device
# ---------------------------------------------------------------------------

def _ids(task_type, payload, *keys):
    """The payload's integer fields, in order; a missing or non-integer one is a BadTask."""
    if not isinstance(payload, dict):
        raise BadTask(f"{task_type} needs a payload, got {payload!r}")
    values = [payload.get(key) for key in keys]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise BadTask(f"{task_type} needs integers {', '.join(keys)}, got {payload!r}")
    return values


def ticket_alert(conn, payload, should_stop):
    """One alert about a ticket -> one push_send per device of each recipient, in this
    transaction (all or nothing, so a retry never doubles it).  Sent only while the alert is
    still worth it (should_send); with push not set up there is no channel, and it is done."""
    ticket_id, event_id = _ids("ticket_alert", payload, "ticket_id", "event_id")
    kind = payload.get("kind")
    if kind not in KINDS:
        raise BadTask(f"ticket_alert: unknown kind {kind!r}")
    exclude = payload.get("exclude_person_ids") or []
    with conn.cursor() as cur:
        found = alerts.read_alert_ticket(cur, ticket_id, event_id)
        if found is None:
            raise BadTask(f"ticket_alert: no ticket {ticket_id} with event {event_id}")
        ticket, facts = found
        if not should_send(kind, ticket["state"]):
            logger.info("ticket_alert %s for ticket %s not sent: the ticket is %s", kind, ticket_id, ticket["state"])
            return
        if not push_sender.enabled():
            logger.info("ticket_alert %s for ticket %s: push is not set up, no channel", kind, ticket_id)
            return
        if kind == ASSIGNED:
            (person_id,) = _ids("ticket_alert", payload, "person_id")
            people = alerts.assignee(cur, ticket_id, person_id, exclude)
        else:
            people = alerts.recipients(cur, ticket, kind, exclude)
        text = message(kind, facts, payload.get("minutes"))
        devices = alerts.subscription_ids(cur, people)
        for subscription_id in devices:
            enqueue(cur, alerts.PUSH_SEND, send_task_payload(subscription_id, text, ALERT_TTL_SECONDS),
                    max_attempts=alerts.PUSH_SEND_ATTEMPTS)
    logger.info("ticket_alert %s for ticket %s: %d people, %d devices", kind, ticket_id, len(people), len(devices))


def ticket_escalate(conn, payload, should_stop):
    """A breakdown still raised when its time is up escalates, once (§ 5.1).  The ticket row is
    locked, so a move at the same moment either commits first and is seen, or waits for this."""
    ticket_id, trigger_event_id, minutes = _ids("ticket_escalate", payload, "ticket_id", "trigger_event_id",
                                                "minutes")
    with conn.cursor() as cur:
        cur.execute("SELECT state, intensity FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
        ticket = cur.fetchone()
        if ticket is None:
            raise BadTask(f"ticket_escalate: no ticket {ticket_id}")
        latest = alerts.latest_critical_event_id(cur, ticket_id)
        if not should_escalate(ticket["state"], ticket["intensity"], latest, trigger_event_id):
            logger.info("ticket_escalate: ticket %s needs no escalation (%s, %s)", ticket_id, ticket["state"],
                        ticket["intensity"])
            return
        alerts.enqueue_ticket_alert(cur, ticket_id, ESCALATION, trigger_event_id, [], minutes=minutes)
    logger.info("ticket_escalate: ticket %s not acknowledged after %d min; escalated", ticket_id, minutes)


# push_subscriptions.last_error
_SUBSCRIPTION_ERROR_CHARS = 255


def _record_send_error(conn, subscription_id, text):
    """The device's last_error, committed now: the raise that follows rolls the worker's
    transaction back, and this record must stay (§ 5.1)."""
    with conn.cursor() as cur:
        cur.execute("UPDATE push_subscriptions SET last_error = %s WHERE id = %s",
                    (text[:_SUBSCRIPTION_ERROR_CHARS], subscription_id))
    conn.commit()


def push_send(conn, payload, should_stop, send=None):
    """Send one alert to one device; the push service's answer decides (push_core.send_outcome).
    ``send`` is push_sender.send unless a test passes a fake."""
    send = send or push_sender.send
    (subscription_id,) = _ids("push_send", payload, "subscription_id")
    with conn.cursor() as cur:
        cur.execute("SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE id = %s", (subscription_id,))
        subscription = cur.fetchone()
    if subscription is None:
        logger.info("push_send: subscription %s was removed; nothing to send", subscription_id)
        return
    # Checked again before the post: the address came from a browser (§ 5.4)
    if refused_host(subscription["endpoint"]) is not None:
        _record_send_error(conn, subscription_id, "Address not allowed")
        raise NoRetry(f"subscription {subscription_id}: address not allowed")
    if not push_sender.enabled():
        _record_send_error(conn, subscription_id, "Push is not set up on this server")
        raise NoRetry("push is not set up on this server")
    try:
        status, retry_after = send(subscription, push_data(payload), payload["urgency"], payload["ttl"])
    except Exception as exc:  # noqa: BLE001 — every failure to post is recorded, then retried
        # A new exception without the original text: requests' messages carry the endpoint,
        # which identifies the device, and stays out of the logs and the task row
        text = f"Could not reach the push service ({type(exc).__name__})"
        _record_send_error(conn, subscription_id, text)
        raise RuntimeError(text) from None
    outcome, after_seconds = send_outcome(status, retry_after)
    with conn.cursor() as cur:
        if outcome == SENT:
            cur.execute("UPDATE push_subscriptions SET last_sent_at = NOW(), last_error = NULL WHERE id = %s",
                        (subscription_id,))
            return
        if outcome == GONE:
            # The device unsubscribed, or its browser data was cleared (404, 410)
            cur.execute("DELETE FROM push_subscriptions WHERE id = %s", (subscription_id,))
            logger.info("push_send: subscription %s is gone (%s); removed", subscription_id, status)
            return
    text = f"Push service answered {status}"
    _record_send_error(conn, subscription_id, text)
    if outcome == REFUSED:
        raise NoRetry(text)
    if outcome == RETRY_LATER:
        raise RetryLater(text, after_seconds)
    raise RuntimeError(text)


HANDLERS = {
    "purge_access_log": purge_access_log,
    alerts.TICKET_ALERT: ticket_alert,
    alerts.TICKET_ESCALATE: ticket_escalate,
    alerts.PUSH_SEND: push_send,
}


def run_task(conn, task, should_stop):
    """Dispatch one claimed task to its handler.  An unknown type is a BadTask."""
    handler = HANDLERS.get(task["task_type"])
    if handler is None:
        raise BadTask(f"Unknown task type {task['task_type']!r}")
    handler(conn, task["payload"], should_stop)
