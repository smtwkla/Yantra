"""RBAC policy and enforcement tests.

Written first, before any module tests — validates the policy file itself
and catches permission mistakes immediately.
"""

import pytest
from flask import Flask, g

from access_core import Membership
from auth_utils import compute_permissions, expand_roles, has_perm, has_perm_at, make_user, require_perm
from config_rbac import (
    INTERNAL_ONLY_ROLES, LOGIN_ROLE, NO_LOGIN_ROLES, PERMISSIONS, ROLE_INCLUDES, ROLES, SITE_ROLES, SITE_SCOPED,
    TOKEN_ROLES,
)


class TestPolicyStructure:
    """The policy file is well-formed."""

    def test_all_permission_keys_have_colons(self):
        for key in PERMISSIONS:
            assert ":" in key, f"Permission key '{key}' missing colon separator"

    def test_all_granted_roles_are_known(self):
        for key, roles in PERMISSIONS.items():
            if roles == ("*",):
                continue
            for role in roles:
                assert role in ROLES, f"Permission '{key}' grants unknown role '{role}'"

    def test_admin_not_in_permission_tuples(self):
        for key, roles in PERMISSIONS.items():
            assert "admin" not in roles, f"Permission '{key}' lists 'admin' — admin bypasses in code"

    def test_wildcard_not_mixed_with_roles(self):
        for key, roles in PERMISSIONS.items():
            if "*" in roles:
                assert roles == ("*",), f"Permission '{key}' mixes '*' with other roles"

    def test_permission_values_are_tuples(self):
        # A bare string ("it_admin") would match roles by substring
        for key, roles in PERMISSIONS.items():
            assert isinstance(roles, tuple), f"Permission '{key}' is not a tuple"

    def test_internal_only_roles_are_known_and_exclude_admin(self):
        """S013 BR1-12: the gate's deny list names real roles; admin bypasses in code."""
        assert isinstance(INTERNAL_ONLY_ROLES, tuple)
        assert set(INTERNAL_ONLY_ROLES) <= set(ROLES)
        assert "admin" not in INTERNAL_ONLY_ROLES

    def test_internal_only_roles_come_from_the_token(self):
        """The gate reads token roles only (S013 § 5.3): a site role here would never match."""
        assert set(INTERNAL_ONLY_ROLES) <= set(TOKEN_ROLES)

    def test_role_includes_targets_are_known(self):
        for parent, children in ROLE_INCLUDES.items():
            assert parent in ROLES, f"ROLE_INCLUDES key '{parent}' not in ROLES"
            for child in children:
                assert child in ROLES, f"ROLE_INCLUDES '{parent}' includes unknown role '{child}'"


