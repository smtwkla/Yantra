"""Meters on models and nodes — the pure rules (docs/steps/S038-meters-on-models-equipment/
1-brief.md § 5).  Plain data in, plain data out: no database, no clock, no Flask.

- validate_limits: a gauge's min / max from a request body, merged over the pair in force;
- effective_meters: a node's meters = its model's active meters (with the node's override of
  their limits) plus its own;
- limits_text and tracked_meter_change: the one source of the limits wording, for the card
  and for the history line.

Limits are numbers of the meter type's decimals, parsed with Decimal (never float) and
returned as strings without trailing zeros.  Only a gauge has limits: a counter triggers PM
every N units, an amount is a quantity produced, and a Yes / No meter's good answer is fixed
on its type (S037 decision 7).
"""

import re
from decimal import Decimal

GAUGE = "gauge"
LIMIT_FIELDS = ("min_value", "max_value")
NO_LIMITS = (None, None)

# DECIMAL(14,3): 11 digits before the point, MAX_DECIMALS after it
LIMIT_MAX = Decimal("99999999999.999")
_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")

PICK_A_METER_TYPE = "Pick a meter type"
NO_LIMITS_FOR_KIND = {
    "counter": "A counter has no limits",
    "amount": "An amount per period has no limits",
    "yes_no": "A Yes / No meter has no limits",
}
MIN_ABOVE_MAX = "Min must not be above Max"
TOO_LARGE = "Enter a smaller number"

SOURCE_MODEL = "model"
SOURCE_NODE = "node"

# The three ways a PUT may change a meter
ACTION_LIMITS = "limits"
ACTION_USE_MODEL = "use_model_limits"
ACTION_REMOVE = "remove"


def _decimals_message(decimals):
    if decimals == 0:
        return "Enter a whole number"
    return f"Enter a number with up to {decimals} decimal{'s' if decimals > 1 else ''}"


