"""Vendor contracts — the pure rules (docs/steps/S080-contract-register/1-brief.md § 5; R02.1).  No DB, no Flask,
no clock: the shell passes in today's IST date.

The fields reuse masters_core's rules through its public names (D9): one copy of the text, flag, id and phone
rules.  The one stated copy is ``_iso_date``, the 7 lines of improvements_core._iso_date (two cores do not import
each other's private helpers), with the date bounds of § 5.1 added here.
"""

import calendar
import re
from datetime import date, timedelta
from decimal import Decimal

from equipment_core import SCRAPPED
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

# The same for a machine line (S081 § 5.4, BS1-02): its price follows the cost key
LINE_GATED_FIELDS = {"price": "contract:read_senior"}


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


# ---------------------------------------------------------------------------
# The machines a contract covers (S081, R02.2; docs/steps/S081-contract-equipment/1-brief.md § 5)
# ---------------------------------------------------------------------------

# contract_equipment.price DECIMAL(10,2): rupees before GST, paise kept (D8)
PRICE_MAX = Decimal("99999999.99")
PRICE_FORMAT = "Enter the price in rupees, before GST, e.g. 9809 or 9809.50."
PRICE_TOO_LARGE = "Price: at most 9,99,99,999.99."
# ASCII digits only: Python's \d also takes other scripts' digits
_PRICE_RE = re.compile(r"^[0-9]+(\.[0-9]{1,2})?$")

# The type in a history line (§ 5.3)
TYPE_SHORT = {"amc": "AMC", "cmc": "CMC", "warranty": "Warranty", "on_call": "On call"}