class TestRoleSources:
    """S011 § 8: which roles come from the token, which from memberships."""

    def test_site_scoped_keys_exist(self):
        assert SITE_SCOPED <= set(PERMISSIONS)

    def test_site_roles_are_roles_and_exclude_it_admin(self):
        assert set(SITE_ROLES) <= set(ROLES)
        assert "it_admin" not in SITE_ROLES
        assert set(TOKEN_ROLES) == {"it_admin"}

    def test_login_role_is_not_a_role(self):
        assert LOGIN_ROLE not in ROLES
        assert compute_permissions([LOGIN_ROLE]) == []

    def test_all_units_is_it_admins_only(self):
        assert PERMISSIONS["equipment:read_all_units"] == ("it_admin",)

    @pytest.mark.parametrize("key", ["masters:edit", "masters:read_senior", "settings:edit"])
    def test_no_site_role_holds_the_grant_power(self, key):
        """BR3-04: granting stays IT admin's; no site role may hold masters:edit."""
        for role in SITE_ROLES:
            assert key not in compute_permissions([role]), (role, key)

    def test_assign_technicians_holders(self):
        holders = {role for role in ROLES if "people:assign_technicians" in compute_permissions([role])}
        assert holders == {"maint_engineer", "maint_manager", "it_admin"}

    def test_failure_codes_edit_holders(self):
        """S016 § 5.5: engineers (and so managers) and IT admin keep the failure codes; a
        global key, the lists are the same at every site."""
        holders = {role for role in ROLES if "failure_codes:edit" in compute_permissions([role])}
        assert holders == {"maint_engineer", "maint_manager", "it_admin"}
        assert "failure_codes:edit" not in SITE_SCOPED

    def test_improvement_keys(self):
        """S067 § 5.5, Q1.3 a: read by the operator and up and IT admin; edit by the engineer (so
        the manager), not IT admin; neither for the storekeeper.  Both site-scoped."""
        readers = {role for role in ROLES if "improvement:read" in compute_permissions([role])}
        editors = {role for role in ROLES if "improvement:edit" in compute_permissions([role])}
        assert readers == set(ROLES) - {"maint_storekeeper"}
        assert editors == {"maint_engineer", "maint_manager"}
        assert {"improvement:read", "improvement:edit"} <= SITE_SCOPED

    def test_procedure_keys(self):
        """S075 § 5.7, Q6.3 a: one-point lessons are written by the engineer (so the manager); not IT
        admin, not the supervisor or the floor roles.  Site-scoped, checked per record."""
        editors = {role for role in ROLES if "procedure:edit" in compute_permissions([role])}
        assert editors == {"maint_engineer", "maint_manager"}
        assert "procedure:edit" in SITE_SCOPED

    def test_improvement_verify_and_note(self):
        """S072 § 5.8: verify by the engineer (so the manager), as edit today; a note by every reader
        at the site but IT admin (D6), never the storekeeper.  Both site-scoped."""
        verifiers = {role for role in ROLES if "improvement:verify" in compute_permissions([role])}
        noters = {role for role in ROLES if "improvement:note" in compute_permissions([role])}
        assert verifiers == {"maint_engineer", "maint_manager"}
        assert noters == set(ROLES) - {"maint_storekeeper", "it_admin"}
        assert {"improvement:verify", "improvement:note"} <= SITE_SCOPED

    @pytest.mark.parametrize("key", ["ticket:read", "ticket:raise", "ticket:restore"])
    def test_ticket_keys(self, key):
        """S017 § 5.6, S018 § 5.7: every maintenance role, the supervisor and IT admin; not the
        storekeeper.  Site-scoped, so checked at the ticket's site."""
        holders = {role for role in ROLES if key in compute_permissions([role])}
        assert holders == set(ROLES) - {"maint_storekeeper"}
        assert key in SITE_SCOPED

    def test_ticket_work_holders(self):
        """S018 § 5.7: the maintenance ladder from the technician up, and IT admin; not the
        supervisor (production side)."""
        holders = {role for role in ROLES if "ticket:work" in compute_permissions([role])}
        assert holders == {"maint_technician", "maint_engineer", "maint_manager", "it_admin"}
        assert "ticket:work" in SITE_SCOPED

    @pytest.mark.parametrize("key", ["ticket:assign", "ticket:close", "ticket:edit_notes"])
    def test_ticket_assign_and_close_holders(self, key):
        """S018 § 5.7: the engineer (so the manager) and IT admin; S027's note correction too."""
        holders = {role for role in ROLES if key in compute_permissions([role])}
        assert holders == {"maint_engineer", "maint_manager", "it_admin"}
        assert key in SITE_SCOPED

    def test_reading_log_holders(self):
        """S039 § 3, U2: the operator and up (the supervisor and the maintenance ladder inherit
        it); not IT admin, not the storekeeper.  Site-scoped, so checked at the node's site."""
        holders = {role for role in ROLES if "reading:log" in compute_permissions([role])}
        assert holders == {"maint_operator", "maint_supervisor", "maint_technician", "maint_engineer", "maint_manager"}
        assert "reading:log" in SITE_SCOPED

    def test_ticket_backdate_is_held_by_admin_only_and_is_global(self):
        """S028: no role holds it; admin has it by the bypass; not site-scoped."""
        assert PERMISSIONS["ticket:backdate"] == ()
        assert not [role for role in ROLES if "ticket:backdate" in compute_permissions([role])]
        assert "ticket:backdate" in compute_permissions(["admin"])
        assert "ticket:backdate" not in SITE_SCOPED

    def test_no_login_roles(self):
        """S017 user decision 5: without a login, Technician or Operator; both site roles."""
        assert set(NO_LOGIN_ROLES) == {"maint_technician", "maint_operator"}
        assert set(NO_LOGIN_ROLES) <= set(SITE_ROLES)

    def test_supervisor_is_off_the_maintenance_ladder(self):
        assert expand_roles(["maint_supervisor"]) == {"maint_supervisor", "maint_operator"}
        assert compute_permissions(["maint_supervisor"]) == compute_permissions(["maint_operator"])
        assert not any("maint_supervisor" in expand_roles([r]) for r in ROLES if r != "maint_supervisor")


