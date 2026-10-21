"""File storage for equipment documents and photos — thin I/O, no rules.

Layout: one folder per owner (S012, the design of S009) — ``DATA_DIR/equipment/<node_id>/``
or ``DATA_DIR/equipment-models/<model_id>/`` or, for ticket photos (S017) and documents (S018),
``DATA_DIR/tickets/<ticket_id>/`` — holding ``<stored_name>`` (and ``<stored_name>.thumb.jpg``).  Names come from documents_core.stored_name; nothing from the
client reaches a path.

config.DATA_DIR is read at call time, so tests can point it elsewhere.  A file is never
written in place: it goes to a temporary name in the same folder and is moved into place
with os.replace, which is all-or-nothing (also on NFS, because it stays within one folder),
so a half-written file is never served.
"""

import logging
import os
import secrets

import config

logger = logging.getLogger(__name__)

# Owner (documents.OWNERS) -> its folder under DATA_DIR
_OWNER_FOLDERS = {
    "equipment": "equipment",
    "model": "equipment-models",
    "ticket": "tickets",
}


def owner_folder(owner, owner_id):
    return os.path.join(config.DATA_DIR, _OWNER_FOLDERS[owner], str(int(owner_id)))


def file_path(owner, owner_id, name):
    return os.path.join(owner_folder(owner, owner_id), name)


def write_file(owner, owner_id, name, data):
    """Write ``data`` as ``name`` in the owner's folder (created when missing) and return
    its path.  Raises OSError; a temporary file is removed before the error propagates."""
    folder = owner_folder(owner, owner_id)
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(folder, name)
    temp = os.path.join(folder, f".{name}.{secrets.token_hex(4)}.tmp")
    try:
        with open(temp, "xb") as f:
            f.write(data)
        os.replace(temp, final)
    except OSError:
        remove_quietly(temp)
        raise
    return final


def remove_quietly(path):
    """Remove one file during clean-up.  A failure is logged, never raised, so it cannot
    hide the error that caused the clean-up."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Could not remove %s during clean-up: %s", path, exc)


def remove_file(path):
    """Remove one file -> True, or False when it was already missing (the caller logs that).
    Any other OSError propagates: unlike remove_quietly, this is the deletion itself, not
    clean-up after another error."""
    try:
        os.remove(path)
    except FileNotFoundError:
        return False
    return True


def is_file(path):
    return os.path.isfile(path)
