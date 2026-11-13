"""v58, meter links on the part and the PM templates' parent tick removed (S104 A1.5, A1.9), in the upgrade database
UPGRADE_DB (one per test run and worker, tests/db_names.py), dropped and created by these tests.

- a fresh build: node_meter_links with its keys, foreign keys and CHECK (a self-link refused, a second link of one
  part and type refused); the two new history events; no meter_from_parent column; the two rewritten CHECKs still
  refuse a meter trigger without meter_every and a Measurement with a meter type;
- a database at v57 with a ticked template and item (built from the migrations up to 57; v57's text is in
  local_db._MIGRATIONS, never edited, so no frozen fixture is needed): v58 keeps the rows and drops the columns;
  db_version gains 58;
- a re-run changes nothing, and a half-applied v58 (stopped after a DROP) re-runs to the fresh shape.

Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from tests.migration_helpers import _migrate, _recreate, _run, _schema, _versions
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys

V57 = [m for m in local_db._MIGRATIONS if m[0] <= 57]
V58 = [m for m in local_db._MIGRATIONS if m[0] <= 58]
(_, _, V58_STATEMENTS), = [m for m in local_db._MIGRATIONS if m[0] == 58]

ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062


def _insert(table, row):
    _run(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))
    return _run(f"SELECT MAX(id) AS id FROM {table}")[0]["id"]


def _refused(code, table, row):
    with pytest.raises((pymysql.err.OperationalError, pymysql.err.IntegrityError)) as refused:
        _insert(table, row)
    assert refused.value.args[0] == code, refused.value


def _columns(table):
    return {r["COLUMN_NAME"] for r in _run("SELECT COLUMN_NAME FROM information_schema.COLUMNS"
                                           " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def _enum(table, column):
    column_type = _run("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                       " AND TABLE_NAME = %s AND COLUMN_NAME = %s", (table, column))[0]["COLUMN_TYPE"]
    return tuple(value.strip("'") for value in column_type.removeprefix("enum(").removesuffix(")").split(","))


def _nodes():
    """Two equipment rows: the ticket's machine (HP001) and a part under it."""
    machine = _run("SELECT id, unit_id, class_id, model_id FROM equipment WHERE code = 'HP001'")[0]
    part = _insert("equipment", {"code": "HP001-P1", "level": "component", "parent_id": machine["id"],
                                 "class_id": machine["class_id"], "model_id": machine["model_id"], "name": "Motor",
                                 "created_by": "kla"})
    return machine["id"], part


def _meter_type():
    return _run("SELECT id FROM meter_types ORDER BY id LIMIT 1")[0]["id"]


@pytest.fixture(scope="module")
def fresh():
    _recreate()
    _migrate(V58)
    _fill_one_ticket()
    return _schema()


def test_the_links_table_keys_and_foreign_keys(fresh):
    keys = {k["INDEX_NAME"]: k["cols"] for k in _keys("node_meter_links")}
    assert keys["uq_node_meter_links"] == "equipment_id,meter_type_id"
    assert keys["ix_node_meter_links_source"] == "source_equipment_id,meter_type_id"
    assert [(f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("node_meter_links")] == [
        ("fk_node_meter_links_equipment", "equipment"), ("fk_node_meter_links_meter_type", "meter_types"),
        ("fk_node_meter_links_source", "equipment")]
    assert _columns("node_meter_links") == {"id", "equipment_id", "meter_type_id", "source_equipment_id",
                                            "created_at", "created_by"}


def test_a_self_link_and_a_second_link_of_one_type_are_refused(fresh):
    machine, part = _nodes()
    meter_type = _meter_type()
    _refused(ER_CONSTRAINT_FAILED, "node_meter_links", {"equipment_id": part, "meter_type_id": meter_type,
                                                        "source_equipment_id": part, "created_by": "kla"})
    _insert("node_meter_links", {"equipment_id": part, "meter_type_id": meter_type, "source_equipment_id": machine,
                                 "created_by": "kla"})
    _refused(ER_DUP_ENTRY, "node_meter_links", {"equipment_id": part, "meter_type_id": meter_type,
                                                "source_equipment_id": machine, "created_by": "kla"})


def test_the_history_events(fresh):
    assert _enum("equipment_events", "event")[-2:] == ("meter_linked", "meter_unlinked")
    assert "contract_removed" in _enum("equipment_events", "event")


def test_no_parent_tick_and_the_checks_still_hold(fresh):
    assert "meter_from_parent" not in _columns("pm_templates")
    assert "meter_from_parent" not in _columns("pm_template_items")
    template = {"name": "Meter check", "trigger_kind": "meter", "meter_type_id": _meter_type(), "created_by": "kla"}
    _refused(ER_CONSTRAINT_FAILED, "pm_templates", template)                       # no meter_every
    template_id = _insert("pm_templates", {**template, "meter_every": 250})
    item = {"template_id": template_id, "position": 1, "item_type": "reading", "text": "Oil", "created_by": "kla"}
    _refused(ER_CONSTRAINT_FAILED, "pm_template_items",
             {**item, "reading_kind": "measurement", "meter_type_id": _meter_type()})
    _insert("pm_template_items", {**item, "reading_kind": "meter", "meter_type_id": _meter_type()})


def test_a_v57_database_with_ticked_rows_migrates(fresh):
    _recreate()
    _migrate(V57)
    _fill_one_ticket()
    meter_type = _meter_type()
    template_id = _insert("pm_templates", {"name": "Ticked", "trigger_kind": "meter", "meter_type_id": meter_type,
                                           "meter_every": 250, "meter_from_parent": 1, "created_by": "kla"})
    _insert("pm_template_items", {"template_id": template_id, "position": 1, "item_type": "reading", "text": "Oil",
                                  "reading_kind": "meter", "meter_type_id": meter_type, "meter_from_parent": 1,
                                  "created_by": "kla"})
    assert _versions()[-1] == 57
    _migrate(V58)
    assert _versions()[-2:] == [57, 58]
    (template,) = _run("SELECT * FROM pm_templates")
    assert (template["id"], template["name"], template["meter_type_id"]) == (template_id, "Ticked", meter_type)
    assert "meter_from_parent" not in template
    (item,) = _run("SELECT * FROM pm_template_items")
    assert (item["template_id"], item["reading_kind"]) == (template_id, "meter") and "meter_from_parent" not in item
    _run("DELETE FROM pm_template_items")
    _run("DELETE FROM pm_templates")
    assert _schema() == fresh


def test_mariadb_refuses_to_drop_the_column_a_check_names(fresh):
    """A1.10 item 6: why v58 drops each CHECK before its column.  On a v57 database a DROP COLUMN of
    meter_from_parent while chk_pm_templates_meter names it is refused; v58's order (CHECK, column, CHECK) works."""
    _recreate()
    _migrate(V57)
    with pytest.raises(pymysql.err.OperationalError):
        _run("ALTER TABLE pm_templates DROP COLUMN meter_from_parent")
    assert "meter_from_parent" in _columns("pm_templates")


def test_a_re_run_and_a_half_applied_v58(fresh):
    _recreate()
    _migrate(V58)
    _fill_one_ticket()
    for statement in V58_STATEMENTS:            # every statement is safe to run twice
        _run(statement)
    assert _schema() == fresh
    _recreate()
    _migrate(V57)
    _fill_one_ticket()
    for statement in V58_STATEMENTS[:4]:        # stopped after pm_templates' DROP COLUMN, before its ADD
        _run(statement)
    _migrate(V58)
    assert _versions()[-1] == 58
    assert _schema() == fresh