class TestRoleExpansion:

    def test_maintenance_ladder_is_transitive(self):
        assert expand_roles(["maint_manager"]) == {
            "maint_manager", "maint_engineer", "maint_technician", "maint_operator",
        }

    def test_technician_includes_operator(self):
        assert expand_roles(["maint_technician"]) == {"maint_technician", "maint_operator"}

    def test_it_admin_stands_apart(self):
        assert expand_roles(["it_admin"]) == {"it_admin"}

    def test_storekeeper_stands_apart(self):
        assert expand_roles(["maint_storekeeper"]) == {"maint_storekeeper"}

    def test_operator_no_expansion(self):
        assert expand_roles(["maint_operator"]) == {"maint_operator"}


class TestComputePermissions:

    def test_admin_gets_all_permissions(self):
        assert set(compute_permissions(["admin"])) == set(PERMISSIONS)

    def test_unknown_role_gets_nothing(self):
        assert compute_permissions(["unknown_role"]) == []

    def test_every_role_gets_wildcard_permissions(self):
        wildcard = {k for k, v in PERMISSIONS.items() if v == ("*",)}
        for role in ROLES:
            assert wildcard <= set(compute_permissions([role])), role

    @pytest.mark.parametrize("role, expected", [
        # S017: ticket:read and ticket:raise to the operator, so to every maintenance role and
        # the supervisor; IT admin too (user decision 7); never the storekeeper.  S018: restore to
        # the operator; work to the technician; assign and close to the engineer; all to IT admin.
        # S021: push:subscribe to every role ('*'): anyone may turn notifications on
        # S039: reading:log to the operator, so to the supervisor and the maintenance ladder; not IT admin
        # S067: improvement:read to the operator and IT admin; improvement:edit to the engineer only
        # S072: improvement:note to the operator (not IT admin); improvement:verify to the engineer
        # S075: procedure:edit to the engineer (so the manager); not IT admin, not the supervisor
        ("maint_operator",    {"equipment:read", "masters:read", "push:subscribe", "ticket:read", "ticket:raise", "ticket:restore",
                               "reading:log", "improvement:read", "improvement:note"}),
        ("maint_technician",  {"equipment:read", "masters:read", "push:subscribe", "ticket:read", "ticket:raise", "ticket:restore",
                               "ticket:work", "reading:log", "improvement:read", "improvement:note"}),
        ("maint_supervisor",  {"equipment:read", "masters:read", "push:subscribe", "ticket:read", "ticket:raise", "ticket:restore",
                               "reading:log", "improvement:read", "improvement:note"}),
        ("maint_engineer",    {"equipment:read", "masters:read", "push:subscribe", "equipment:edit", "people:edit",
                               "people:assign_technicians", "failure_codes:edit", "ticket:read", "ticket:raise",
                               "ticket:restore", "ticket:work", "ticket:assign", "ticket:close",
                               "ticket:edit_notes", "reading:log", "improvement:read", "improvement:edit",
                               "improvement:note", "improvement:verify", "procedure:edit"}),
        # S011: the manager's breadth is "all units of the site" in the membership, not read_all_units
        ("maint_manager",     {"equipment:read", "masters:read", "push:subscribe", "equipment:edit",
                               "equipment:purge_documents", "settings:read", "people:edit",
                               "people:assign_technicians", "access_log:view", "failure_codes:edit",
                               "ticket:read", "ticket:raise", "ticket:restore", "ticket:work", "ticket:assign",
                               "ticket:close", "ticket:edit_notes", "reading:log", "improvement:read",
                               "improvement:edit", "improvement:note", "improvement:verify", "procedure:edit"}),
        ("it_admin",          {"equipment:read", "equipment:read_all_units", "masters:read", "push:subscribe", "masters:edit",
                               "masters:read_senior", "equipment:edit", "equipment:purge_documents",
                               "settings:read", "settings:edit", "people:edit", "people:assign_technicians",
                               "access_log:view", "failure_codes:edit", "ticket:read", "ticket:raise",
                               "ticket:restore", "ticket:work", "ticket:assign", "ticket:close",
                               "ticket:edit_notes", "improvement:read"}),
        ("maint_storekeeper", {"equipment:read", "masters:read", "push:subscribe"}),
    ])
    def test_role_matrix(self, role, expected):
        assert set(compute_permissions([role])) == expected

    def test_multi_role_union(self):
        perms = set(compute_permissions(["maint_operator", "it_admin"]))
        assert perms == set(compute_permissions(["maint_operator"])) | set(compute_permissions(["it_admin"]))

    def test_accepts_single_role_string(self):
        assert compute_permissions("it_admin") == compute_permissions(["it_admin"])


