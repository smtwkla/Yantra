"""The one place that calls pywebpush (S021 § 3, § 7 decision 3): RFC 8291 encryption and the
RFC 8292 VAPID signature, then one POST to the device's push service.

The keys are read from config at call time, not at import (BR3-11): the pytest fixture and
the e2e backend set config.VAPID_* after import.  The push_send handler takes ``send`` as a
parameter, so tests pass a fake instead of posting anywhere.
"""

import json

from pywebpush import WebPushException, webpush

import config
from company_settings import PUSH_TIMEOUT_SECONDS


def enabled():
    """Push is set up when all three VAPID values are present (§ 3: empty means off)."""
    return bool(config.VAPID_PUBLIC_KEY and config.VAPID_PRIVATE_KEY and config.VAPID_SUBJECT)


def send(subscription, data, urgency, ttl):
    """Post ``data`` (a dict, sent as JSON) to one device -> ``(status, retry_after)``: the push
    service's HTTP status and its Retry-After header (or None).  A timeout or a connection
    error raises (requests' exceptions); the caller records it and lets the queue retry."""
    try:
        response = webpush(
            subscription_info={"endpoint": subscription["endpoint"],
                               "keys": {"p256dh": subscription["p256dh"], "auth": subscription["auth"]}},
            data=json.dumps(data),
            vapid_private_key=config.VAPID_PRIVATE_KEY,
            # A new dict each call: webpush writes aud and exp into the one it is given
            vapid_claims={"sub": config.VAPID_SUBJECT},
            ttl=ttl,
            headers={"Urgency": urgency},
            timeout=PUSH_TIMEOUT_SECONDS,
        )
    except WebPushException as exc:
        # webpush raises on any status above 202; the answer itself is what the caller needs
        if exc.response is None:
            raise
        response = exc.response
    return response.status_code, response.headers.get("Retry-After")
