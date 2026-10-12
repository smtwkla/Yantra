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
    "maint_technician",
    "maint_operator",
)

# Role inheritance — a role automatically gains all permissions of included roles.
# Maintenance is a ladder: manager ⊇ engineer ⊇ technician ⊇ maint_operator.
# it_admin stands apart: housekeeping and settings, not maintenance work.
ROLE_INCLUDES = {
    "maint_manager": ("maint_engineer",),
    "maint_engineer": ("maint_technician",),
    "maint_technician": ("maint_operator",),
}

PERMISSIONS = {
    # Masters — machine register, locations, codes
    "masters:read": ("*",),
    "masters:edit": ("maint_engineer", "it_admin"),

    # Settings — DB status, escalation times, notification channels
    "settings:read": ("maint_manager", "it_admin"),
    "settings:edit": ("it_admin",),
}
