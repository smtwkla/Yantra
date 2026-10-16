"""Request-level pieces shared by the blueprints — the API error shape, the
duplicate-key mapping, the acting user and body validation.

Errors follow ``{error, field?}``.  Handlers are registered once at app level
(register_error_handlers), so every blueprint gets the same mapping; each
module adds the names of its UNIQUE keys to UNIQUE_KEY_ERRORS at import.
"""

import re

import pymysql
from flask import g, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from config import UPLOAD_MAX_MB_CEILING

MYSQL_DUPLICATE_ENTRY = 1062

# Named UNIQUE index -> (field to flag or None, plain message).  Filled by each module.
UNIQUE_KEY_ERRORS = {}

# MariaDB says  for key 'uq_x'  — newer servers say  for key 'table.uq_x'
# Anchored to the end: the duplicated value comes first and can be user text.
_DUPLICATE_KEY_RE = re.compile(r"for key '(?:\w+\.)?(\w+)'$")


class ApiError(Exception):
    """A refusal the user can act on; becomes ``{error, field?}`` with ``status``."""

    def __init__(self, message, status, field=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.field = field


def _error_response(exc):
    body = {"error": exc.message}
    if exc.field:
        body["field"] = exc.field
    return jsonify(body), exc.status


def _integrity_error(exc):
    """A duplicate caught by a UNIQUE or primary key is a 409; anything else is a bug."""
    if exc.args[0] != MYSQL_DUPLICATE_ENTRY:
        raise exc
    match = _DUPLICATE_KEY_RE.search(str(exc.args[1]))
    field, message = UNIQUE_KEY_ERRORS.get(
        match.group(1) if match else None,
        (None, "Conflicts with an existing record; reload and try again"),
    )
    return _error_response(ApiError(message, 409, field))


def _request_too_large(_exc):
    """A backstop: Werkzeug refuses a body over MAX_CONTENT_LENGTH only when the form is
    parsed, after the upload route's own size check has answered for anything over the
    upload limit (S006 § 5.2).  JSON, so the dialog shows it beside the file field."""
    return _error_response(ApiError(f"The file is larger than {UPLOAD_MAX_MB_CEILING} MB", 413, "file"))


def register_error_handlers(app):
    app.register_error_handler(ApiError, _error_response)
    app.register_error_handler(pymysql.err.IntegrityError, _integrity_error)
    app.register_error_handler(RequestEntityTooLarge, _request_too_large)


def actor():
    """The acting user, from the validated token — never from the request body."""
    return g.user["username"]


def clean_body(validator, creating):
    """Validate the JSON body with ``validator(body, creating)``; the first error becomes a 400."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("Request body must be a JSON object", 400)
    clean, errors = validator(body, creating)
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    return clean


DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200
# Far past any real register (MAX_PAGE x MAX_PER_PAGE = 20 million rows), and it keeps
# the OFFSET a number MariaDB accepts: an unbounded page overflows it (error 1064).
MAX_PAGE = 100_000


def int_arg(name, default, minimum, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    # isascii: str.isdigit() also accepts digits such as '²' that int() rejects
    if not (raw.isascii() and raw.isdigit()) or int(raw) < minimum or (maximum is not None and int(raw) > maximum):
        bounds = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise ApiError(f"{name} must be a whole number {bounds}", 400, name)
    return int(raw)


def enum_arg(name, allowed):
    raw = request.args.get(name)
    if raw is not None and raw not in allowed:
        raise ApiError(f"{name} must be one of: {', '.join(allowed)}", 400, name)
    return raw


def like_pattern(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
