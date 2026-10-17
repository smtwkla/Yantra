"""Pure access rules (S011 § 8): permissions per site, the global union, units per key."""

import pytest

import config_rbac
from access_core import (
    Membership, compute_permissions, display_role, every_unit_by_token, global_permissions, has_key_at,
    permissions_at, unit_ids_for,
)

A, B, C = 1, 2, 3
# Units: 11, 12 at A; 21, 22 at B; 31 at C (all active, as the shell passes them)
UNITS = [(11, A), (12, A), (21, B), (22, B), (31, C)]


def _m(site_id, role, all_units=False):
    return Membership(site_id, role, all_units)


class TestGlobalPermissions:

    def test_union_over_two_sites(self):
        keys = global_permissions([], [_m(A, "maint_engineer"), _m(B, "maint_manager")])
        assert set(keys) == set(compute_permissions(["maint_engineer", "maint_manager"]))

    def test_it_admin_token_adds_its_keys(self):
        keys = set(global_permissions(["it_admin"], [_m(A, "maint_operator")]))
        assert keys == set(compute_permissions(["it_admin"])) | set(compute_permissions(["maint_operator"]))

    def test_nothing_without_token_role_or_membership(self):
        assert global_permissions([], []) == []

    def test_login_role_alone_grants_nothing(self):
        assert compute_permissions(["maintenance_team"]) == []
        assert global_permissions(["maintenance_team"], []) == []

    def test_admin_gets_every_key(self):
        assert set(global_permissions(["admin"], [])) == set(config_rbac.PERMISSIONS)


class TestPermissionsAt:

    def test_engineer_at_a_operator_at_b(self):
        memberships = [_m(A, "maint_engineer"), _m(B, "maint_operator")]
        assert "equipment:edit" in permissions_at([], memberships, A)
        assert "equipment:edit" not in permissions_at([], memberships, B)
        assert "equipment:read" in permissions_at([], memberships, B)

    def test_ladder_applies_per_site(self):
        keys = set(permissions_at([], [_m(A, "maint_manager")], A))
        assert {"equipment:edit", "equipment:purge_documents", "people:assign_technicians"} <= keys

    def test_unknown_site_gives_token_roles_only(self):
        memberships = [_m(A, "maint_engineer")]
        assert permissions_at([], memberships, C) == []
        assert permissions_at(["it_admin"], memberships, C) == compute_permissions(["it_admin"])

    def test_wildcard_membership_applies_at_every_site(self):
        memberships = [_m(None, "maint_engineer")]
        for site in (A, B, C):
            assert "equipment:edit" in permissions_at([], memberships, site)

    def test_site_none_matches_no_real_membership(self):
        assert permissions_at(["it_admin"], [_m(A, "maint_manager")], None) == compute_permissions(["it_admin"])

    def test_supervisor_has_the_operators_keys_and_no_edit(self):
        keys = permissions_at([], [_m(A, "maint_supervisor")], A)
        assert keys == permissions_at([], [_m(A, "maint_operator")], A)
        assert "equipment:edit" not in keys

    def test_has_key_at(self):
        memberships = [_m(A, "maint_engineer")]
        assert has_key_at("equipment:edit", [], memberships, A)
        assert not has_key_at("equipment:edit", [], memberships, B)
        assert has_key_at("equipment:edit", ["admin"], [], B)

    def test_a_global_key_at_a_site_is_a_programming_error(self):
        with pytest.raises(AssertionError):
            has_key_at("masters:edit", ["it_admin"], [], A)


class TestNonSiteRolesInTheDb:
    """BR2-06, BR3-02: a membership whose role is not a site role grants nothing at all."""

    @pytest.mark.parametrize("role", ["it_admin", "admin", "maint_enginer", "maintenance_team"])
    def test_ignored_entirely(self, role):
        memberships = [_m(A, role, True)]
        assert global_permissions([], memberships) == []
        assert permissions_at([], memberships, A) == []
        assert not {"masters:edit", "settings:edit", "masters:read"} & set(global_permissions([], memberships))
        assert unit_ids_for("equipment:read", [], memberships, UNITS, [(11, A)]) == set()
        assert display_role([], memberships) is None


class TestUnitIdsFor:

    def test_all_units_site_plus_chosen_units_elsewhere(self):
        memberships = [_m(A, "maint_engineer", True), _m(B, "maint_technician")]
        assert unit_ids_for("equipment:read", [], memberships, UNITS, [(21, B)]) == {11, 12, 21}

    def test_rows_at_a_site_without_membership_are_ignored(self):
        assert unit_ids_for("equipment:read", [], [_m(A, "maint_operator")], UNITS, [(11, A), (31, C)]) == {11}

    def test_only_the_active_units_passed_count(self):
        # The shell passes active units only; an all-units site gives exactly those
        assert unit_ids_for("equipment:read", [], [_m(A, "maint_manager", True)], [(11, A)], []) == {11}

    def test_per_key(self):
        memberships = [_m(A, "maint_manager", True), _m(B, "maint_operator", True)]
        assert unit_ids_for("equipment:purge_documents", [], memberships, UNITS, []) == {11, 12}
        assert unit_ids_for("equipment:read", [], memberships, UNITS, []) == {11, 12, 21, 22}

    def test_it_admin_token_sees_every_unit(self):
        assert unit_ids_for("equipment:read", ["it_admin"], [], UNITS, []) is None
        assert unit_ids_for("equipment:purge_documents", ["it_admin"], [], UNITS, []) is None
        assert unit_ids_for("equipment:read", ["admin"], [], UNITS, []) is None

    def test_a_wildcard_membership(self):
        assert unit_ids_for("equipment:read", [], [_m(None, "maint_manager", True)], UNITS, []) == {11, 12, 21, 22, 31}
        assert unit_ids_for("equipment:read", [], [_m(None, "maint_engineer")], UNITS, [(21, B)]) == {21}

    def test_a_future_key_it_admin_lacks_fails_closed(self, monkeypatch):
        """BR2-01: it_admin + engineer at A, a key granted to engineers only -> A's units, not None."""
        monkeypatch.setitem(config_rbac.PERMISSIONS, "test:engineers_only", ("maint_engineer",))
        monkeypatch.setattr("access_core.SITE_SCOPED", config_rbac.SITE_SCOPED | {"test:engineers_only"})
        assert not every_unit_by_token("test:engineers_only", ["it_admin"])
        result = unit_ids_for("test:engineers_only", ["it_admin"], [_m(A, "maint_engineer", True)], UNITS, [])
        assert result == {11, 12}

    def test_a_non_site_scoped_key_is_a_programming_error(self):
        with pytest.raises(AssertionError):
            unit_ids_for("masters:read", [], [], UNITS, [])


class TestDisplayRole:

    def test_most_privileged_of_token_and_site_roles(self):
        assert display_role(["maintenance_team"], [_m(A, "maint_operator"), _m(B, "maint_manager")]) == "maint_manager"
        assert display_role(["it_admin", "maintenance_team"], [_m(A, "maint_technician")]) == "it_admin"
        assert display_role(["admin"], []) == "admin"

    def test_login_only_is_none(self):
        assert display_role(["maintenance_team"], []) is None
