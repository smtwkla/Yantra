"""The access log: sightings, outcomes, the DB-down back-off and the viewer (S013 § 5.4, § 8 API)."""

import pytest

import access_control
import config
import db_helpers
import network_core
from local_db import get_local_db

LOG = "/api/settings/access-log"
SITES = "/api/masters/sites"


def _rows(db_rows, **where):
    clauses = " AND ".join(f"{k} = %s" for k in where)
    return list(db_rows(f"SELECT * FROM access_log WHERE {clauses} ORDER BY id", tuple(where.values())))


@pytest.fixture
def ip(uniq):
    """A fresh external address per call, so rows can be told apart."""
    def fresh():
        n = int(uniq.username()[4:])   # the session-wide counter
        return f"198.51.{n // 250 % 250}.{n % 250 + 1}"
    return fresh


class TestSightings:

    def test_one_row_per_sighting(self, role_client, uniq, db_rows):
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        assert engineer.get(SITES).status_code == 200
        assert engineer.get(SITES).status_code == 200
        assert engineer.get("/api/equipment").status_code == 200
        rows = _rows(db_rows, username=login)
        assert len(rows) == 1
        row = rows[0]
        assert row["outcome"] == "ok" and row["client_ip"] == "10.0.0.5" and row["is_internal"] == 1
        assert row["method"] == "GET" and row["path"] == SITES and row["role"] == "maint_engineer"
        assert row["session_id"] is None and row["detail"] is None

    def test_a_new_address_is_a_new_row(self, role_client, uniq, db_rows):
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        engineer.get(SITES)
        engineer.get(SITES, headers={"X-Real-IP": "203.0.113.50"})
        engineer.get(SITES, headers={"X-Real-IP": "203.0.113.50"})
        rows = _rows(db_rows, username=login)
        assert [(r["client_ip"], r["is_internal"]) for r in rows] == [("10.0.0.5", 1), ("203.0.113.50", 0)]

    def test_one_row_per_day_across_workers(self, role_client, uniq, db_rows):
        """S013 A1: a second worker has its own empty cache; the unique key keeps one row."""
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        engineer.get(SITES)
        access_control.reset_access_log_state()   # as a second Gunicorn worker would see it
        engineer.get("/api/equipment")
        rows = _rows(db_rows, username=login)
        assert len(rows) == 1 and rows[0]["path"] == SITES
        assert rows[0]["sighting_day"] == rows[0]["ts"].date()
        assert rows[0]["sighting_hash"] == network_core.sighting_hash("ok", login, "10.0.0.5", None)

    @pytest.mark.parametrize("second", [
        {"headers": {"X-Real-IP": "203.0.113.51"}},   # another address
        {"path": LOG},                                # another outcome (denied_perm) and detail
    ])
    def test_another_key_is_another_row(self, role_client, uniq, db_rows, second):
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        engineer.get(SITES)
        access_control.reset_access_log_state()
        engineer.get(second.get("path", SITES), headers=second.get("headers", {}))
        assert len(_rows(db_rows, username=login)) == 2

    def test_another_detail_is_another_row(self, client, ip, db_rows):
        address = ip()
        client.get(SITES, headers={"X-Real-IP": address})
        access_control.reset_access_log_state()
        client.get(SITES, headers={"X-Real-IP": address, "Authorization": "Bearer not-a-jwt"})
        assert [r["detail"] for r in _rows(db_rows, client_ip=address)] == ["no_token", "invalid_token"]

    def test_a_rejected_insert_is_remembered(self, role_client, uniq, db_rows, monkeypatch):
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        engineer.get(SITES)
        access_control.reset_access_log_state()
        results = []
        real_insert = access_control._insert

        def counting(row):
            results.append(real_insert(row))
            return results[-1]

        monkeypatch.setattr(access_control, "_insert", counting)
        engineer.get(SITES)   # cache miss: the insert runs and is ignored
        engineer.get(SITES)   # remembered: no third attempt
        assert results == [0]
        assert len(_rows(db_rows, username=login)) == 1

    def test_user_agent_is_kept(self, role_client, uniq, db_rows):
        login = uniq.username()
        role_client("maint_engineer", login).get(SITES, headers={"User-Agent": "Phone/1.0"})
        assert _rows(db_rows, username=login)[0]["user_agent"] == "Phone/1.0"

    def test_public_paths_are_not_logged(self, client, ip, db_rows):
        address = ip()
        client.get("/api/health", headers={"X-Real-IP": address})
        client.get("/api/version", headers={"X-Real-IP": address})
        assert _rows(db_rows, client_ip=address) == []


