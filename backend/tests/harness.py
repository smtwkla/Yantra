"""The X-Test-Role harness's user, shared by the pytest suite (conftest.py) and the browser
tests' backend (tooling/e2e/e2e_backend.py, S024), so both build g.user the same way.

No pytest import: the e2e backend imports this outside pytest.  It stays under tests/,
which .dockerignore keeps out of the production image.
"""

from access_core import Membership
from auth_utils import make_user
from config_rbac import LOGIN_ROLE, SITE_ROLES, TOKEN_ROLES


def harness_user(role_name, username, name=None):
    """The g.user for an X-Test-Role header (S011 § 5.8):
    - a site role: that role at every site (a wildcard membership; DB memberships ignored),
      all units only for the manager; the unit rows come from the DB, as in production;
    - admin, it_admin, maintenance_team: token roles; memberships from the DB, as in production;
    - anything else ("nobody"): no token role and no membership, never a wildcard.
    ``name`` is the display name (default "Test <role>"); the e2e backend gives each seed
    person their own, so the top bar shows who is acting."""
    name = name or f"Test {role_name}"
    if role_name in SITE_ROLES:
        return make_user(username, name, [LOGIN_ROLE], [Membership(None, role_name, role_name == "maint_manager")])
    if role_name in ("admin", LOGIN_ROLE, *TOKEN_ROLES):
        return make_user(username, name, [role_name])
    return make_user(username, name, [], [])
