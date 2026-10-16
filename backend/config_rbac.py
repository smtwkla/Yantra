"""RBAC policy — single source of truth for roles and permissions.

ROLES: ordered most → least privileged.
ROLE_INCLUDES: maps a role to roles it inherits (transitive).
PERMISSIONS: maps 'module:action' → tuple of granted roles.

Rules:
  - admin bypasses all checks in code — never list it here.
  - ('*',) means any authenticated role. Never mix '*' with other roles.
  - Unknown permission keys grant nobody (fail-closed).
  - Order entries to match sidebar nav order for readability.
  - ROLE_INCLUDES is expanded transitively by compute_permissions().

Roles and the first-cut permission matrix: docs/Plan.MD § 3.
"""

# Ordered most → least privileged
ROLES = (
    "maint_manager",
    "maint_engineer",
    "it_admin",
    "maint_storekeeper",
    "maint_technician",
    "maint_operator",
)

# Role inheritance — a role automatically gains all permissions of included roles.
# Maintenance is a ladder: manager ⊇ engineer ⊇ technician ⊇ maint_operator.
# it_admin stands apart: housekeeping and settings, not maintenance work.
# maint_storekeeper stands apart too: issuing stock is not part of the
# maintenance ladder. No v1 permissions beyond '*' — spares come later.
ROLE_INCLUDES = {
    "maint_manager": ("maint_engineer",),
    "maint_engineer": ("maint_technician",),
    "maint_technician": ("maint_operator",),
}

PERMISSIONS = {
    # Equipment — the equipment register (S002) and equipment classes
    "equipment:read": ("*",),
    # A scope key, not a read level: it says *where* (every unit, not only the user's
    # unit-access rows), so it departs from the read_basic/read/read_senior naming.
    "equipment:read_all_units": ("maint_manager", "it_admin"),
    "equipment:edit": ("maint_engineer", "it_admin"),
    # Removed documents (S008): list them, restore one, delete one for good.  Senior roles
    # only: engineers remove, but do not bring back or erase (ISO 27001 A.5.3, A.8.2).
    "equipment:purge_documents": ("maint_manager", "it_admin"),

    # Masters — machine register, locations, codes
    "masters:read": ("*",),
    "masters:edit": ("it_admin",),
    "masters:read_senior": ("it_admin",),   # users' unit access

    # Settings — DB status, escalation times, notification channels
    "settings:read": ("maint_manager", "it_admin"),
    "settings:edit": ("it_admin",),
}
