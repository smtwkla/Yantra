"""App settings — GET/PUT /api/settings/app and get_setting_int, against the test DB."""

import logging

import pytest

import config
from local_db import get_local_db
from settings import get_setting_int

APP = "/api/settings/app"


class TestGet:

    @pytest.mark.parametrize("role", ["maint_manager", "it_admin"])
    def test_manager_and_it_admin_read(self, role_client, role):
        res = role_client(role).get(APP)
        assert res.status_code == 200
        assert res.get_json() == {"upload_max_mb": 20}

    def test_operator_is_forbidden(self, role_client):
        assert role_client("maint_operator").get(APP).status_code == 403


class TestPut:

    def test_it_admin_changes_the_limit_and_it_is_logged(self, admin, upload_limit_mb, caplog):
        caplog.set_level(logging.INFO, logger="settings")
        res = admin.put(APP, json={"upload_max_mb": 5, "unknown_key": "ignored"})
        assert res.status_code == 200, res.get_json()
        assert res.get_json() == {"upload_max_mb": 5}
        assert admin.get(APP).get_json() == {"upload_max_mb": 5}
        assert any(r.levelname == "INFO" and "upload_max_mb changed by test_it_admin: 20 -> 5" in r.getMessage()
                   for r in caplog.records)

    def test_limits_of_the_range(self, admin, upload_limit_mb):
        assert admin.put(APP, json={"upload_max_mb": 1}).status_code == 200
        assert admin.put(APP, json={"upload_max_mb": 100}).status_code == 200

    def test_a_missing_row_is_written(self, admin, upload_limit_mb):
        upload_limit_mb(None)
        assert admin.put(APP, json={"upload_max_mb": 7}).get_json() == {"upload_max_mb": 7}

    def test_manager_is_forbidden(self, role_client):
        assert role_client("maint_manager").put(APP, json={"upload_max_mb": 5}).status_code == 403

    @pytest.mark.parametrize("value", [0, 101, "20", 20.5, True, None])
    def test_not_a_whole_number_in_range_is_400(self, admin, value):
        res = admin.put(APP, json={"upload_max_mb": value})
        assert res.status_code == 400
        assert res.get_json()["field"] == "upload_max_mb"

    def test_missing_key_and_not_an_object_are_400(self, admin):
        assert admin.put(APP, json={}).status_code == 400
        assert admin.put(APP, json=[5]).status_code == 400


class TestGetSettingInt:

    def _read(self, key):
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                return get_setting_int(cur, key, 20, 1, 100)
        finally:
            conn.close()

    def test_the_stored_value(self, upload_limit_mb):
        upload_limit_mb(" 42 ")
        assert self._read("upload_max_mb") == 42

    @pytest.mark.parametrize("stored", [None, "abc", "500", "0", "20.5", "", "٤٢"])
    def test_a_bad_value_gives_the_default_with_a_warning(self, upload_limit_mb, caplog, stored):
        upload_limit_mb(stored)
        assert self._read("upload_max_mb") == 20
        assert any(r.levelname == "WARNING" and "upload_max_mb" in r.getMessage() for r in caplog.records)