def _parse_limit(raw, decimals):
    """One limit: None, an int, or a decimal string → Decimal or None; ValueError with the
    user's message otherwise.  A bool and a float are refused (a float is already rounded)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise ValueError(_decimals_message(decimals))
    text = str(raw).strip()
    if not _DECIMAL_RE.match(text):
        raise ValueError(_decimals_message(decimals))
    value = Decimal(text)
    # Trailing zeros are not decimals: "62.50" is 62.5
    places = max(0, -value.normalize().as_tuple().exponent)
    if places > decimals:
        raise ValueError(_decimals_message(decimals))
    if abs(value) > LIMIT_MAX:
        raise ValueError(TOO_LARGE)
    return value


def validate_limits(body, kind, decimals, stored):
    """The limits pair after a write → ``((min, max), errors)``, errors in the masters_core
    shape.  ``stored`` is the pair in force before the write (a row's own pair; a node's first
    override starts from the model's; a create from NO_LIMITS).  An absent field keeps its
    stored value; an explicit null clears it.  The kind check comes first, so a counter with
    "abc" reads "A counter has no limits"; an explicit null on a non-gauge is not a limit sent
    (a form that posts every field passes)."""
    if kind != GAUGE:
        for field in LIMIT_FIELDS:
            if body.get(field) is not None:
                return NO_LIMITS, [{"field": field, "message": NO_LIMITS_FOR_KIND[kind]}]
        return NO_LIMITS, []
    merged = dict(zip(LIMIT_FIELDS, stored))
    for field in LIMIT_FIELDS:
        if field in body:
            try:
                merged[field] = _parse_limit(body[field], decimals)
            except ValueError as exc:
                return stored, [{"field": field, "message": str(exc)}]
    low, high = merged["min_value"], merged["max_value"]
    if low is not None and high is not None and low > high:
        return stored, [{"field": "max_value", "message": MIN_ABOVE_MAX}]
    return (low, high), []


def parse_meter_type_id(body):
    """The meter type of an add → ``(id, errors)``."""
    raw = body.get("meter_type_id")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        return None, [{"field": "meter_type_id", "message": PICK_A_METER_TYPE}]
    return raw, []


def parse_change_action(body, allow_use_model):
    """What a PUT asks → ``(action, errors)``: ``active: false`` removes, ``use_model_limits:
    true`` (a node only) clears the override, anything else sets limits.  A PUT never
    reactivates: an add brings a removed meter back (BR1-18).  The texts are for API callers;
    the screens never send these mixes."""
    keys = {"active", "use_model_limits", *LIMIT_FIELDS} & set(body)
    if "active" in body:
        if body["active"] is not False:
            return None, [{"field": "active", "message": "Add the meter again to bring it back"}]
        if keys != {"active"}:
            return None, [{"field": "active", "message": "Send the removal alone"}]
        return ACTION_REMOVE, []
    if "use_model_limits" in body:
        if not allow_use_model or body["use_model_limits"] is not True:
            return None, [{"field": "use_model_limits", "message": "Only true is accepted here"}]
        if keys != {"use_model_limits"}:
            return None, [{"field": "use_model_limits", "message": "Send the model's limits alone"}]
        return ACTION_USE_MODEL, []
    return ACTION_LIMITS, []


# ---------------------------------------------------------------------------
# Wording — the card's limits line and the history text
# ---------------------------------------------------------------------------

def format_number(value):
    """A stored DECIMAL as the user writes it: no trailing zeros, no exponent ("10", "62.5")."""
    if value is None:
        return None
    text = f"{Decimal(value).normalize():f}"
    return "0" if text == "-0" else text


def _range(unit, pair):
    """"10–60 °C", "up to 60 °C", "from 10 °C", or None when neither limit is set."""
    low, high = (format_number(v) for v in pair)
    if low is not None and high is not None:
        return f"{low}–{high} {unit}"
    if high is not None:
        return f"up to {high} {unit}"
    if low is not None:
        return f"from {low} {unit}"
    return None


def limits_text(meter_type, pair):
    """The card's line for a gauge: "Limits: 10–60 °C" … "No limits"; None for a counter, an
    amount and a Yes / No meter, which show no limits line (BR3-01)."""
    if meter_type["kind"] != GAUGE:
        return None
    text = _range(meter_type["unit"], pair)
    return f"Limits: {text}" if text else "No limits"


def _history_side(meter_type, pair):
    return f"{meter_type['name']}: {_range(meter_type['unit'], pair) or 'no limits'}"


def tracked_meter_change(meter_type, old_pair, new_pair):
    """The history line of a limits write → ``[("meter_limits", old, new)]``, both sides the
    limits in force (BR1-06); none when the limits in force did not change."""
    if same_limits(old_pair, new_pair):
        return []
    return [("meter_limits", _history_side(meter_type, old_pair), _history_side(meter_type, new_pair))]


def same_limits(a, b):
    """Two limit pairs equal by value (Decimal("10.000") equals Decimal("10"))."""
    return all((x is None and y is None) or (x is not None and y is not None and Decimal(x) == Decimal(y))
               for x, y in zip(a, b))



# ---------------------------------------------------------------------------
# A node's meters
# ---------------------------------------------------------------------------

def _pair(row):
    return (row["min_value"], row["max_value"])


def override_of(node_row):
    """The pair a node row sets over its model's meter, or None when it sets none.  An own = 0
    row exists only while it differs from the model (a both-NULL one means "no limits here").
    An own = 1 row of a type the model gained later (active or not, BR2-02) overrides only
    while it holds a limit: *Use the model's limits* clears its pair and keeps the row."""
    if node_row is None:
        return None
    if not node_row["own"]:
        return _pair(node_row) if node_row["active"] else None
    if node_row["min_value"] is None and node_row["max_value"] is None:
        return None
    return _pair(node_row)


def _out_limits(pair):
    return {"min_value": format_number(pair[0]), "max_value": format_number(pair[1])}


def effective_meters(model_meters, node_rows):
    """A node's meters (§ 5.2), ordered by meter type name.  ``model_meters`` are the rows of
    the node's model (none without a model, S033) and ``node_rows`` the node's own rows, each
    with ``meter_type`` ({id, name, unit, kind, decimals, expected_answer}), ``min_value``,
    ``max_value``, ``active``; a node row also has ``own``.

    - an active model meter: the node's override when there is one, else the model's limits;
    - an active own meter whose type is not an active model meter: its own limits;
    - an override of a type no longer on the model, and a removed own meter: left out."""
    node_by_type = {row["meter_type"]["id"]: row for row in node_rows}
    out = []
    model_type_ids = set()
    for row in model_meters:
        if not row["active"]:
            continue
        meter_type = row["meter_type"]
        model_type_ids.add(meter_type["id"])
        model_pair = _pair(row)
        override = override_of(node_by_type.get(meter_type["id"]))
        in_force = override if override is not None else model_pair
        out.append({
            "meter_type": meter_type, "source": SOURCE_MODEL, **_out_limits(in_force),
            "model_min": format_number(model_pair[0]), "model_max": format_number(model_pair[1]),
            "overridden": override is not None,
            "limits_text": limits_text(meter_type, in_force),
            "model_limits_text": limits_text(meter_type, model_pair),
        })
    for row in node_rows:
        meter_type = row["meter_type"]
        if not row["own"] or not row["active"] or meter_type["id"] in model_type_ids:
            continue
        out.append({
            "meter_type": meter_type, "source": SOURCE_NODE, **_out_limits(_pair(row)),
            "model_min": None, "model_max": None, "overridden": False,
            "limits_text": limits_text(meter_type, _pair(row)), "model_limits_text": None,
        })
    out.sort(key=lambda m: (m["meter_type"]["name"].casefold(), m["meter_type"]["id"]))
    return out


def in_force_pair(model_meter, node_row):
    """The limits in force on a node for one meter type: the override, else the model meter's
    (``model_meter`` an active row or None), else the node's own row's."""
    if model_meter is not None:
        override = override_of(node_row)
        return override if override is not None else _pair(model_meter)
    return _pair(node_row) if node_row is not None else NO_LIMITS


def meter_type_of(row, prefix="t_"):
    """The ``meter_type`` dict from a joined row whose meter type columns carry ``prefix``."""
    return {field: row[f"{prefix}{field}"] for field in ("id", "name", "unit", "kind", "decimals", "expected_answer")}
