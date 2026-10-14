"""Shared database utilities — per-request connection, transactions, row helpers."""

from contextlib import contextmanager
from datetime import date, datetime

import pymysql
from flask import g

from config import DB_CONFIG
from local_db import DBUnavailable, describe_error, ensure_schema, get_pooled_db, return_pooled_db


def get_db():
    """Return a per-request DB connection from the pool, cached on g.

    Raises DBUnavailable (→ 503) while the schema cannot be brought up to date,
    or when no connection can be made.
    Usage in routes:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
    """
    if "db" not in g:
        error = ensure_schema(DB_CONFIG)
        if error:
            raise DBUnavailable(error)
        try:
            # The pool pings on checkout, so a connection that died while idle is replaced
            # here; an error means the server itself cannot be reached.
            g.db = get_pooled_db()
        except pymysql.err.OperationalError as exc:
            raise DBUnavailable(describe_error(exc)) from exc
    return g.db


def close_db(exc):
    """Teardown: return the per-request DB connection to the pool."""
    return_pooled_db(g.pop("db", None))


@contextmanager
def transaction(conn):
    """Run the block as one transaction: commit on success, roll back on any exception.

    Pool connections are autocommit, so anything that must be atomic (replace a
    set of rows; check-then-update) goes through here.
    """
    conn.begin()
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


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
