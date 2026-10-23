"""Email — pure texts and rules (docs/steps/S032-closed-ticket-email/1-brief.md § 1.4, § 5.3–5.5;
no DB, no clock, no Flask, no network).

The email channel's own decisions: the text of *Ticket closed* and of the test email, the check
of an address from the login token, and what an SMTP failure means for the queue.  Who gets an
email is alerts_core's (AUDIENCE, CHANNELS), the same table as every other alert.

smtplib is imported here for its exception classes only (smtp_outcome); mail_sender.py is the one
module that opens a connection.
"""

import re
from decimal import Decimal
from smtplib import (
    SMTPConnectError, SMTPException, SMTPRecipientsRefused, SMTPResponseException, SMTPServerDisconnected,
)

from tickets_core import BREAKDOWN_INTENSITY, WAITING_REASONS

# § 4: the longest address SMTP carries (RFC 5321 path limit), people.email VARCHAR(254)
ADDRESS_MAX = 254
ADDRESS_MIN = 3
# Characters a single address never holds: a list separator, an angle bracket or a line break
# would let one claim name several recipients or break a header
_ADDRESS_REFUSED = set(",;<>")

# § 5.3: the email has room for the whole story; the push cut of 80 is for a phone banner
EMAIL_DESCRIPTION_CUT = 500
EMAIL_REMARK_CUT = 500
EMAIL_PARTS_MAX = 10
_CUT_MARK = "…"

# The body's label column: "Back in service:" and two spaces
_LABEL_WIDTH = 18
_TIME_FORMAT = "%d-%m-%Y %H:%M"

TEST_EMAIL_SUBJECT = "Yantra test email"
TEST_EMAIL_BODY = "This is a test email from Yantra.\nYantra can send email to this address.\n"


# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------

def one_line(text):
    """Header text without CR or LF: EmailMessage refuses a header with a line break (§ 5.3)."""
    return re.sub(r"[\r\n]+", " ", text or "").strip()


def duration_text(minutes):
    """``2 h 28 min``; hours never roll into days, so a manager compares downtimes by hours."""
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest:02d} min"


def _cut(text, limit):
    if text is None or len(text) <= limit:
        return text
    return text[:limit] + _CUT_MARK


def _time(value):
    return value.strftime(_TIME_FORMAT)


def _quantity(value):
    """``Decimal("1.50")`` -> ``1.5``, ``2.00`` -> ``2`` (never ``1E+2``)."""
    return format(Decimal(str(value)).normalize(), "f")


def _field(label, value):
    """One fact as ``Label:           value``; a value over several lines keeps the column."""
    lines = str(value).splitlines() or [""]
    head = f"{label + ':':<{_LABEL_WIDTH}}{lines[0]}"
    return "\n".join([head, *(f"{'':<{_LABEL_WIDTH}}{line}" for line in lines[1:])])


# ---------------------------------------------------------------------------
# The address from the login token (§ 5.4)
# ---------------------------------------------------------------------------

def valid_address(text):
    """A guard against a broken claim, not full RFC 5322: 3–254 characters, exactly one ``@``
    with something before it, no whitespace, comma, semicolon, angle bracket or line break, and
    a dot after the ``@``."""
    if not isinstance(text, str) or not ADDRESS_MIN <= len(text) <= ADDRESS_MAX:
        return False
    if text.count("@") != 1 or any(c.isspace() or c in _ADDRESS_REFUSED for c in text):
        return False
    local, domain = text.split("@")
    return bool(local) and "." in domain


def clean_address(raw):
    """The token's email as stored: stripped and lower-cased when valid_address accepts it,
    else None (a token with no email, or a broken one, clears the stored address)."""
    if not isinstance(raw, str):
        return None
    address = raw.strip().lower()
    return address if valid_address(address) else None


# ---------------------------------------------------------------------------
# The texts
# ---------------------------------------------------------------------------

def email_for_test():
    """The test email of My notifications -> ``(subject, body)``."""
    return TEST_EMAIL_SUBJECT, TEST_EMAIL_BODY


def _waiting(times):
    """``0 h 20 min (parts 0 h 20 min)``: the reasons by their WAITING_REASONS code, in its order."""
    by_reason = times.get("waiting_by_reason") or {}
    parts = [f"{code} {duration_text(by_reason[code])}" for code in WAITING_REASONS if code in by_reason]
    total = duration_text(times["waiting_minutes"])
    return f"{total} ({', '.join(parts)})" if parts else total


def _code_name(code, name):
    return f"{code} — {name}" if name else code


def _parts_lines(parts):
    lines = [f"{p['description']} — {_quantity(p['quantity'])} {p['qty_unit']}" for p in parts[:EMAIL_PARTS_MAX]]
    if len(parts) > EMAIL_PARTS_MAX:
        lines.append(f"and {len(parts) - EMAIL_PARTS_MAX} more")
    return "\n".join(lines)


