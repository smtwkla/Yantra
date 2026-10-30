"""Vendor contracts — the pure rules (docs/steps/S080-contract-register/1-brief.md § 5; R02.1).  No DB, no Flask,
no clock: the shell passes in today's IST date.

The fields reuse masters_core's rules through its public names (D9): one copy of the text, flag, id and phone
rules.  The one stated copy is ``_iso_date``, the 7 lines of improvements_core._iso_date (two cores do not import
each other's private helpers), with the date bounds of § 5.1 added here.
"""

from datetime import date, timedelta

from masters_core import collapsed, flag_parser, id_parser, optional_text_parser, phone_parser, validate_fields

# The ENUM of contracts.contract_type (v43), in the order the dialog lists them after AMC
CONTRACT_TYPES = ("warranty", "amc", "cmc", "on_call")

TITLE_MAX = 100
CONTRACT_NUMBER_MAX = 60
TEXT_MAX = 1000
COST_NOTE_MAX = 255
DATE_MIN = date(2000, 1, 1)
DATE_MAX = date(2099, 12, 31)
CALLS_MIN, CALLS_MAX = 1, 365
PM_VISITS_MIN, PM_VISITS_MAX = 0, 52
RESPONSE_MIN, RESPONSE_MAX = 1, 720

# The status badge's window: the first reminder of R02 Q5.1 a (R02.5 may make it a setting, § 9 A3)
ENDING_SOON_DAYS = 60

# The list's Status filter (§ 5.3); the default shows every contract that has not ended
STATUS_FILTERS = ("not_ended", "in_force", "ending", "upcoming", "ended", "all")
DEFAULT_STATUS = "not_ended"

VENDOR_MISSING = "Choose a vendor. The list holds the active vendors of Masters › Vendors."
SITE_KEPT = "A contract keeps its site. Deactivate it, then add the contract at the other site."
SITE_INACTIVE = "Choose an active site."
TO_BEFORE_FROM = "Enter a To date on or after the From date."
FROM_AFTER_TO = "Enter a From date on or before the To date."
CALLS_WITHOUT_TICK = "Tick Breakdown calls to enter calls per year."

REQUIRED = ("site_id", "vendor_id", "contract_type", "title", "from_date", "to_date")


