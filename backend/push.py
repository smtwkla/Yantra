"""My notifications — a person's own devices for web push (docs/steps/S021-alerts-push/1-brief.md
§ 1.2, § 1.3, § 5.5, § 6), and the email channel's line and test (S032 § 1.5, § 5.8, § 6).

Every route needs push:subscribe (any logged-in role).  Alerts go to a person, so turning a
device on, listing and testing also need a Team record; removing a device by its endpoint
does not (sign-out removes this device whoever owns the row, BR3-03: presenting the
endpoint proves the caller holds the device, since nobody else has that address).

The VAPID public key is read from config at call time, not at import (BR3-11).  The email
address is the person's own, copied from the login (S032 § 5.4): shown only to its owner here.
"""

import logging

from flask import Blueprint, jsonify, request

import config
import mail_sender
import push_sender
from alerts import PUSH_SEND, PUSH_SEND_ATTEMPTS, enqueue_email, person_memberships, subscription_ids
from alerts_core import message_for_test, you_get
from email_core import email_for_test
from api_common import ApiError, actor, clean_body
from auth_utils import current_person_id, require_perm
from db_helpers import get_db, row_to_dict, transaction
from push_core import (
    BROWSER_CANNOT, TEST_TTL_SECONDS, device_label, endpoint_hash, is_endpoint_hash, refused_host, send_task_payload,
    validate_subscription,
)
from task_queue import enqueue

logger = logging.getLogger(__name__)

push_bp = Blueprint("push", __name__)

KEY = "push:subscribe"
NOT_IN_TEAM = "You are not in Team. Ask IT admin to add you."
NOT_SET_UP = "Notifications are not set up on this server yet. Ask IT admin."
TURN_ON_FIRST = "Turn notifications on first."
ENDPOINT_NEEDED = "endpoint is required"
EMAIL_NOT_SET_UP = "Email is not set up on this server yet. Ask IT admin."
NO_EMAIL_ADDRESS = "Your login has no email address. Ask IT admin to add an email address to your login."

_ROW = "SELECT id, label, created_at, last_sent_at, last_error, endpoint_hash FROM push_subscriptions"


def _device_out(row, this_hash):
    """A device as My devices shows it; the endpoint and keys never go back to the browser."""
    plain = row_to_dict(row)
    return {"id": plain["id"], "label": plain["label"], "created_at": plain["created_at"],
            "last_sent_at": plain["last_sent_at"], "last_error": plain["last_error"],
            "this_device": this_hash is not None and plain["endpoint_hash"] == this_hash}


def _own_person(cur):
    person_id = current_person_id(cur)
    if person_id is None:
        raise ApiError(NOT_IN_TEAM, 409)
    return person_id


def _email_of(cur, person_id):
    """The person's stored address, or None (S032 § 5.4)."""
    cur.execute("SELECT email FROM people WHERE id = %s", (person_id,))
    row = cur.fetchone()
    return row["email"] if row else None


@push_bp.route("/config")
@require_perm(KEY)
def get_config():
    """Whether push is set up, the public key the browser subscribes with, *What you will get*
    (BR2-06) from the person's memberships ([] without a Team record), and the email channel:
    set up or not, and the person's own address (S032 § 6; null without one)."""
    enabled = push_sender.enabled()
    address = None
    with get_db().cursor() as cur:
        person_id = current_person_id(cur)
        lines = you_get(person_memberships(cur, person_id)) if person_id is not None else []
        if person_id is not None:
            address = _email_of(cur, person_id)
    return jsonify({"enabled": enabled, "public_key": config.VAPID_PUBLIC_KEY if enabled else "", "you_get": lines,
                    "email": {"enabled": mail_sender.enabled(), "address": address}})


@push_bp.route("/subscriptions")
@require_perm(KEY)
def list_subscriptions():
    """Mine only.  ``endpoint_hash`` names this browser's device; anything that is not 64
    lowercase hex characters marks no row, never a 400 (BR3-15)."""
    raw = request.args.get("endpoint_hash")
    this_hash = raw if is_endpoint_hash(raw) else None
    with get_db().cursor() as cur:
        person_id = current_person_id(cur)
        rows = []
        if person_id is not None:
            cur.execute(f"{_ROW} WHERE person_id = %s ORDER BY created_at, id", (person_id,))
            rows = cur.fetchall()
    items = [_device_out(row, this_hash) for row in rows]
    return jsonify({"items": items, "total": len(items)})