def closed_email(facts):
    """*Ticket closed* -> ``(subject, body)`` (§ 1.4), plain text, one fact per line; a line with
    no value is left out.  ``facts`` (alerts.read_closed_facts): serial, site_code, unit_code,
    machine_code, machine_name, component_code, component_name, intensity, not_a_fault, symptom,
    description, raised_at, raised_by, back_in_service_at, times (tickets_core.ticket_times),
    cause, action, labour_minutes, labour_people, parts ([{description, quantity, qty_unit}]),
    closed_at, closed_by, remark, url."""
    not_a_fault = facts["not_a_fault"]
    place = f"{facts['site_code']}.{facts['unit_code']}"
    head = "Closed as not a fault" if not_a_fault else "Closed"
    subject = " · ".join(one_line(text) for text in (head, place, facts["machine_code"], facts["serial"]))

    word = "Breakdown" if facts["intensity"] == BREAKDOWN_INTENSITY else "Defect"
    lines = [f"{facts['serial']} — {word}, {'closed as not a fault' if not_a_fault else 'closed'}"]

    def add(label, value):
        if value is not None and value != "":
            lines.append(_field(label, value))

    def by(when, name):
        return f"{_time(when)} by {name}" if name else _time(when)

    times = facts["times"]
    add("Machine", _code_name(facts["machine_code"], facts["machine_name"]))
    if facts["component_code"]:
        add("Component", _code_name(facts["component_code"], facts["component_name"]))
    add("Unit", place)
    add("Problem", " — ".join(t for t in (facts["symptom"], _cut(facts["description"], EMAIL_DESCRIPTION_CUT)) if t))
    add("Raised", by(facts["raised_at"], facts["raised_by"]))
    if facts["back_in_service_at"] is not None:
        add("Back in service", _time(facts["back_in_service_at"]))
    for label, key in (("Downtime", "downtime_minutes"), ("Repair time", "repair_minutes")):
        if times[key] is not None:
            add(label, duration_text(times[key]))
    if times["waiting_minutes"] is not None:
        add("Waiting", _waiting(times))
    add("Cause", facts["cause"])
    if not not_a_fault:
        # A not-a-fault close records no action, and refuses parts (S020); its labour is not a repair
        add("Action", facts["action"])
        if facts["labour_people"]:
            people = "person" if facts["labour_people"] == 1 else "people"
            add("Labour", f"{duration_text(facts['labour_minutes'])}, {facts['labour_people']} {people}")
        if facts["parts"]:
            add("Parts", _parts_lines(facts["parts"]))
    add("Closed", by(facts["closed_at"], facts["closed_by"]))
    add("Remark", _cut(facts["remark"], EMAIL_REMARK_CUT))
    lines += ["", f"Open the ticket: {facts['url']}", ""]
    return subject, "\n".join(lines)


# ---------------------------------------------------------------------------
# What an SMTP failure means (§ 5.5)
# ---------------------------------------------------------------------------

def _temporary(code):
    """A 4xx answer: the server asks to try again later (greylisting, a full mailbox, a limit)."""
    return isinstance(code, int) and 400 <= code < 500


def _by_code(code):
    if _temporary(code):
        return True, f"email deferred (SMTP {code})"
    return False, f"email refused (SMTP {code})"


def smtp_outcome(exc):
    """A failed send -> ``(retry, text)``: retry with the queue's back-off, or fail at once.
    Decided by the SMTP code wherever there is one; the rows are checked in this order, so a
    subclass meets its own row first (SMTPConnectError is an SMTPResponseException, and every
    SMTPException is an OSError).  ``text`` is the outcome with the code or the exception's type,
    never ``str(exc)``: SMTPRecipientsRefused's text carries the address."""
    name = type(exc).__name__
    # 1. The connection: the greeting was refused, or the server hung up
    if isinstance(exc, (SMTPConnectError, SMTPServerDisconnected)):
        code = getattr(exc, "smtp_code", None)
        return True, f"mail server not reached ({f'SMTP {code}' if code is not None else name})"
    # 2. The one recipient's code: the dict's only value, never looked up by address, whose case
    #    the server may change
    if isinstance(exc, SMTPRecipientsRefused):
        if not exc.recipients:
            return False, f"email refused ({name})"
        return _by_code(next(iter(exc.recipients.values()))[0])
    # 3. Sender, login, data, HELO and any other answer with a code
    if isinstance(exc, SMTPResponseException):
        return _by_code(exc.smtp_code)
    # 4. No code, e.g. SMTPNotSupportedError (the server offers no STARTTLS)
    if isinstance(exc, SMTPException):
        return False, f"email failed ({name})"
    # 5. The network: a timeout, a refused connection, DNS, TLS
    if isinstance(exc, OSError):
        return True, f"mail server not reached ({name})"
    # 6. Anything else is not a network fault, so a retry cannot fix it
    return False, f"email failed ({name})"