class TestOutcomes:

    def test_denied_network(self, role_client, uniq, db_rows):
        login = uniq.username()
        role_client("it_admin", login).get(SITES, headers={"X-Real-IP": "203.0.113.9"})
        row = _rows(db_rows, username=login)[0]
        assert row["outcome"] == "denied_network" and row["is_internal"] == 0 and row["role"] == "it_admin"

    def test_denied_perm_from_require_perm(self, role_client, uniq, db_rows):
        login = uniq.username()
        assert role_client("maint_engineer", login).get(LOG).status_code == 403
        row = [r for r in _rows(db_rows, username=login) if r["outcome"] == "denied_perm"][0]
        assert row["detail"] == "access_log:view" and row["path"] == LOG

    def test_denied_perm_from_require_perm_at(self, user_at_sites, make_site, make_unit, make_equipment, db_rows):
        site_a, site_b = make_site(), make_site()
        unit_b = make_unit(site=site_b)
        node = make_equipment(unit=unit_b)
        client, person = user_at_sites([(site_a, "maint_engineer", "all"), (site_b, "maint_operator", "all")])
        res = client.put(f"/api/equipment/{node['id']}", json={"name": "Renamed"})
        assert res.status_code == 403
        rows = _rows(db_rows, username=person["username"], outcome="denied_perm")
        assert rows[0]["detail"] == f"equipment:edit@site:{site_b['id']}"

    def test_business_403_keeps_its_message(self, role_client, uniq, db_rows):
        login = uniq.username()
        res = role_client("maint_engineer", login).post(
            "/api/masters/people", json={"name": "X", "employment": "direct", "trade_ids": [], "username": "zz"})
        assert res.status_code == 403
        row = _rows(db_rows, username=login, outcome="denied_perm")[0]
        assert row["detail"] == "Only IT admin can set the login"

    def test_auth_failed_has_no_username_and_a_fixed_code(self, client, ip, db_rows):
        address = ip()
        client.get(SITES, headers={"X-Real-IP": address})
        client.get(SITES, headers={"X-Real-IP": address, "Authorization": "Bearer not-a-jwt"})
        client.get(SITES, headers={"X-Real-IP": address, "Authorization": "Bearer other-garbage"})
        rows = _rows(db_rows, client_ip=address)
        assert [(r["outcome"], r["detail"], r["username"]) for r in rows] == [
            ("auth_failed", "no_token", None), ("auth_failed", "invalid_token", None)]

    def test_a_long_path_is_truncated(self, client, ip, db_rows):
        address = ip()
        client.get("/api/" + "x" * 400, headers={"X-Real-IP": address})
        row = _rows(db_rows, client_ip=address)[0]
        assert len(row["path"]) == 255 and row["outcome"] == "auth_failed"

    def test_a_validation_error_is_ok(self, role_client, uniq, db_rows):
        login = uniq.username()
        assert role_client("it_admin", login).post(f"{SITES}", json={}).status_code == 400
        assert _rows(db_rows, username=login)[0]["outcome"] == "ok"

    def test_an_unknown_outcome_is_logged_not_written(self, role_client, uniq, db_rows, monkeypatch, caplog):
        """S013 CR4-01: INSERT IGNORE would store '' for a value missing from the ENUM."""
        login = uniq.username()
        monkeypatch.setattr(access_control, "classify_outcome", lambda *_args: ("brand_new", None))
        with caplog.at_level("ERROR", logger=access_control.logger.name):
            assert role_client("maint_engineer", login).get(SITES).status_code == 200
        assert _rows(db_rows, username=login) == []
        assert "brand_new" in caplog.text

    def test_a_missing_address_is_warned_once(self, role_client, uniq, db_rows, caplog):
        """S013 CR4-02: the warning comes with the written row, not with the deduped repeat."""
        login = uniq.username()
        engineer = role_client("maint_engineer", login)
        with caplog.at_level("WARNING", logger=access_control.logger.name):
            engineer.get(SITES, headers={"X-Real-IP": ""})
            assert caplog.text.count("missing or not an address") == 1
            engineer.get(SITES, headers={"X-Real-IP": ""})
        assert caplog.text.count("missing or not an address") == 1
        assert len(_rows(db_rows, username=login)) == 1