@pytest.fixture
def ctx():
    app = Flask(__name__)
    with app.test_request_context("/x"):
        yield


def _user(roles):
    """Token roles; a site role in the list becomes a wildcard membership (no DB needed)."""
    token = [r for r in roles if r not in SITE_ROLES]
    memberships = [Membership(None, r, False) for r in roles if r in SITE_ROLES]
    return make_user("u", "U", token, memberships)


class TestHasPerm:

    def test_no_user_is_false(self, ctx):
        assert has_perm("masters:read") is False

    def test_admin_always_true(self, ctx):
        g.user = _user(["admin"])
        assert has_perm("masters:read") is True
        assert has_perm("no_such:key") is True

    def test_unknown_key_false_for_non_admin(self, ctx):
        g.user = _user(["it_admin"])
        assert has_perm("no_such:key") is False

    def test_granted_and_denied(self, ctx):
        g.user = _user(["maint_operator"])
        assert has_perm("masters:read") is True
        assert has_perm("settings:read") is False

    def test_held_somewhere_from_a_site_role(self, ctx):
        g.user = make_user("u", "U", [LOGIN_ROLE], [Membership(1, "maint_engineer", False)])
        assert has_perm("equipment:edit") is True
        assert has_perm_at("equipment:edit", 1) is True
        assert has_perm_at("equipment:edit", 2) is False

    def test_a_global_key_at_a_site_is_a_programming_error(self, ctx):
        g.user = _user(["it_admin"])
        with pytest.raises(AssertionError):
            has_perm_at("masters:edit", 1)


@require_perm("settings:edit")
def _guarded():
    return "ok"


class TestRequirePerm:

    def test_allows_holder(self, ctx):
        g.user = _user(["it_admin"])
        assert _guarded() == "ok"

    def test_blocks_non_holder_with_403(self, ctx):
        g.user = _user(["maint_manager"])
        response, status = _guarded()
        assert status == 403
        # S064 UX-13 row 1: plain words on the screen; the key needed goes to the access log only
        assert response.get_json()["error"] == "You don't have permission for this. Ask your engineer or IT."
        assert (g.access_outcome, g.access_detail) == ("denied_perm", "settings:edit")

    def test_blocks_anonymous(self, ctx):
        _, status = _guarded()
        assert status == 403


class TestDevStub:
    """S011 § 5.8: DEV_STUB_ROLE set to a site role gives that role at every site."""

    @pytest.mark.parametrize("role, roles, memberships", [
        ("maint_engineer", ["maintenance_team"], [Membership(None, "maint_engineer", True)]),
        ("it_admin", ["it_admin"], None),
        ("maintenance_team", ["maintenance_team"], None),
        ("admin", ["admin"], None),
        ("nobody", [], []),
    ])
    def test_stub_user(self, monkeypatch, role, roles, memberships):
        import auth_utils
        import config
        monkeypatch.setattr(config, "DEV_STUB_ROLE", role)
        monkeypatch.setattr(auth_utils, "_DEV_STUB_USER", None)
        user = auth_utils._get_dev_stub_user()
        assert (user["roles"], user["memberships"]) == (roles, memberships)
