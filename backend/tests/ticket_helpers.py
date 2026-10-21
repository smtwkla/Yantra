"""Shared by the ticket tests (S017, S018): times as the dialogs send them and as the API
answers, and a refusal's status, field and message."""

from datetime import datetime

from equipment import IST


def now_ist():
    return datetime.now(IST).replace(tzinfo=None)


def local(dt):
    """A naive datetime as the screens send it (datetime-local, no offset)."""
    return dt.strftime("%Y-%m-%dT%H:%M")


def api_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")


def refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]
