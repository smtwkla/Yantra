"""Shared database utilities — cursors, date formatting, row helpers."""

from datetime import date, datetime
from decimal import Decimal


def row_to_dict(row):
    """Convert a DB row dict to a JSON-safe dict.

    - datetime → ISO string with IST offset (+05:30)
    - date → ISO string (YYYY-MM-DD)
    - Decimal → left as-is (Flask's jsonify serialises to string, which is safe)
    """
    if row is None:
        return None

    result = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            result[key] = value.strftime("%Y-%m-%dT%H:%M:%S+05:30")
        elif isinstance(value, date):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def rows_to_list(rows):
    """Convert a list of DB row dicts to JSON-safe dicts."""
    return [row_to_dict(r) for r in rows]