def _iso_date(value):
    """``YYYY-MM-DD`` (trimmed) -> the date, or None for anything else (a copy of improvements_core._iso_date)."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    # date.fromisoformat also takes 20270331 and week dates (2027-W13-3); the API takes YYYY-MM-DD only (S080 CR1-02)
    if len(text) != len("YYYY-MM-DD") or text[4] != "-" or text[7] != "-":
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _date_parser(message):
    def parse(raw):
        value = _iso_date(raw)
        if value is None or not DATE_MIN <= value <= DATE_MAX:
            raise ValueError(message)
        return value
    return parse


def _bounded_int_parser(low, high, message):
    """A whole number from ``low`` to ``high``, or None (empty).  A boolean or a string is refused."""
    def parse(raw):
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or not low <= raw <= high:
            raise ValueError(message)
        return raw
    return parse


def _parse_title(raw):
    if raw is not None and not isinstance(raw, str):
        raise ValueError("Title must be text")
    title = collapsed(raw)
    if not title:
        raise ValueError("Enter a title.")
    if len(title) > TITLE_MAX:
        raise ValueError(f"Title must be at most {TITLE_MAX} characters")
    return title


def _parse_contract_type(raw):
    if raw not in CONTRACT_TYPES:
        raise ValueError("Choose a type.")
    return raw


_parse_site_id = id_parser("Site")
_parse_vendor_id_plain = id_parser("Vendor")


def _parse_vendor_id(raw):
    """id_parser("Vendor")'s rule, with the longer text that says where the vendors come from (§ 5.1, BS1-01).
    An unknown or inactive vendor is the shell's check (masters.check_active_vendor), with S079's texts."""
    try:
        return _parse_vendor_id_plain(raw)
    except ValueError:
        raise ValueError(VENDOR_MISSING) from None


# field -> (parser, required when creating).  validate_contract gives an absent required field the value None
# on a POST, so its own parser's "Enter …" / "Choose …" text shows; the table therefore marks nothing required.
_CONTRACT_FIELDS = {
    "site_id": (_parse_site_id, False),
    "vendor_id": (_parse_vendor_id, False),
    "contract_type": (_parse_contract_type, False),
    "title": (_parse_title, False),
    "contract_number": (optional_text_parser("Contract number", CONTRACT_NUMBER_MAX, collapse=True), False),
    "from_date": (_date_parser("Enter a From date."), False),
    "to_date": (_date_parser("Enter a To date."), False),
    "covers_labour": (flag_parser("Labour"), False),
    "covers_parts": (flag_parser("Spare parts"), False),
    "covers_consumables": (flag_parser("Consumables"), False),
    "covers_breakdown_calls": (flag_parser("Breakdown calls"), False),
    "breakdown_calls_per_year": (_bounded_int_parser(
        CALLS_MIN, CALLS_MAX, "Calls per year: a whole number from 1 to 365, or empty for no limit."), False),
    "covered_text": (optional_text_parser("Covered", TEXT_MAX), False),
    "not_covered_text": (optional_text_parser("Not covered", TEXT_MAX), False),
    "pm_visits_per_year": (_bounded_int_parser(
        PM_VISITS_MIN, PM_VISITS_MAX, "PM visits per year: a whole number from 0 to 52, or empty."), False),
    "response_hours": (_bounded_int_parser(
        RESPONSE_MIN, RESPONSE_MAX, "Response time: a whole number of hours from 1 to 720, or empty."), False),
    "only_vendor_repairs": (flag_parser("Only the vendor may repair"), False),
    "callout_number": (phone_parser("Call-out number"), False),
    "cost_note": (optional_text_parser("Cost note", COST_NOTE_MAX), False),
    "notes": (optional_text_parser("Notes", TEXT_MAX), False),
    "active": (flag_parser("Active"), False),
}

# The fields only some readers see and write (§ 5.4): field -> the key needed at the contract's site
GATED_FIELDS = {"callout_number": "contract:read", "cost_note": "contract:read_senior"}


def validate_contract(body, creating):
    """The body -> ``(clean, errors)`` for clean_body (§ 5.1).  On a POST every required field must be there (an
    absent one is parsed as None, so its own text shows) and ``active`` is ignored (a new contract is active); on a
    PUT an absent field stays as it is.  Unknown fields (``renewal_of_id`` included) are ignored.  Breakdown calls
    unticked with no number sent clears the stored number (the shell writes NULL)."""
    data = dict(body)
    if creating:
        data.pop("active", None)
        for field in REQUIRED:
            data.setdefault(field, None)
    clean, errors = validate_fields(data, _CONTRACT_FIELDS, creating)
    if clean.get("covers_breakdown_calls") == 0 and "breakdown_calls_per_year" not in data:
        clean["breakdown_calls_per_year"] = None
    return clean, errors


def period_error(from_date, to_date, to_sent):
    """The merged period (§ 5.1) -> ``(field, message)`` or None.  The message goes beside the date that was sent:
    the To date when it was, else the From date."""
    if to_date >= from_date:
        return None
    return ("to_date", TO_BEFORE_FROM) if to_sent else ("from_date", FROM_AFTER_TO)


def breakdown_calls_error(ticked, calls):
    """A number of calls (not None) with the merged tick off -> the message, else None (§ 5.1)."""
    if calls is not None and not ticked:
        return CALLS_WITHOUT_TICK
    return None


def _days_text(days):
    if days == 0:
        return "Ends today"
    return f"Ends in {days} day" if days == 1 else f"Ends in {days} days"


def contract_status(from_date, to_date, today):
    """The status from the dates (§ 5.3), the period inclusive -> ``{kind, label, days}``."""
    if from_date > today:
        return {"kind": "upcoming", "label": f"Starts on {from_date.strftime('%d-%m-%Y')}", "days": None}
    if to_date < today:
        return {"kind": "ended", "label": "Ended", "days": None}
    days = (to_date - today).days
    if days <= ENDING_SOON_DAYS:
        return {"kind": "ending", "label": _days_text(days), "days": days}
    return {"kind": "in_force", "label": "In force", "days": None}


def status_bounds(status, today):
    """The Status filter (§ 5.3) -> ``[(column, operator, date), …]``, all to hold.  Each filter matches exactly
    the rows whose kind it names: in_force also the ending ones, not_ended every kind but ended."""
    ending_by = today + timedelta(days=ENDING_SOON_DAYS)
    return {
        "not_ended": [("to_date", ">=", today)],
        "in_force": [("from_date", "<=", today), ("to_date", ">=", today)],
        "ending": [("from_date", "<=", today), ("to_date", ">=", today), ("to_date", "<=", ending_by)],
        "upcoming": [("from_date", ">", today)],
        "ended": [("to_date", "<", today)],
        "all": [],
    }[status]


def newest_end_first(status):
    """The list's order (§ 5.3): the soonest end first, but the latest ended first when looking at ended ones."""
    return status == "ended"
