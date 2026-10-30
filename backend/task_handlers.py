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
with the back-off.  email_send (S032) has no row of its own to write on: its failure is kept in
task_queue.last_error and the log only.
"""

import logging
from datetime import datetime

import requests

import alerts
import mail_sender
import push_sender
from alerts_core import (
    ACTION_GIVEN, ACTION_OVERDUE, ASSIGNED, CHANNELS, EMAIL, ESCALATION, IMPROVEMENT_KINDS, PAYLOAD_DATE, PAYLOAD_TIME,
    PUSH, TICKET_KINDS, VERIFY_READY, improvement_message, message, overdue_alert_due, ready_alert_due,
    should_escalate, should_send, should_send_improvement,
)
from company_settings import ACCESS_LOG_RETENTION_DAYS, DONE_TASK_RETENTION_DAYS, PURGE_BATCH_ROWS
from improvements_core import watch_until
from push_core import (
    ALERT_TTL_SECONDS, GONE, IMPROVEMENT_TTL_SECONDS, REFUSED, RETRY_LATER, SENT, push_data, refused_host,
    send_outcome, send_task_payload,
)
from email_core import closed_email, smtp_outcome
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
# sends to one device, email_send (S032) to one person
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
    """One alert about a ticket -> its sends, by the kind's channels (S032 § 5.1): one push_send
    per device of each recipient, or one email_send per recipient with an address, in this
    transaction (all or nothing, so a retry never doubles it).  Sent only while the alert is
    still worth it (should_send); a channel not set up on the server is skipped."""
    ticket_id, event_id = _ids("ticket_alert", payload, "ticket_id", "event_id")
    kind = payload.get("kind")
    if kind not in TICKET_KINDS:
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
        if PUSH in CHANNELS[kind]:
            _push_fan_out(cur, kind, ticket, facts, payload, exclude)
        if EMAIL in CHANNELS[kind]:
            _email_fan_out(cur, kind, ticket, event_id, exclude)


def _push_fan_out(cur, kind, ticket, facts, payload, exclude):
    ticket_id = ticket["id"]
    if not push_sender.enabled():
        logger.info("ticket_alert %s for ticket %s: push is not set up, no channel", kind, ticket_id)
        return
    if kind == ASSIGNED:
        (person_id,) = _ids("ticket_alert", payload, "person_id")
        people = alerts.assignee(cur, ticket_id, person_id, exclude)
    else:
        people = alerts.recipients(cur, ticket, kind, exclude)
    devices = _push_to_people(cur, people, message(kind, facts, payload.get("minutes")), ALERT_TTL_SECONDS)
    logger.info("ticket_alert %s for ticket %s: %d people, %d devices", kind, ticket_id, len(people), devices)


def _push_to_people(cur, people, text, ttl):
    """The push fan-out every alert task shares (S074 D1): one push_send per device of these
    people, in the caller's transaction -> the number of devices."""
    devices = alerts.subscription_ids(cur, people)
    for subscription_id in devices:
        enqueue(cur, alerts.PUSH_SEND, send_task_payload(subscription_id, text, ttl),
                max_attempts=alerts.PUSH_SEND_ATTEMPTS)
    return len(devices)


def _email_fan_out(cur, kind, ticket, event_id, exclude):
    """The recipients with an address first; the email's extra facts are read only when there is
    one (BR1-15).  *Ticket closed* is the only kind on this channel, so its text is closed_email."""
    ticket_id = ticket["id"]
    if not mail_sender.enabled():
        logger.info("ticket_alert %s for ticket %s: email is not set up, no channel", kind, ticket_id)
        return
    people = alerts.recipients_with_email(cur, ticket, kind, exclude)
    if people:
        subject, body = closed_email(alerts.read_closed_facts(cur, ticket_id, event_id))
        for person_id in people:
            alerts.enqueue_email(cur, person_id, subject, body)
    logger.info("ticket_alert %s for ticket %s: %d emails", kind, ticket_id, len(people))


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


# ---------------------------------------------------------------------------
# Improvement alerts (S074, R05.5): improvement_alert sends one alert, improvement_alert_scan
# finds the overdue countermeasures and the ended watches once a day
# ---------------------------------------------------------------------------

def _payload_time(payload, key, fmt):
    """A payload date or time, written by alerts.enqueue_improvement_alert; else a BadTask."""
    try:
        return datetime.strptime(payload.get(key), fmt)
    except (TypeError, ValueError):
        raise BadTask(f"improvement_alert needs {key} as {fmt}, got {payload!r}") from None


