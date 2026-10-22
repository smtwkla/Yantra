"""RBAC policy — single source of truth for roles and permissions.

ROLES: ordered most → least privileged (the order is for display: the "role" /auth/me shows).
ROLE_INCLUDES: maps a role to roles it inherits (transitive).
PERMISSIONS: maps 'module:action' → tuple of granted roles.

Rules:
  - admin bypasses all checks in code — never list it here.
  - ('*',) means any authenticated role. Never mix '*' with other roles.
  - Unknown permission keys grant nobody (fail-closed).
  - Order entries to match sidebar nav order for readability.
  - ROLE_INCLUDES is expanded transitively by compute_permissions().

Where roles come from (S011, a deliberate departure from the base RBAC pattern, which takes
every role from the token):
  - TOKEN_ROLES and admin come from Keycloak: they hold at every site.
  - SITE_ROLES come from Yantra's database, one per person and site (table memberships):
    a role's keys hold only at that site (SITE_SCOPED keys) and add to the global union
    (every other key).  The DB stores the role as text, validated against SITE_ROLES.
  - LOGIN_ROLE lets a user log in and grants nothing by itself.

Roles and the first-cut permission matrix: docs/Plan.MD § 3.
"""

# Ordered most → least privileged
ROLES = (
    "maint_manager",
    "maint_engineer",
    "it_admin",
    "maint_storekeeper",
    "maint_supervisor",
    "maint_technician",
    "maint_operator",
)

# Keycloak client roles that grant permissions.  admin comes from the realm (auth_utils).
TOKEN_ROLES = ("it_admin",)

# The Keycloak client role that only lets a user log in; deliberately not in ROLES, so it
# matches no ('*',) key and grants nothing: access comes from memberships.
LOGIN_ROLE = "maintenance_team"

# The roles a person holds per site (S011, A1), in the order the Team dialog offers them
SITE_ROLES = (
    "maint_manager",
    "maint_engineer",
    "maint_supervisor",
    "maint_technician",
    "maint_operator",
    "maint_storekeeper",
)

# The one role an engineer may give at their site (S011 A1, user decision at gate A)
TECHNICIAN_ROLE = "maint_technician"

# The roles a person without a login may hold (S017 user decision 5, changing S011 A1's
# "technician only"): such a row grants nothing, it places the person at the site's units for
# the pick-lists (a ticket's reported-by, S018's labour).  Only IT admin sets an Operator row.
NO_LOGIN_ROLES = (TECHNICIAN_ROLE, "maint_operator")

# The site roles a ticket may be assigned to, manually or automatically on acknowledge / start
# (S018 § 5.8): assignment hands out maintenance work, so the maintenance ladder from the
# technician up.  Contractor firms hold a technician row, so AMC vendors qualify.
ASSIGNABLE_ROLES = (TECHNICIAN_ROLE, "maint_engineer", "maint_manager")

# Roles that may use Yantra from the plant network only (S013 network gate): a deny list, a
# deliberate departure from the base pattern's access:wan allow list, because a person can hold
# IT admin and a site role at once.  Token roles only: the gate never reads memberships, so a
# site role added here would need the gate to read them (S013 § 5.3).
# 18-10-2026 (KLA, S013 gate A): IT admin only, the privileged account for logins, masters and
# network settings (ISO 27001 A.8.2); managers work from the floor on mobile data, so not them.
INTERNAL_ONLY_ROLES = ("it_admin",)

# Role inheritance — a role automatically gains all permissions of included roles.
# Maintenance is a ladder: manager ⊇ engineer ⊇ technician ⊇ maint_operator.
# it_admin stands apart: housekeeping and settings, not maintenance work — with one
# exception, tickets (S017 user decision 7: IT admin may read, raise and work them).
# maint_storekeeper stands apart too: issuing stock is not part of the
# maintenance ladder. No v1 permissions beyond '*' — spares come later.
# maint_supervisor is production-side (TPM autonomous maintenance): above the operator,
# off the maintenance ladder, so a supervisor does not work tickets.
ROLE_INCLUDES = {
    "maint_manager": ("maint_engineer",),
    "maint_engineer": ("maint_technician",),
    "maint_technician": ("maint_operator",),
    "maint_supervisor": ("maint_operator",),
}

