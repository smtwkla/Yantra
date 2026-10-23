"""email_core — the closed-ticket email's text, the address check and the SMTP outcomes (S032 § 8
Backend, test_email_core.py)."""

import smtplib
import ssl
from datetime import datetime
from decimal import Decimal

import pytest

from email_core import (
    clean_address, closed_email, duration_text, email_for_test, one_line, smtp_outcome, valid_address,
)

RAISED = datetime(2026, 10, 20, 9, 12)
RESTORED = datetime(2026, 10, 20, 11, 40)
CLOSED = datetime(2026, 10, 20, 14, 5)
URL = "https://vel-yantra.mspv.app/tickets/123"
ADDRESS = "priya@example.test"


def _times(**overrides):
    times = {"response_minutes": 10, "repair_minutes": 110, "downtime_minutes": 148, "waiting_minutes": 20,
             "waiting_by_reason": {"parts": 20}, "planned_downtime_minutes": None}
    return {**times, **overrides}


def _facts(**overrides):
    facts = {
        "serial": "TK-2026-10-012", "site_code": "SMTW", "unit_code": "MCC2", "machine_code": "VBM001",
        "machine_name": "Vertical ball mill", "component_code": "GBX01", "component_name": "Gearbox",
        "intensity": "critical", "not_a_fault": False, "symptom": "Not building pressure",
        "description": "oil leak at the gearbox seal", "raised_at": RAISED, "raised_by": "Ravi",
        "back_in_service_at": RESTORED, "times": _times(), "cause": "Wear", "action": "Replace",
        "labour_minutes": 195, "labour_people": 2,
        "parts": [{"description": "Oil seal 45x62x8", "quantity": Decimal("1.00"), "qty_unit": "nos"},
                  {"description": "Gear oil EP 220", "quantity": Decimal("2.00"), "qty_unit": "l"}],
        "closed_at": CLOSED, "closed_by": "Priya", "remark": "Seal changed, watch for 2 days", "url": URL,
    }
    return {**facts, **overrides}


def _line(body, label):
    """The line that starts with ``label:``, or None."""
    return next((line for line in body.splitlines() if line.startswith(f"{label}:")), None)


NOT_A_FAULT_TIMES = dict.fromkeys(_times())


class TestClosedEmail:

    def test_a_breakdown_with_every_line(self):
        subject, body = closed_email(_facts())
        assert subject == "Closed · SMTW.MCC2 · VBM001 · TK-2026-10-012"
        assert body == (
            "TK-2026-10-012 — Breakdown, closed\n"
            "Machine:          VBM001 — Vertical ball mill\n"
            "Component:        GBX01 — Gearbox\n"
            "Unit:             SMTW.MCC2\n"
            "Problem:          Not building pressure — oil leak at the gearbox seal\n"
            "Raised:           20-10-2026 09:12 by Ravi\n"
            "Back in service:  20-10-2026 11:40\n"
            "Downtime:         2 h 28 min\n"
            "Repair time:      1 h 50 min\n"
            "Waiting:          0 h 20 min (parts 0 h 20 min)\n"
            "Cause:            Wear\n"
            "Action:           Replace\n"
            "Labour:           3 h 15 min, 2 people\n"
            "Parts:            Oil seal 45x62x8 — 1 nos\n"
            "                  Gear oil EP 220 — 2 l\n"
            "Closed:           20-10-2026 14:05 by Priya\n"
            "Remark:           Seal changed, watch for 2 days\n"
            "\n"
            "Open the ticket: https://vel-yantra.mspv.app/tickets/123\n")

    def test_a_defect_shows_zero_downtime(self):
        """BR1-11: a defect is never down, so ticket_times gives 0 and the line says so."""
        _subject, body = closed_email(_facts(intensity="degraded", component_code=None, labour_people=1,
                                             labour_minutes=30, times=_times(downtime_minutes=0, waiting_minutes=None,
                                                                             waiting_by_reason=None)))
        assert body.splitlines()[0] == "TK-2026-10-012 — Defect, closed"
        assert _line(body, "Downtime") == "Downtime:         0 h 00 min"
        assert _line(body, "Waiting") is None and _line(body, "Component") is None
        assert _line(body, "Labour") == "Labour:           0 h 30 min, 1 person"

    def test_not_a_fault(self):
        subject, body = closed_email(_facts(intensity="initial", not_a_fault=True, times=NOT_A_FAULT_TIMES,
                                            back_in_service_at=None, action=None, parts=[], cause="No fault found",
                                            remark="Ran fine when I got there"))
        assert subject == "Closed as not a fault · SMTW.MCC2 · VBM001 · TK-2026-10-012"
        assert body.splitlines()[0] == "TK-2026-10-012 — Defect, closed as not a fault"
        for label in ("Back in service", "Downtime", "Repair time", "Waiting", "Action", "Labour", "Parts"):
            assert _line(body, label) is None, label
        assert _line(body, "Cause") == "Cause:            No fault found"
        assert _line(body, "Closed") == "Closed:           20-10-2026 14:05 by Priya"
        assert _line(body, "Remark") == "Remark:           Ran fine when I got there"

    def test_no_parts(self):
        _subject, body = closed_email(_facts(parts=[]))
        assert _line(body, "Parts") is None

    def test_eleven_parts_show_ten_and_one_more(self):
        parts = [{"description": f"Part {n}", "quantity": Decimal("1.50"), "qty_unit": "kg"} for n in range(1, 12)]
        _subject, body = closed_email(_facts(parts=parts))
        lines = body.splitlines()
        start = lines.index("Parts:            Part 1 — 1.5 kg")
        assert lines[start + 9] == "                  Part 10 — 1.5 kg"
        assert lines[start + 10] == "                  and 1 more"
        assert "Part 11" not in body

    def test_a_long_description_is_cut_at_500_with_a_mark(self):
        _subject, body = closed_email(_facts(symptom=None, description="x" * 600))
        assert _line(body, "Problem") == f"Problem:          {'x' * 500}…"

    def test_a_description_with_line_breaks_keeps_the_subject_on_one_line(self):
        subject, body = closed_email(_facts(symptom=None, description="Leak\r\nat the seal", serial="TK-1\n2"))
        assert "\n" not in subject and "\r" not in subject
        assert subject == "Closed · SMTW.MCC2 · VBM001 · TK-1 2"
        # In the body a second line keeps the value column
        assert "Problem:          Leak\n                  at the seal" in body

    def test_a_raise_with_no_name_and_a_missing_component_name(self):
        _subject, body = closed_email(_facts(raised_by="", component_name=None, closed_by=""))
        assert _line(body, "Raised") == "Raised:           20-10-2026 09:12"
        assert _line(body, "Component") == "Component:        GBX01"
        assert _line(body, "Closed") == "Closed:           20-10-2026 14:05"

    def test_the_test_email(self):
        subject, body = email_for_test()
        assert subject == "Yantra test email"
        assert body.startswith("This is a test email from Yantra.")