def _improvement_payload(payload):
    """The validated payload -> ``(kind, improvement_id, action_id, expected, given_by)``;
    ``expected`` holds what should_send_improvement compares, parsed."""
    (improvement_id,) = _ids("improvement_alert", payload, "improvement_id")
    kind = payload.get("kind")
    if kind not in IMPROVEMENT_KINDS:
        raise BadTask(f"improvement_alert: unknown kind {kind!r}")
    if kind == VERIFY_READY:
        return kind, improvement_id, None, {"watch_until": _payload_time(payload, "watch_until", PAYLOAD_TIME)}, None
    (action_id,) = _ids("improvement_alert", payload, "action_id")
    if kind == ACTION_OVERDUE:
        return kind, improvement_id, action_id, {"due_date": _payload_time(payload, "due_date", PAYLOAD_DATE).date()}, None
    (person_id,) = _ids("improvement_alert", payload, "person_id")
    given_by = payload.get("given_by")
    if not isinstance(given_by, str):
        raise BadTask(f"improvement_alert needs given_by as text, got {payload!r}")
    return kind, improvement_id, action_id, {"person_id": person_id}, given_by


def improvement_alert(conn, payload, should_stop):
    """One alert about an improvement -> one push_send per device of each recipient (§ 5.3), in
    this transaction (all or nothing, so a retry never doubles them).  Sent only while still true
    (should_send_improvement, from the rows as they are now); push only (CHANNELS, D9)."""
    kind, improvement_id, action_id, expected, given_by = _improvement_payload(payload)
    with conn.cursor() as cur:
        found = alerts.read_alert_improvement(cur, improvement_id, action_id, given_by)
        if found is None:
            raise BadTask(f"improvement_alert: no improvement {improvement_id} with countermeasure {action_id}")
        row, action, facts = found
        watch_end = watch_until(row["watch_from"], row["watch_days"]) if row["watch_from"] else None
        if not should_send_improvement(kind, row["state"], watch_end, action, expected):
            logger.info("improvement_alert %s for %s: not sent, no longer true (improvement %s, countermeasure %s,"
                        " owner %s, due %s, watch end %s; payload expected %s)", kind, row["serial"], row["state"],
                        action["state"] if action else None, action["owner_id"] if action else None,
                        action["due_date"] if action else None, watch_end, expected)
            return
        if not push_sender.enabled():
            logger.info("improvement_alert %s for %s: push is not set up, no channel", kind, row["serial"])
            return
        people = alerts.improvement_recipients(cur, kind, row, action)
        devices = _push_to_people(cur, people, improvement_message(kind, facts), IMPROVEMENT_TTL_SECONDS)
    logger.info("improvement_alert %s for %s: %d people, %d devices", kind, row["serial"], len(people), devices)


def improvement_alert_scan(conn, payload, should_stop):
    """Daily (scheduled_tasks.SCHEDULE): queue *Countermeasure overdue* once per due date and
    *Ready to verify* once per watch end (§ 5.2), each with its marker (v40), all in the worker's
    one transaction: a fault rolls back the markers and the tasks together, and the retry finds
    the same candidates.  The markers are written even when push is off (D8).  Locks: alerts.py's
    docstring."""
    _expect_no_payload(alerts.IMPROVEMENT_SCAN, payload)
    overdue = ready = 0
    with conn.cursor() as cur:
        # The session clock (IST), as the queue's timestamps; SELECT NOW() reads no table, so the
        # candidates' read below still opens the transaction's snapshot
        cur.execute("SELECT NOW() AS now")
        now = cur.fetchone()["now"]
        today = now.date()
        for improvement_id, action_ids in alerts.scan_candidates(cur, today, now).items():
            improvement, actions = alerts.lock_for_scan(cur, improvement_id, action_ids)
            if improvement is None:
                continue
            if ready_alert_due(improvement["state"], improvement["watch_from"], improvement["watch_days"],
                               improvement["ready_alert_for"], now):
                end = watch_until(improvement["watch_from"], improvement["watch_days"])
                alerts.mark_ready_alerted(cur, improvement_id, end)
                alerts.enqueue_improvement_alert(cur, VERIFY_READY, improvement_id, watch_until=end)
                ready += 1
            for action in actions:
                if overdue_alert_due(action["state"], action["due_date"], action["overdue_alert_for"],
                                     improvement["state"], today):
                    alerts.mark_overdue_alerted(cur, action["id"], action["due_date"])
                    alerts.enqueue_improvement_alert(cur, ACTION_OVERDUE, improvement_id, action_id=action["id"],
                                                     due_date=action["due_date"])
                    overdue += 1
    logger.info("improvement_alert_scan: %d overdue, %d ready to verify", overdue, ready)