def parse_price(raw):
    """A line's price (§ 5.1) -> a Decimal, or None for null or "" (not entered).  An int, or a string of digits
    with at most two decimals (trimmed), 0 to PRICE_MAX.  A float (already rounded), a boolean, a minus sign, a
    comma or a rupee sign is refused.  Not meters_core.parse_number: money is never negative (B11)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise ValueError(PRICE_FORMAT)
    if isinstance(raw, int):
        if raw < 0:
            raise ValueError(PRICE_FORMAT)
        value = Decimal(raw)
    else:
        text = raw.strip()
        if not text:
            return None
        if not _PRICE_RE.match(text):
            raise ValueError(PRICE_FORMAT)
        value = Decimal(text)
    if value > PRICE_MAX:
        raise ValueError(PRICE_TOO_LARGE)
    return value


_LINE_FIELDS = {
    "equipment_id": (id_parser("Machine"), False),
    "price": (parse_price, False),
}


def validate_line(body, creating):
    """A machine line's body -> ``(clean, errors)`` for clean_body (§ 5.1).  On a POST the machine is required (an
    absent one is parsed as None, so "Choose a machine." shows); on a PUT the path names it, so a sent
    ``equipment_id`` is ignored.  Unknown fields are ignored."""
    data = dict(body)
    if creating:
        data.setdefault("equipment_id", None)
    else:
        data.pop("equipment_id", None)
    return validate_fields(data, _LINE_FIELDS, creating)


def event_text(contract):
    """The contract as the machine's history names it (§ 5.3): "<title> (<type>, DD-MM-YYYY to DD-MM-YYYY)".
    Never the price: the history is read with equipment:read.  At most 137 characters."""
    period = f"{contract['from_date'].strftime('%d-%m-%Y')} to {contract['to_date'].strftime('%d-%m-%Y')}"
    return f"{contract['title']} ({TYPE_SHORT[contract['contract_type']]}, {period})"


# ---------------------------------------------------------------------------
# Under contract on the machine (S082, R02.2; docs/steps/S082-under-contract-card/1-brief.md § 5)
# ---------------------------------------------------------------------------

# The card also shows a contract that ended this many days ago or less (the roadmap's window, § 9 A2)
CARD_ENDED_DAYS = 90

# The equipment list's Contract filter (§ 5.4); absent = no filter
COVERAGE_FILTERS = ("under", "not_under")


def card_items(rows, node, today):
    """The card's contracts (§ 5.1) -> ``[{row, via_id}, …]``, one per contract.

    ``rows`` are contract rows, each with the ``equipment_id`` of one of its lines on ``node`` (``{id,
    parent_id, gp_id}``) or an ancestor.  A contract shows from its From date until CARD_ENDED_DAYS after its To
    date; one that starts later does not (B15).  The line nearest the node wins: ``via_id`` is None on the node
    itself, else the ancestor's id.  Order: the contracts not ended by ``to_date, id``; then the ended ones, the
    latest end first, then by ``id``."""
    distance = {node["id"]: 0}
    for steps, ancestor_id in ((1, node["parent_id"]), (2, node["gp_id"])):
        if ancestor_id is not None:
            distance[ancestor_id] = steps
    shown_from = today - timedelta(days=CARD_ENDED_DAYS)
    nearest = {}
    for row in rows:
        if row["equipment_id"] not in distance or row["from_date"] > today or row["to_date"] < shown_from:
            continue
        kept = nearest.get(row["id"])
        if kept is None or distance[row["equipment_id"]] < distance[kept["equipment_id"]]:
            nearest[row["id"]] = row
    not_ended = sorted((r for r in nearest.values() if r["to_date"] >= today), key=lambda r: (r["to_date"], r["id"]))
    ended = sorted((r for r in nearest.values() if r["to_date"] < today), key=lambda r: (-r["to_date"].toordinal(), r["id"]))
    return [{"row": r, "via_id": None if r["equipment_id"] == node["id"] else r["equipment_id"]}
            for r in [*not_ended, *ended]]


def covered_sql(coverage, site_ids, today):
    """The Contract filter (§ 5.4) -> ``(sql, params)`` for the equipment list's WHERE.  Under contract: the row's
    node (``e``), its parent or its grandparent (``p.parent_id``, NODE_JOINS' parent alias) is on a line of an
    active contract in force on ``today`` at one of ``site_ids`` (where the reader holds contract:read_basic).  Not
    under contract: the opposite.  No site: nothing is under contract, with no empty ``IN ()``."""
    if not site_ids:
        return ("0 = 1", []) if coverage == "under" else ("1 = 1", [])
    exists = ("EXISTS (SELECT 1 FROM contract_equipment ce JOIN contracts ct ON ct.id = ce.contract_id"
              " WHERE ce.equipment_id IN (e.id, e.parent_id, p.parent_id) AND ct.active = 1"
              f" AND ct.from_date <= %s AND ct.to_date >= %s AND ct.site_id IN ({', '.join(['%s'] * len(site_ids))}))")
    return (exists if coverage == "under" else f"NOT {exists}"), [today, today, *site_ids]


# ---------------------------------------------------------------------------
# Renewal (S085, R02.4; docs/steps/S085-contract-renewal/1-brief.md § 5)
# ---------------------------------------------------------------------------

RENEW_INACTIVE = "This contract is inactive. Set it active in Masters › Contracts, then renew it."
# The unique key's text (§ 5.5): two renewals of one contract at one instant
RENEWAL_RACE = "This contract is already renewed. Reload the page to see the renewal."
SKIP_SCRAPPED = "scrapped"


def renew_site_inactive(site_code):
    """§ 5.5: the old contract's site is inactive."""
    return f"{site_code} is inactive. Set it active in Masters › Sites, then renew the contract."


def already_renewed(title):
    """§ 5.5: the contract has a renewal, active or not."""
    return f"This contract is already renewed: {title}. Open that contract to change it."


def validate_renewal(body, creating):
    """A renewal's body -> ``(clean, errors)`` for clean_body (§ 5.4, E10).  ``creating`` is taken only for
    clean_body's call shape and ignored: a renewal is always a create.  The site is the old contract's, set by the
    route, so a ``site_id`` sent is removed and validate_contract's "Choose a site." is dropped; ``active`` and
    ``renewal_of_id`` are ignored, as on a create."""
    data = dict(body)
    data.pop("site_id", None)
    clean, errors = validate_contract(data, True)
    clean.pop("site_id", None)
    return clean, [e for e in errors if e["field"] != "site_id"]


def _add_months(day, months):
    """``day`` plus whole months: the same day of the month, or the month's last day when the month is shorter."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def renewal_period(from_date, to_date):
    """The proposed period of the renewal (§ 5.2, E3) -> ``(new_from, new_to)``, or ``(None, None)`` past DATE_MAX.
    It starts the day after ``to_date``.  When the old period was whole months (the new From has the old From's day
    of the month) it keeps that number of months; otherwise the same number of days."""
    new_from = to_date + timedelta(days=1)
    if new_from.day == from_date.day:
        months = max(1, (new_from.year - from_date.year) * 12 + new_from.month - from_date.month)
        new_to = _add_months(new_from, months) - timedelta(days=1)
    else:
        new_to = new_from + (to_date - from_date)
    if new_to > DATE_MAX:
        return None, None
    return new_from, new_to


def renewal_lines(machines):
    """The old contract's lines -> ``(copied, skipped)`` (§ 5.3, E5).  Each line has ``equipment_id``, ``code``,
    ``lifecycle``, ``at_contract_site`` and ``site_code``.  Copied: not scrapped and still at the contract's site, as
    an add requires (S081 § 5.2 rules 3 and 4); the renewer's units are not asked.  Skipped, with the reason:
    "scrapped" (it wins), or "now at <site>"."""
    copied, skipped = [], []
    for line in machines:
        if line["lifecycle"] == SCRAPPED:
            reason = SKIP_SCRAPPED
        elif not line["at_contract_site"]:
            reason = f"now at {line['site_code']}"
        else:
            copied.append({"equipment_id": line["equipment_id"], "code": line["code"]})
            continue
        skipped.append({"equipment_id": line["equipment_id"], "code": line["code"], "reason": reason})
    return copied, skipped