class TestHelpers:

    @pytest.mark.parametrize("minutes, text", [(0, "0 h 00 min"), (5, "0 h 05 min"), (148, "2 h 28 min"),
                                               (1560, "26 h 00 min")])
    def test_duration_text(self, minutes, text):
        assert duration_text(minutes) == text

    def test_one_line(self):
        assert one_line("a\r\nb\nc\rd") == "a b c d"
        assert one_line(None) == ""


class TestAddress:

    @pytest.mark.parametrize("text", ["priya@example.test", "a.b-c+d@mail.example.test", "x@y.test"])
    def test_good(self, text):
        assert valid_address(text)

    @pytest.mark.parametrize("text", [
        "", None, "bad", "priya.example.test", "a@b@example.test", "priya @example.test", "a@b.test, c@d.test",
        "a@b.test;c@d.test", "<a@b.test>", "a@b.test\r\nBcc: x@y.test", "@example.test", "priya@localhost", "a@" + "b" * 248 + ".test",   # the last: 255 characters
    ])
    def test_refused(self, text):
        assert not valid_address(text)

    def test_254_characters_is_the_limit(self):
        assert len("a@" + "b" * 247 + ".test") == 254
        assert valid_address("a@" + "b" * 247 + ".test")

    def test_clean_address_strips_and_lower_cases_or_clears(self):
        assert clean_address("  Priya@EXAMPLE.test ") == ADDRESS
        assert clean_address("bad") is None
        assert clean_address("") is None
        assert clean_address(None) is None


def _refused(code):
    return smtplib.SMTPRecipientsRefused({"Priya@EXAMPLE.test": (code, b"refused")})


class TestSmtpOutcome:
    """One case per row of § 5.5, in its order, and the cases the review named."""

    @pytest.mark.parametrize("exc, outcome", [
        # Row 1: the connection
        (smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
         (True, "mail server not reached (SMTPServerDisconnected)")),
        (smtplib.SMTPConnectError(421, b"busy"), (True, "mail server not reached (SMTP 421)")),
        # A 554 greeting is still row 1 (retry), not row 3
        (smtplib.SMTPConnectError(554, b"no service"), (True, "mail server not reached (SMTP 554)")),
        # Row 2: the one recipient's code
        (_refused(450), (True, "email deferred (SMTP 450)")),
        (_refused(451), (True, "email deferred (SMTP 451)")),
        (_refused(550), (False, "email refused (SMTP 550)")),
        (smtplib.SMTPRecipientsRefused({}), (False, "email refused (SMTPRecipientsRefused)")),
        # Row 3: answers with a code
        (smtplib.SMTPSenderRefused(452, b"too many", "yantra@example.test"), (True, "email deferred (SMTP 452)")),
        (smtplib.SMTPSenderRefused(550, b"not allowed", "yantra@example.test"), (False, "email refused (SMTP 550)")),
        # A wrong password fails at once: row 3, not row 5 (it is an OSError too)
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), (False, "email refused (SMTP 535)")),
        (smtplib.SMTPDataError(554, b"rejected"), (False, "email refused (SMTP 554)")),
        (smtplib.SMTPHeloError(501, b"bad helo"), (False, "email refused (SMTP 501)")),
        (smtplib.SMTPResponseException(421, b"closing"), (True, "email deferred (SMTP 421)")),
        # Row 4: no code
        (smtplib.SMTPNotSupportedError("STARTTLS extension not supported by server."),
         (False, "email failed (SMTPNotSupportedError)")),
        # Row 5: the network
        (TimeoutError("timed out"), (True, "mail server not reached (TimeoutError)")),
        (ConnectionRefusedError(10061, "refused"), (True, "mail server not reached (ConnectionRefusedError)")),
        (ssl.SSLError("certificate verify failed"), (True, "mail server not reached (SSLError)")),
        # Row 6: anything else
        (ValueError("Header values may not contain linefeed"), (False, "email failed (ValueError)")),
    ])
    def test_each_row(self, exc, outcome):
        assert smtp_outcome(exc) == outcome

    def test_every_smtp_error_is_an_os_error(self):
        """Why rows 1-4 come before row 5 (BR2-01)."""
        assert issubclass(smtplib.SMTPException, OSError)

    def test_the_text_never_holds_the_address(self):
        exc = _refused(550)
        assert "example" in str(exc).lower()
        assert "example" not in smtp_outcome(exc)[1].lower()