PERMISSIONS = {
    # Equipment — the equipment register (S002) and equipment classes
    "equipment:read": ("*",),
    # A scope key, not a read level: it says *where* (every unit, not only the user's
    # memberships), so it departs from the read_basic/read/read_senior naming.  Managers get
    # their breadth from "all units of the site" in their membership instead (S011 § 5.3).
    "equipment:read_all_units": ("it_admin",),
    "equipment:edit": ("maint_engineer", "it_admin"),
    # Removed documents (S008): list them, restore one, delete one for good.  Senior roles
    # only: engineers remove, but do not bring back or erase (ISO 27001 A.5.3, A.8.2).
    "equipment:purge_documents": ("maint_manager", "it_admin"),

    # Tickets (S017) — one ticket for every problem found on equipment, a breakdown or a
    # defect (Plan.MD § 4.2).  Granted to the operator, so the maintenance ladder and the
    # supervisor inherit them.  IT admin holds them too (user decision 7, 20-10-2026), a
    # departure from "maintenance work is not IT admin's"; the storekeeper holds neither.
    "ticket:read": ("maint_operator", "it_admin"),
    "ticket:raise": ("maint_operator", "it_admin"),
    # Working the ticket (S018 § 5.7).  Back in service by whoever has operator rights at the
    # unit (Plan.MD § 4.2), so production confirms the restoration; the work itself and the
    # labour by the maintenance ladder from the technician up; assignment, send back and close
    # by the engineer (managers inherit).  The supervisor stays off the ladder.  IT admin holds
    # all four (S017 user decision 7) but no site role, so it is never assigned.
    "ticket:work": ("maint_technician", "it_admin"),
    "ticket:restore": ("maint_operator", "it_admin"),
    "ticket:assign": ("maint_engineer", "it_admin"),
    "ticket:close": ("maint_engineer", "it_admin"),
    # Correcting a work note (S027): a typo or wrong fact, keeping the earlier text.  Adding a
    # note is ticket:restore's; editing someone else's record is a narrower right (ISO 27001
    # A.5.15).  The holders equal ticket:close's today, but the two can drift.
    "ticket:edit_notes": ("maint_engineer", "it_admin"),

    # Masters — machine register, locations, codes
    "masters:read": ("*",),
    "masters:edit": ("it_admin",),
    "masters:read_senior": ("it_admin",),   # everyone's logins and access

    # Team and trades (S010 A1): the maintenance side knows who can do what; IT admin
    # maintains masters too.  Managers inherit it from the engineer.  A person's login, and
    # the active flag of a person who has one, need masters:edit as well (masters.py).
    "people:edit": ("maint_engineer", "it_admin"),
    # Engineers assign Technicians at their own site (S011 A1, gate A): the one grant
    # delegated to the maintenance side; every other role is IT admin's (masters:edit).
    "people:assign_technicians": ("maint_engineer", "it_admin"),

    # Failure codes (S016): failure modes, causes and maintenance actions, the ISO 14224
    # pick-lists of tickets.  Engineers keep them (managers inherit it); IT admin too, as
    # masters housekeeping.  Global, not site-scoped: the lists are the same at every site.
    "failure_codes:edit": ("maint_engineer", "it_admin"),

    # Settings — DB status, escalation times, notification channels
    "settings:read": ("maint_manager", "it_admin"),
    "settings:edit": ("it_admin",),

    # Access log (S013): who reached the API, from where, and the refusals.  The people who
    # own the security question; global, not site-scoped.
    "access_log:view": ("maint_manager", "it_admin"),

    # Notifications (S021): turn alerts on for one's own devices, list and remove them, send
    # oneself a test.  Any logged-in role; the routes also need a Team record (alerts go to a
    # person).  Global, not site-scoped: a device is not at a site.
    "push:subscribe": ("*",),
}

# Keys checked at the record's site (has_perm_at, accessible_unit_ids).  Every later
# ticket, PM, reading and report key joins this list.  A key not listed here is global.
SITE_SCOPED = frozenset({
    "equipment:read",
    "equipment:edit",
    "equipment:purge_documents",
    "people:assign_technicians",
    "ticket:read",
    "ticket:raise",
    "ticket:work",
    "ticket:restore",
    "ticket:assign",
    "ticket:close",
    "ticket:edit_notes",
})
