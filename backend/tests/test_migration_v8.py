"""Migration v8 moves legacy user_units rows to people and person_units (S011 A1 rules 3, 7).

On the test DB: legacy rows are inserted, db_version 8 is removed, and init_db runs twice.
Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
"""

import config
from local_db import get_local_db, init_db


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def test_legacy_rows_move_once_and_user_units_stays(admin, make_unit, make_person, uniq):
    unit_a, unit_b = make_unit(), make_unit()
    fresh, leaver = uniq.username(), uniq.username()
    inactive = make_person(name="Left", username=leaver)
    admin.put(f"/api/masters/people/{inactive['id']}", json={"active": 0})
    for username, unit in ((fresh, unit_a), (fresh, unit_b), (leaver, unit_a)):
        _run("INSERT INTO user_units (username, unit_id, granted_at, granted_by) "
             "VALUES (%s, %s, '2026-01-02 03:04:05', 'it_old')", (username, unit["id"]))
    people_before = _run("SELECT COUNT(*) AS n FROM people")[0]["n"]
    try:
        _run("DELETE FROM db_version WHERE version = 8")
        init_db(config.DB_CONFIG)
        _run("DELETE FROM db_version WHERE version = 8")
        init_db(config.DB_CONFIG)   # every statement is safe to re-run

        created = _run("SELECT id, name, employment, username, active, created_by FROM people WHERE username = %s",
                       (fresh,))
        assert len(created) == 1
        assert created[0] | {"id": None} == {"id": None, "name": fresh, "employment": "direct", "username": fresh,
                                              "active": 1, "created_by": "migration-v8"}
        assert _run("SELECT COUNT(*) AS n FROM people")[0]["n"] == people_before + 1

        moved = _run("SELECT unit_id, granted_at, granted_by FROM person_units WHERE person_id = %s ORDER BY unit_id",
                     (created[0]["id"],))
        assert [r["unit_id"] for r in moved] == sorted([unit_a["id"], unit_b["id"]])
        assert all(r["granted_by"] == "it_old" and str(r["granted_at"]) == "2026-01-02 03:04:05" for r in moved)

        # A username held by an inactive person attaches to that person, which stays inactive
        attached = _run("SELECT unit_id FROM person_units WHERE person_id = %s", (inactive["id"],))
        assert [r["unit_id"] for r in attached] == [unit_a["id"]]
        assert _run("SELECT active FROM people WHERE id = %s", (inactive["id"],))[0]["active"] == 0

        # No membership: the moved rows grant nothing until IT admin adds a role
        assert _run("SELECT COUNT(*) AS n FROM memberships WHERE person_id = %s", (created[0]["id"],))[0]["n"] == 0
        # Additive: user_units is kept for a rollback to the previous release
        assert _run("SELECT COUNT(*) AS n FROM user_units WHERE username IN (%s, %s)", (fresh, leaver))[0]["n"] == 3
        assert _run("SELECT version FROM db_version WHERE version = 8")
    finally:
        _run("DELETE FROM user_units WHERE username IN (%s, %s)", (fresh, leaver))
