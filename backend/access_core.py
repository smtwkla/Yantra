"""Access — pure rules for roles, permissions and units (S011; no DB, no Flask).

Two sources of rights meet here:

- **token roles** (``admin``, ``it_admin``; ``maintenance_team`` only logs in) hold at every
  site;
- **memberships**: one site role per person and site, with all units of the site or the
  person's chosen units there.  A membership whose ``site_id`` is ``None`` means *every
  site*: the dev stub and the test harness use it, nothing in the database can hold it.

A key in ``config_rbac.SITE_SCOPED`` is checked at a site; every other key is global, the
union of the token roles' keys and every membership's keys (S011 § 5.2).

A membership whose role is not a site role (a typo, or ``it_admin`` written straight into
the database) is ignored entirely: it grants no key, wildcard or not, and no units.
"""

from collections import namedtuple

from config_rbac import PERMISSIONS, ROLE_INCLUDES, ROLES, SITE_ROLES, SITE_SCOPED

ALL_UNITS_KEY = "equipment:read_all_units"

# site_id: int, or None for every site; role: text from the DB; all_units: bool
Membership = namedtuple("Membership", "site_id role all_units")


def expand_roles(roles):
    """Expand a list of roles by following ROLE_INCLUDES transitively.

    E.g. ['maint_engineer'] → {'maint_engineer', 'maint_technician', 'maint_operator'}.
    """
    expanded = set(roles)
    queue = list(roles)
    while queue:
        role = queue.pop()
        for included in ROLE_INCLUDES.get(role, ()):
            if included not in expanded:
                expanded.add(included)
                queue.append(included)
    return expanded


def compute_permissions(roles):
    """Return the sorted list of permission keys granted to any of the given roles.

    Roles are expanded via ROLE_INCLUDES before checking permissions.
    """
    if isinstance(roles, str):
        roles = [roles]
    if "admin" in roles:
        return sorted(PERMISSIONS.keys())

    effective = expand_roles(roles)

    perms = set()
    for key, granted_roles in PERMISSIONS.items():
        if granted_roles == ("*",) and any(r in ROLES for r in effective):
            perms.add(key)
        elif any(r in granted_roles for r in effective):
            perms.add(key)
    return sorted(perms)


def roles_holding(perm_key):
    """The site roles that hold ``perm_key`` (through ROLE_INCLUDES), in SITE_ROLES order: who an
    alert about that key may reach (S074 § 5.6).  A wildcard key gives every site role; an
    unknown key none (fail-closed)."""
    return tuple(role for role in SITE_ROLES if perm_key in compute_permissions([role]))


def valid_memberships(memberships):
    return [m for m in memberships if m.role in SITE_ROLES]


def _matches(membership, site_id):
    """A wildcard membership is at every site; a real one only at its own.  A query for
    site None matches no real membership."""
    return membership.site_id is None or (site_id is not None and membership.site_id == site_id)


def global_permissions(token_roles, memberships):
    """Every key the user holds somewhere: the token roles' keys and every site role's."""
    keys = set(compute_permissions(list(token_roles)))
    for membership in valid_memberships(memberships):
        keys.update(compute_permissions([membership.role]))
    return sorted(keys)


def permissions_at(token_roles, memberships, site_id):
    """Every key the user holds at ``site_id``: the token roles' keys and the keys of the
    role held there (every key for admin)."""
    keys = set(compute_permissions(list(token_roles)))
    for membership in valid_memberships(memberships):
        if _matches(membership, site_id):
            keys.update(compute_permissions([membership.role]))
    return sorted(keys)


def has_key_at(key, token_roles, memberships, site_id):
    assert key in SITE_SCOPED, f"{key} is not a site-scoped key"
    return "admin" in token_roles or key in permissions_at(token_roles, memberships, site_id)


def every_unit_by_token(key, token_roles):
    """True when the token alone gives every unit for ``key``: admin, or token roles that
    grant both the key and equipment:read_all_units.  Never for a key the token roles do
    not grant themselves, so a future key fails closed (BR2-01)."""
    if "admin" in token_roles:
        return True
    token_keys = compute_permissions(list(token_roles))
    return key in token_keys and ALL_UNITS_KEY in token_keys


def unit_ids_for(key, token_roles, memberships, units, user_unit_ids):
    """The units where the user holds ``key`` → ``None`` for every unit, else a set of ids.

    ``units``: ``(unit_id, site_id)`` of the active units (needed only when a membership
    has all units); ``user_unit_ids``: ``(unit_id, site_id)`` of the user's own active unit
    rows.  Every unit only for admin, or when the token roles grant both ``key`` and
    ``equipment:read_all_units`` (IT admin, for today's keys); otherwise the units of the
    sites whose role grants ``key``: all the site's units, or the user's rows there.  A row
    at a site without a membership counts for nothing.
    """
    assert key in SITE_SCOPED, f"{key} is not a site-scoped key"
    if every_unit_by_token(key, token_roles):
        return None
    result = set()
    for membership in valid_memberships(memberships):
        if key not in compute_permissions([membership.role]):
            continue
        pool = units if membership.all_units else user_unit_ids
        result.update(unit_id for unit_id, site_id in pool if _matches(membership, site_id))
    return result


def display_role(token_roles, memberships):
    """The most privileged role held anywhere, for display only (None for a login-only
    user).  admin first, then by ROLES order."""
    if "admin" in token_roles:
        return "admin"
    held = set(token_roles) | {m.role for m in valid_memberships(memberships)}
    return next((role for role in ROLES if role in held), None)
