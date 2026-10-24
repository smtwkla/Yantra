"""v31, equipment properties (S043 § 4, § 8.3), in the upgrade database UPGRADE_DB that the
v20-v30 migration tests also use (one per test run and worker, tests/db_names.py).  A fresh
database gets the four tables, their CHECKs and the 22-row seed with its options; a v30 database
with a class, a model, equipment and a model meter keeps every row; a re-run changes nothing and
keeps an engineer's edit of a seed row.  Needs the dev MariaDB container.

A new file: test_migration_v26.py is S031's (the branch's S035 used v26; BS1-08).
"""

import pymysql
import pytest

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V30 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 31)]
V31 = [m for m in local_db._MIGRATIONS if m[0] in range(20, 32)]
VERSIONS = list(range(20, 32))

SEED = "migration-v31"
NEW_TABLES = ("property_definitions", "property_options", "class_properties", "model_property_values")
SEED_OPTIONS = {
    "Shaft sealing": ["Mechanical seal", "Packed gland", "Lip seal", "Seal-less"],
    "Shaft orientation": ["Horizontal", "Vertical"],
    "Coupling": ["Rigid", "Flexible", "Magnetic", "Direct"],
    "Insulation class": ["A", "B", "E", "F", "H"],
    "Actuation": ["Manual", "Solenoid", "Pneumatic", "Hydraulic", "Electric motor"],
}
ER_CONSTRAINT_FAILED = 4025
ER_NO_REFERENCED_ROW = 1452


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _seed():
    """The seed as (name, data_type, unit, description) by name, and the options per property in id order."""
    properties = [tuple(r.values()) for r in _run(
        "SELECT name, data_type, unit, description FROM property_definitions WHERE created_by = %s ORDER BY name",
        (SEED,))]
    options = {}
    for row in _run("SELECT p.name, o.label FROM property_options o JOIN property_definitions p"
                    " ON p.id = o.property_id WHERE o.created_by = %s ORDER BY o.id", (SEED,)):
        options.setdefault(row["name"], []).append(row["label"])
    return properties, options


OLD_TABLES = ("sites", "units", "equipment_classes", "manufacturers", "equipment_models", "equipment", "tickets",
              "meter_types", "model_meters")


def _old_rows():
    return {table: _run(f"SELECT * FROM {table}") for table in OLD_TABLES}


def test_a_fresh_database_gets_v31_with_the_seed():
    _recreate()
    _migrate(V31)
    assert _versions() == VERSIONS
    tables = {r["TABLE_NAME"] for r in _run("SELECT TABLE_NAME FROM information_schema.TABLES"
                                            " WHERE TABLE_SCHEMA = DATABASE()")}
    assert set(NEW_TABLES) <= tables
    checks = {r["CONSTRAINT_NAME"] for r in _run("SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS"
                                                 " WHERE CONSTRAINT_SCHEMA = DATABASE()")}
    assert {"chk_property_unit", "chk_model_property_one_value"} <= checks

    properties, options = _seed()
    assert len(properties) == 22
    by_name = {p[0]: p for p in properties}
    assert by_name["Power – design"] == ("Power – design", "number", "kW",
                                         "The maker's rating, from the nameplate or the data sheet.")
    assert by_name["Number of stages"] == ("Number of stages", "number", None, "From the data sheet.")
    assert by_name["Degree of protection"][1:] == ("text", None, "The IP code on the nameplate, for example IP55.")
    assert by_name["Mounting"][3] == "The IM or B/V code, for example B3."
    # Every description is a sentence (CR1-04)
    assert all(p[3].endswith(".") for p in properties if p[3] is not None)
    assert by_name["Variable speed drive"][1:] == ("yes_no", None, None)
    assert by_name["Free air delivery"][2] == "m³/min"
    # No equipment type became a property, and the request's examples are left to the users
    for name in ("Pump type", "Motor type", "Execution", "Displacement", "Drain", "Poppet type",
                 "Maximum operating pressure"):
        assert name not in by_name
    assert options == SEED_OPTIONS
    assert _run("SELECT COUNT(*) AS n FROM class_properties")[0]["n"] == 0


def test_the_database_keeps_the_value_rules():
    """The CHECKs and the option's composite FK hold even past the backend."""
    _recreate()
    _migrate(V31)
    _fill_one_ticket()
    with pytest.raises(pymysql.err.OperationalError) as refused:
        _run("UPDATE property_definitions SET unit = 'kW' WHERE name = 'Frame size'")
    assert refused.value.args[0] == ER_CONSTRAINT_FAILED

    model = _run("SELECT id FROM equipment_models")[0]["id"]
    power = _run("SELECT id FROM property_definitions WHERE name = 'Power – design'")[0]["id"]
    insert = ("INSERT INTO model_property_values (model_id, property_id, value_number, value_text, option_id)"
              " VALUES (%s, %s, %s, %s, %s)")
    for number, text in ((None, None), ("7.5", "x")):
        with pytest.raises(pymysql.err.OperationalError) as refused:
            _run(insert, (model, power, number, text, None))
        assert refused.value.args[0] == ER_CONSTRAINT_FAILED
    # An option of another property is refused by the composite FK
    vertical = _run("SELECT id FROM property_options WHERE label = 'Vertical'")[0]["id"]
    with pytest.raises(pymysql.err.IntegrityError) as refused:
        _run(insert, (model, power, None, None, vertical))
    assert refused.value.args[0] == ER_NO_REFERENCED_ROW
    _run(insert, (model, power, "7.5", None, None))
    assert str(_run("SELECT value_number FROM model_property_values")[0]["value_number"]) == "7.5000"


def test_a_v30_database_with_equipment_keeps_every_row():
    _recreate()
    _migrate(V30)
    _fill_one_ticket()
    _run("INSERT INTO model_meters (model_id, meter_type_id, min_value, max_value, created_by)"
         " SELECT m.id, t.id, 10, 60, 'kla' FROM equipment_models m, meter_types t WHERE t.name = 'Oil temperature'")
    before, schema_before = _old_rows(), _schema()
    _migrate(V31)
    assert _versions() == VERSIONS
    assert _old_rows() == before
    # No existing table changed: the old tables' columns are as they were
    assert [c for c in _schema()["columns"] if c[0] not in NEW_TABLES] == schema_before["columns"]
    assert len(_seed()[0]) == 22


def test_a_rerun_changes_nothing_and_keeps_an_edited_seed_row():
    _recreate()
    _migrate(V31)
    schema, seed = _schema(), _seed()

    _run("DELETE FROM db_version WHERE version = 31")
    _migrate(V31)
    assert (_schema(), _seed()) == (schema, seed)

    # A renamed seed row stays renamed; INSERT IGNORE keys on the name, so the old name comes
    # back as a new row on a hand re-run (§ 9.4)
    _run("UPDATE property_definitions SET name = 'Rated power' WHERE name = 'Power – design'")
    _run("UPDATE property_definitions SET description = 'Edited' WHERE name = 'Speed'")
    _run("DELETE FROM db_version WHERE version = 31")
    _migrate(V31)
    names = [r["name"] for r in _run("SELECT name FROM property_definitions ORDER BY id")]
    assert "Rated power" in names and names[-1] == "Power – design" and len(names) == 23
    assert _run("SELECT description FROM property_definitions WHERE name = 'Speed'")[0]["description"] == "Edited"
    assert _seed()[1] == SEED_OPTIONS