@push_bp.route("/subscriptions", methods=["POST"])
@require_perm(KEY)
def subscribe():
    """Turn on this device: the browser's subscription, stored against the person (§ 5.5).  The
    same device again (same endpoint) moves to whoever signed in last, with fresh keys; a move
    starts its *added* time and last send afresh.  The label comes from the User-Agent header."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person_id = _own_person(cur)
        clean = clean_body(validate_subscription, creating=True)
        host = refused_host(clean["endpoint"])
        if host is not None:
            # The host only, never the address: a refused browser's service can be added later (BR3-05)
            logger.warning("Push subscription refused for %s: push service host %r is not allowed", actor(), host)
            raise ApiError(BROWSER_CANNOT, 400)
        digest = endpoint_hash(clean["endpoint"])
        cur.execute("SELECT person_id FROM push_subscriptions WHERE endpoint_hash = %s", (digest,))
        before = cur.fetchone()
        # created_at and last_sent_at are assigned before person_id, so they compare the old owner
        cur.execute(
            "INSERT INTO push_subscriptions (person_id, endpoint, endpoint_hash, p256dh, auth, label)"
            " VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE"
            " created_at = IF(person_id = VALUES(person_id), created_at, NOW()),"
            " last_sent_at = IF(person_id = VALUES(person_id), last_sent_at, NULL),"
            " person_id = VALUES(person_id), endpoint = VALUES(endpoint), p256dh = VALUES(p256dh),"
            " auth = VALUES(auth), label = VALUES(label), last_error = NULL",
            (person_id, clean["endpoint"], digest, clean["p256dh"], clean["auth"],
             device_label(request.headers.get("User-Agent"))))
        cur.execute(f"{_ROW} WHERE endpoint_hash = %s", (digest,))
        row = cur.fetchone()
    if before is not None and before["person_id"] != person_id:
        logger.info("Push device %s moved from person %s to person %s (%s)", row["id"], before["person_id"],
                    person_id, actor())
    return jsonify(_device_out(row, digest)), 201


@push_bp.route("/subscriptions/<int:subscription_id>", methods=["DELETE"])
@require_perm(KEY)
def remove_subscription(subscription_id):
    """Remove one of my devices.  Someone else's id is a 404, not a 403, so nobody can tell
    which ids exist."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person_id = current_person_id(cur)
        cur.execute("DELETE FROM push_subscriptions WHERE id = %s AND person_id = %s", (subscription_id, person_id))
        if cur.rowcount == 0:
            raise ApiError("Not found", 404)
    return "", 204


def _validate_endpoint(body, _creating):
    endpoint = body.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        return {}, [{"field": "endpoint", "message": ENDPOINT_NEEDED}]
    return {"endpoint": endpoint}, []


@push_bp.route("/subscriptions/remove", methods=["POST"])
@require_perm(KEY)
def remove_by_endpoint():
    """Sign-out and *Turn off*: this device's row goes, whoever owns it, so a phone that
    changes hands goes quiet (BR3-03).  204 also when there is none."""
    endpoint = clean_body(_validate_endpoint, creating=False)["endpoint"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute("SELECT id, person_id FROM push_subscriptions WHERE endpoint_hash = %s FOR UPDATE",
                    (endpoint_hash(endpoint),))
        row = cur.fetchone()
        if row is not None:
            cur.execute("DELETE FROM push_subscriptions WHERE id = %s", (row["id"],))
            logger.info("Push device %s (person %s) removed by its endpoint, by %s", row["id"], row["person_id"],
                        actor())
    return "", 204


@push_bp.route("/test", methods=["POST"])
@require_perm(KEY)
def send_test():
    """A test alert to every device of mine -> ``{devices: N}``; the worker sends it."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person_id = _own_person(cur)
        if not push_sender.enabled():
            raise ApiError(NOT_SET_UP, 409)
        devices = subscription_ids(cur, [person_id])
        if not devices:
            raise ApiError(TURN_ON_FIRST, 409)
        for subscription_id in devices:
            enqueue(cur, PUSH_SEND, send_task_payload(subscription_id, message_for_test(), TEST_TTL_SECONDS),
                    max_attempts=PUSH_SEND_ATTEMPTS)
    return jsonify({"devices": len(devices)})


@push_bp.route("/test-email", methods=["POST"])
@require_perm(KEY)
def send_test_email():
    """A test email to my own address -> ``{address}``, 202; the worker sends it (S032 § 1.5).
    Only to the caller's own address, so it cannot mail anyone else.  Refusals in order: not in
    Team, email not set up, no address (§ 5.8)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person_id = _own_person(cur)
        if not mail_sender.enabled():
            raise ApiError(EMAIL_NOT_SET_UP, 409)
        address = _email_of(cur, person_id)
        if not address:
            raise ApiError(NO_EMAIL_ADDRESS, 409)
        enqueue_email(cur, person_id, *email_for_test())
    return jsonify({"address": address}), 202