# push_subscriptions.last_error
_SUBSCRIPTION_ERROR_CHARS = 255

# What My devices shows as *Last error* (CR1-03): one plain line per outcome, what happened and
# what to do.  The technical text goes to task_queue.last_error and the log only.
DEVICE_REFUSED = "The last alert did not reach this device. Turn notifications off and on again on that device."
# True on every attempt: after the last of the 3 attempts nothing tries again (CR3-01)
DEVICE_LATE = "The push service did not take the last alert. It may be late or lost. Check your tickets."
DEVICE_NOT_SET_UP = "Notifications are not set up on this server yet. Ask IT admin."
DEVICE_FAULT = "The last alert could not be sent. Ask IT admin."


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
        _record_send_error(conn, subscription_id, DEVICE_REFUSED)
        raise NoRetry(f"subscription {subscription_id}: address not allowed")
    if not push_sender.enabled():
        _record_send_error(conn, subscription_id, DEVICE_NOT_SET_UP)
        raise NoRetry("push is not set up on this server")
    data = push_data(payload)
    try:
        status, retry_after = send(subscription, data, payload["urgency"], payload["ttl"])
    except requests.RequestException as exc:
        # A new exception without the original text: requests' messages carry the endpoint,
        # which identifies the device, and stays out of the logs and the task row
        text = f"Could not reach the push service ({type(exc).__name__})"
        _record_send_error(conn, subscription_id, DEVICE_LATE)
        raise RuntimeError(text) from None
    except Exception as exc:  # noqa: BLE001 — not a network fault, so a retry cannot fix it (CR1-02)
        # Typically a bad VAPID key or malformed device keys.  The message of pywebpush's own
        # errors does not carry the endpoint, so the cause stays in the log.
        logger.error("push_send: subscription %s could not be sent: %s: %s", subscription_id,
                     type(exc).__name__, exc)
        _record_send_error(conn, subscription_id, DEVICE_FAULT)
        raise NoRetry(f"push could not be sent ({type(exc).__name__})") from None
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
    _record_send_error(conn, subscription_id, DEVICE_REFUSED if outcome == REFUSED else DEVICE_LATE)
    if outcome == REFUSED:
        raise NoRetry(text)
    if outcome == RETRY_LATER:
        raise RetryLater(text, after_seconds)
    raise RuntimeError(text)


def email_send(conn, payload, should_stop, send=None):
    """Send one email to one person (S032 § 5.5).  The address is read now, never kept in the
    queue: no address any more, or an inactive person, is done.  A failure's meaning is
    email_core.smtp_outcome's; the text raised (and so task_queue.last_error and the log) holds
    the outcome and the SMTP code or the exception's type, never the address, the password or the
    body.  ``send`` is mail_sender.send unless a test passes a fake."""
    send = send or mail_sender.send
    (person_id,) = _ids("email_send", payload, "person_id")
    subject, body = payload.get("subject"), payload.get("body")
    if not isinstance(subject, str) or not isinstance(body, str):
        raise BadTask(f"email_send needs a subject and a body, for person {person_id}")
    with conn.cursor() as cur:
        cur.execute("SELECT email, active FROM people WHERE id = %s", (person_id,))
        person = cur.fetchone()
    if person is None or not person["active"] or not person["email"]:
        logger.info("email_send: person %s has no address now, or is inactive; nothing to send", person_id)
        return
    if not mail_sender.enabled():
        raise NoRetry("email is not set up on this server")
    try:
        send(person["email"], subject, body)
    except Exception as exc:  # noqa: BLE001 — smtp_outcome decides; str(exc) may carry the address
        retry, text = smtp_outcome(exc)
        logger.warning("email_send: person %s not sent: %s", person_id, text)
        if retry:
            raise RuntimeError(text) from None
        raise NoRetry(text) from None
    logger.info("email_send: sent to person %s", person_id)


HANDLERS = {
    "purge_access_log": purge_access_log,
    alerts.TICKET_ALERT: ticket_alert,
    alerts.TICKET_ESCALATE: ticket_escalate,
    alerts.IMPROVEMENT_ALERT: improvement_alert,
    alerts.IMPROVEMENT_SCAN: improvement_alert_scan,
    alerts.PUSH_SEND: push_send,
    alerts.EMAIL_SEND: email_send,
}


def run_task(conn, task, should_stop):
    """Dispatch one claimed task to its handler.  An unknown type is a BadTask."""
    handler = HANDLERS.get(task["task_type"])
    if handler is None:
        raise BadTask(f"Unknown task type {task['task_type']!r}")
    handler(conn, task["payload"], should_stop)