class TestDatabaseDown:
    """S013 BR1-01, BR2-01, BR2-03."""

    def test_skipped_while_down_and_written_once_back(self, role_client, uniq, db_rows, monkeypatch):
        login = uniq.username()
        monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "down")
        monkeypatch.setattr(access_control, "ensure_schema", lambda _config: "down")
        assert role_client("it_admin", login).get("/api/auth/me").status_code == 200
        assert _rows(db_rows, username=login) == []
        monkeypatch.undo()
        role_client("it_admin", login).get("/api/auth/me")
        assert len(_rows(db_rows, username=login)) == 1   # not cached while down

    def test_a_failed_write_backs_off(self, role_client, uniq, db_rows, monkeypatch):
        login = uniq.username()
        calls = []

        def broken():
            calls.append(1)
            raise access_control.pymysql.err.OperationalError(2003, "Can't connect (test)")

        monkeypatch.setattr(access_control, "get_pooled_db", broken)
        engineer = role_client("maint_engineer", login)
        assert engineer.get(SITES).status_code == 200
        assert engineer.get(SITES, headers={"X-Real-IP": "203.0.113.77"}).status_code == 200
        assert len(calls) == 1   # the second sighting fell in the back-off: no connect attempt
        monkeypatch.undo()
        monkeypatch.setattr(access_control, "_log_backoff_until", 0.0)   # 30 s later
        engineer.get(SITES)
        assert len(_rows(db_rows, username=login)) == 1


def _insert_rows(rows):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            for ts, username, is_internal, outcome in rows:
                cur.execute("INSERT INTO access_log (ts, username, client_ip, is_internal, outcome, method, path,"
                            " sighting_day, sighting_hash) VALUES (%s, %s, '10.9.9.9', %s, %s, 'GET', '/api/x',"
                            " DATE(%s), SHA1(UUID()))", (ts, username, is_internal, outcome, ts))
    finally:
        conn.close()


class TestViewer:

    @pytest.fixture
    def seeded(self, uniq):
        prefix = f"viewer{uniq.username()}"
        _insert_rows([
            ("2026-03-01 09:00:00", f"{prefix}_a", 1, "ok"),
            ("2026-03-02 23:59:59", f"{prefix}_a", 0, "ok"),
            ("2026-03-03 00:00:00", f"{prefix}_b", 0, "denied_network"),
            ("2026-03-04 12:00:00", f"{prefix}_b", 1, "denied_perm"),
        ])
        return prefix

    def _get(self, role_client, **params):
        res = role_client("maint_manager").get(LOG, query_string=params)
        assert res.status_code == 200, res.get_json()
        return res.get_json()

    def test_newest_first(self, role_client, seeded):
        body = self._get(role_client, user=seeded)
        assert body["total"] == 4
        assert [i["ts"] for i in body["items"]] == ["2026-03-04T12:00:00+05:30", "2026-03-03T00:00:00+05:30",
                                                    "2026-03-02T23:59:59+05:30", "2026-03-01T09:00:00+05:30"]
        assert body["items"][0]["is_internal"] is True

    def test_user_contains(self, role_client, seeded):
        assert self._get(role_client, user=f"{seeded}_b")["total"] == 2

    def test_dates_to_inclusive(self, role_client, seeded):
        assert self._get(role_client, user=seeded, **{"from": "02-03-2026", "to": "02-03-2026"})["total"] == 1
        assert self._get(role_client, user=seeded, **{"from": "2026-03-02", "to": "2026-03-03"})["total"] == 2
        assert self._get(role_client, user=seeded, to="01-03-2026")["total"] == 1

    def test_external_and_denied(self, role_client, seeded):
        assert self._get(role_client, user=seeded, external="1")["total"] == 2
        assert self._get(role_client, user=seeded, denied="1")["total"] == 2
        assert self._get(role_client, user=seeded, external="1", denied="1")["total"] == 1
        assert self._get(role_client, user=seeded, external="0", denied="0")["total"] == 4

    def test_paging(self, role_client, seeded):
        body = self._get(role_client, user=seeded, page="2", per_page="3")
        assert body["page"] == 2 and body["per_page"] == 3 and body["total"] == 4
        assert [i["ts"] for i in body["items"]] == ["2026-03-01T09:00:00+05:30"]

    @pytest.mark.parametrize("params", [{"from": "31-02-2026"}, {"to": "2026/03/01"}, {"external": "yes"},
                                        {"page": "0"}, {"per_page": "1000"}])
    def test_bad_arguments_are_400(self, role_client, params):
        assert role_client("maint_manager").get(LOG, query_string=params).status_code == 400

    @pytest.mark.parametrize("role, status", [("it_admin", 200), ("maint_manager", 200), ("admin", 200),
                                              ("maint_engineer", 403), ("maint_operator", 403)])
    def test_who_may_read(self, role_client, role, status):
        assert role_client(role).get(LOG).status_code == status

    def test_the_log_has_no_write_routes(self, app):
        methods = {m for rule in app.url_map.iter_rules() if rule.rule.startswith(LOG) for m in rule.methods}
        assert methods <= {"GET", "HEAD", "OPTIONS"}
