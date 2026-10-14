"""RBAC policy and enforcement tests.

Written first, before any module tests — validates the policy file itself
and catches permission mistakes immediately.
"""

import pytest
from flask import Flask, g

from auth_utils import compute_permissions, expand_roles, has_perm, require_perm
from config_rbac import PERMISSIONS, ROLE_INCLUDES, ROLES


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

    def test_role_includes_targets_are_known(self):
        for parent, children in ROLE_INCLUDES.items():
            assert parent in ROLES, f"ROLE_INCLUDES key '{parent}' not in ROLES"
            for child in children:
                assert child in ROLES, f"ROLE_INCLUDES '{parent}' includes unknown role '{child}'"


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
        ("maint_operator",         {"masters:read"}),
        ("maint_technician", {"masters:read"}),
        ("maint_engineer",   {"masters:read", "equipment:edit"}),
        ("maint_manager",    {"masters:read", "equipment:edit", "settings:read"}),
        ("it_admin",         {"masters:read", "masters:edit", "masters:read_senior", "equipment:edit",
                              "settings:read", "settings:edit"}),
        ("maint_storekeeper", {"masters:read"}),
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
    return {"username": "u", "name": "U", "role": roles[0], "roles": roles,
            "permissions": compute_permissions(roles)}


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
        assert "settings:edit" in response.get_json()["error"]

    def test_blocks_anonymous(self, ctx):
        _, status = _guarded()
        assert status == 403
