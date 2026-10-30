"""The schema docs' pure core (S078 § 8.1): normalising, the JSON and script texts, the four
checks and the outcome.  Rows are small dicts in the information_schema column names."""
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "schema"))

import schema_docs_core as core  # noqa: E402


def col(table, name, pos, ctype="int(11)", nullable="NO", default=None, extra=""):
    return {"TABLE_NAME": table, "COLUMN_NAME": name, "ORDINAL_POSITION": pos, "COLUMN_TYPE": ctype,
            "IS_NULLABLE": nullable, "COLUMN_DEFAULT": default, "EXTRA": extra}


def stat(table, index, seq, column, non_unique=0, sub_part=None):
    return {"TABLE_NAME": table, "INDEX_NAME": index, "NON_UNIQUE": non_unique, "SEQ_IN_INDEX": seq,
            "COLUMN_NAME": column, "SUB_PART": sub_part}


def fk(table, name, pos, column, ref_table, ref_column):
    return {"CONSTRAINT_NAME": name, "TABLE_NAME": table, "COLUMN_NAME": column, "ORDINAL_POSITION": pos,
            "REFERENCED_TABLE_NAME": ref_table, "REFERENCED_COLUMN_NAME": ref_column,
            "DELETE_RULE": "RESTRICT", "UPDATE_RULE": "RESTRICT"}


def check(table, name, clause, level="Table"):
    return {"TABLE_NAME": table, "CONSTRAINT_NAME": name, "LEVEL": level, "CHECK_CLAUSE": clause}


def catalogue():
    """people, improvements (a unique self FK), links (a two-column unique key with an FK),
    values (a two-column FK, one column nullable)."""
    return {
        "tables": [{"TABLE_NAME": t} for t in ("people", "improvements", "links", "options", "values")],
        "columns": [
            col("people", "id", 1, extra="auto_increment"),
            col("people", "name", 2, "varchar(100)"),
            col("people", "username", 3, "varchar(100)", "YES", "NULL"),
            col("people", "active", 4, "tinyint(1)", default="1"),
            col("improvements", "id", 1, extra="auto_increment"),
            col("improvements", "follow_up_of_id", 2, nullable="YES", default="NULL"),
            col("improvements", "lead_id", 3),
            col("links", "improvement_id", 1),
            col("links", "ticket_id", 2),
            col("links", "open_link", 3, "tinyint(1)", "YES", "1"),
            col("options", "id", 1),
            col("options", "property_id", 2),
            col("values", "model_id", 1),
            col("values", "property_id", 2),
            col("values", "option_id", 3, nullable="YES", default="NULL"),
        ],
        "statistics": [
            stat("people", "PRIMARY", 1, "id"),
            stat("people", "uq_people_username", 1, "username"),
            stat("improvements", "PRIMARY", 1, "id"),
            stat("improvements", "uq_improvements_follow_up", 1, "follow_up_of_id"),
            stat("improvements", "fk_improvements_lead", 1, "lead_id", non_unique=1),
            stat("links", "PRIMARY", 1, "improvement_id"),
            stat("links", "PRIMARY", 2, "ticket_id"),
            stat("links", "uq_links_open", 1, "ticket_id"),
            stat("links", "uq_links_open", 2, "open_link"),
            stat("options", "PRIMARY", 1, "id"),
            stat("options", "uq_options_id_property", 1, "id"),
            stat("options", "uq_options_id_property", 2, "property_id"),
            stat("values", "PRIMARY", 1, "model_id"),
            stat("values", "PRIMARY", 2, "property_id"),
            stat("values", "ix_values_name", 1, "option_id", non_unique=1, sub_part=10),
        ],
        "foreign_keys": [
            fk("improvements", "fk_improvements_follow_up", 1, "follow_up_of_id", "improvements", "id"),
            fk("improvements", "fk_improvements_lead", 1, "lead_id", "people", "id"),
            fk("links", "fk_links_improvement", 1, "improvement_id", "improvements", "id"),
            fk("values", "fk_values_option", 2, "property_id", "options", "property_id"),
            fk("values", "fk_values_option", 1, "option_id", "options", "id"),
        ],
        "checks": [
            check("improvements", "chk_improvements_b", "`lead_id` > 0"),
            check("improvements", "chk_improvements_a", "`lead_id` between −90 and 90"),
            check("values", "option_id", "json_valid(`option_id`)", level="Column"),
        ],
    }


def notes():
    return {
        "overview_note": "Every table.",
        "areas": [{"name": "Team", "note": "People."}, {"name": "Work", "note": "Improvements."}],
        "tables": {"people": {"area": "Team", "holds": "A person"},
                   "improvements": {"area": "Work", "holds": "An improvement"},
                   "links": {"area": "Work", "holds": "Links"},
                   "options": {"area": "Work", "holds": "Options"},
                   "values": {"area": "Work", "holds": "Values"}},
        "planned_note": "Not built yet.",
        "planned": [{"tables": ["pm_plans", "pm_jobs"], "holds": "PM"}],
    }


def built(rows=None, migration=41):
    return core.build_schema(rows or catalogue(), migration)


def column(schema, table, name):
    return next(c for c in schema["tables"][table]["columns"] if c["name"] == name)


# 1 ---------------------------------------------------------------------------

@pytest.mark.parametrize("given, expected", [
    ("int(11)", "int"), ("tinyint(1)", "tinyint"), ("bigint(20) unsigned", "bigint unsigned"),
    ("smallint(6)", "smallint"), ("mediumint(9)", "mediumint"), ("INT(11)", "int"),
    ("varchar(100)", "varchar(100)"), ("decimal(14,3)", "decimal(14,3)"), ("enum('a','b')", "enum('a','b')"),
    ("VARCHAR(20)", "varchar(20)"), ("datetime", "datetime"),
])
def test_type_normalisation(given, expected):
    assert core.normalise_type(given) == expected


# 2 ---------------------------------------------------------------------------

@pytest.mark.parametrize("given, expected", [
    (None, None), ("NULL", None), ("'manual'", "'manual'"), ("1", "1"),
    ("current_timestamp()", "current_timestamp()"),
])
def test_default_normalisation(given, expected):
    assert core.normalise_default(given) == expected


# 3 ---------------------------------------------------------------------------

def test_key_tags():
    schema = built()
    assert column(schema, "links", "improvement_id")["key"] == "PK,FK"
    assert column(schema, "improvements", "follow_up_of_id")["key"] == "FK,UK"
    assert column(schema, "links", "open_link")["key"] == ""   # in a two-column unique key only
    assert column(schema, "people", "username")["key"] == "UK"
    assert column(schema, "people", "name")["key"] == ""
    assert column(schema, "people", "id")["key"] == "PK"


# 4 ---------------------------------------------------------------------------

def test_foreign_key_required_and_column_order():
    tables = built()["tables"]
    lead = next(f for f in tables["improvements"]["foreign_keys"] if f["name"] == "fk_improvements_lead")
    assert lead["required"] is True
    option = tables["values"]["foreign_keys"][0]
    assert option == {"name": "fk_values_option", "columns": ["option_id", "property_id"], "references": "options",
                      "ref_columns": ["id", "property_id"], "required": False, "on_delete": "RESTRICT",
                      "on_update": "RESTRICT"}


def test_column_fields_and_prefix_index():
    schema = built()
    assert schema["tables"]["people"]["columns"][0] == {
        "name": "id", "type": "int", "null": False, "default": None, "key": "PK", "extra": "auto_increment"}
    assert schema["tables"]["values"]["indexes"] == [{"name": "ix_values_name", "unique": False,
                                                      "columns": ["option_id(10)"]}]
    assert schema["tables"]["links"]["primary_key"] == ["improvement_id", "ticket_id"]
    assert schema["tables"]["values"]["checks"] == [
        {"name": "option_id", "level": "column", "clause": "json_valid(`option_id`)"}]


# 5 ---------------------------------------------------------------------------

def test_ordering_and_shuffled_rows_give_the_same_text():
    schema = built()
    assert list(schema["tables"]) == ["improvements", "links", "options", "people", "values"]
    assert [c["name"] for c in schema["tables"]["improvements"]["checks"]] == ["chk_improvements_a", "chk_improvements_b"]
    assert [f["name"] for f in schema["tables"]["improvements"]["foreign_keys"]] == [
        "fk_improvements_follow_up", "fk_improvements_lead"]
    assert [c["name"] for c in schema["tables"]["people"]["columns"]] == ["id", "name", "username", "active"]
    shuffled = catalogue()
    rng = random.Random(7)
    for rows in shuffled.values():
        rng.shuffle(rows)
    assert core.schema_json_text(built(shuffled)) == core.schema_json_text(schema)


# 6 ---------------------------------------------------------------------------

def test_json_layout():
    schema = built()
    text = core.schema_json_text(schema)
    lines = text.split("\n")
    assert text.endswith("}\n") and not text.endswith("\n\n") and "\r" not in text
    assert lines[1] == f"  \"_note\": {json.dumps(core.NOTE)},"
    assert lines[2] == "  \"migration\": 41,"
    assert "        {\"name\": \"id\", \"type\": \"int\", \"null\": false, \"default\": null, \"key\": \"PK\", " \
           "\"extra\": \"auto_increment\"}," in lines
    assert "      \"foreign_keys\": []," in lines
    assert "      \"primary_key\": [\"id\"]," in lines
    people = lines.index("    \"people\": {")
    block = lines[people + 1:lines.index("    },", people)]
    keys = [line.strip().split("\"")[1] for line in block if line.startswith("      \"")]
    assert keys == ["columns", "primary_key", "foreign_keys", "indexes", "checks"]
    assert "−90" in text   # non-ASCII kept
    assert json.loads(text) == schema


# 7 ---------------------------------------------------------------------------

def test_data_js_text():
    schema_text = core.schema_json_text(built())
    js = core.data_js_text(schema_text, notes())
    lines = js.split("\n")
    assert lines[0] == core.DATA_JS_HEADER
    assert js.startswith(core.DATA_JS_HEADER + "\nwindow.YANTRA_SCHEMA = " + schema_text.rstrip("\n") + ";\n")
    notes_part = js.split("window.YANTRA_SCHEMA_NOTES = ", 1)[1]
    assert notes_part.endswith("};\n")
    assert json.loads(notes_part[:-2]) == notes()
    assert "    \"people\": {\"area\": \"Team\", \"holds\": \"A person\"}," in lines
    assert "    {\"name\": \"Team\", \"note\": \"People.\"}," in lines
    assert "    {\"tables\": [\"pm_plans\", \"pm_jobs\"], \"holds\": \"PM\"}" in lines


# 8 ---------------------------------------------------------------------------

def test_file_check_equal_and_crlf_pass():
    text = "a\nb\nc\n"
    assert core.file_problems(core.SCHEMA_JSON, text, text) == []
    assert core.file_problems(core.SCHEMA_JSON, text.replace("\n", "\r\n"), text) == []


def test_file_check_changed_line_names_line_and_both_texts():
    [problem] = core.file_problems(core.SCHEMA_JSON, "a\nB\nc\n", "a\nb\nc\n")
    assert problem == ("docs/schema/schema.json is stale: line 2 differs (on disk: B; generated: b). "
                       r"Run tooling\schema-docs.bat write and commit the result.")


def test_file_check_cuts_long_lines_and_shorter_file():
    [problem] = core.file_problems(core.SCHEMA_DATA_JS, "x" * 200 + "\n", "y" * 200 + "\n")
    assert "on disk: " + "x" * 120 + "…;" in problem
    [problem] = core.file_problems(core.SCHEMA_DATA_JS, "a\n", "a\nb\n")
    assert "line 2 differs (on disk: (end of file); generated: b)" in problem


def test_file_check_missing():
    [problem] = core.file_problems(core.SCHEMA_JSON, None, "a\n")
    assert problem == r"docs/schema/schema.json is missing. Run tooling\schema-docs.bat write and commit the result."


# 9 ---------------------------------------------------------------------------

def test_notes_check_passes_on_matching_notes():
    assert core.notes_problems(built(), notes()) == []


def test_notes_check_built_table_without_notes():
    n = notes()
    del n["tables"]["links"]
    assert core.notes_problems(built(), n) == [
        "docs/schema/notes.json has no line for table links. Add \"links\": {\"area\": \"<one of: Team, Work>\", "
        "\"holds\": \"<what it holds>\"} under \"tables\", then run tooling\\schema-docs.bat write."]


def test_notes_check_table_not_built():
    n = notes()
    n["tables"]["user_units"] = {"area": "Team", "holds": "Legacy"}
    assert core.notes_problems(built(), n) == [
        "docs/schema/notes.json has a line for table user_units, which is not built. "
        "Remove the line, or move it to \"planned\"."]


def test_notes_check_unknown_or_missing_area():
    n = notes()
    n["tables"]["people"]["area"] = "Teams"
    del n["tables"]["links"]["area"]
    assert core.notes_problems(built(), n) == [
        "docs/schema/notes.json: table links names area (none), which is not in \"areas\".",
        "docs/schema/notes.json: table people names area \"Teams\", which is not in \"areas\"."]


def test_notes_check_two_areas_with_one_name():
    n = notes()
    n["areas"].append({"name": "Team", "note": "Again."})
    assert core.notes_problems(built(), n) == [
        "docs/schema/notes.json names area \"Team\" twice under \"areas\". Give each area its own name."]


def test_notes_check_missing_or_empty_holds():
    n = notes()
    n["tables"]["people"]["holds"] = " "
    del n["tables"]["links"]["holds"]
    assert core.notes_problems(built(), n) == [
        "docs/schema/notes.json: table links has no \"holds\" text. Write what it holds.",
        "docs/schema/notes.json: table people has no \"holds\" text. Write what it holds."]


# 10 --------------------------------------------------------------------------

def test_planned_check():
    assert core.planned_problems(built(), notes()) == []
    n = notes()
    n["planned"].append({"tables": ["links"], "holds": "x"})
    assert core.planned_problems(built(), n) == [
        "docs/schema/notes.json lists links under \"planned\", but it is built. Move it to \"tables\" with its area."]


# 11 --------------------------------------------------------------------------

def _generated_and_disk():
    schema = built()
    generated = core.files_to_write(schema, notes())
    return schema, generated, dict(generated)


def test_outcome_all_passed():
    schema, generated, disk = _generated_and_disk()
    code, lines = core.outcome(41, core.run_checks(schema, notes(), disk, generated))
    assert (code, lines) == (0, ["Schema docs at migration v41: 4 passed"])


def test_outcome_one_failed():
    schema, generated, disk = _generated_and_disk()
    disk[core.SCHEMA_DATA_JS] = None
    code, lines = core.outcome(41, core.run_checks(schema, notes(), disk, generated))
    assert code == 1
    assert lines == [r"docs/schema/schema-data.js is missing. Run tooling\schema-docs.bat write and commit the result.",
                     "Schema docs at migration v41: 3 passed, 1 failed"]


def test_outcome_not_completed():
    message = core.unreachable_message("Can't connect (error 2003)")
    assert core.outcome(41, not_completed=message) == (2, [message, "Schema docs: not completed"])
    assert message.startswith("The schema docs were not built. The dev database cannot be reached: Can't connect")


def test_notes_not_valid_json_fails_checks_3_and_4_and_writes_nothing():
    parsed, problem = core.parse_notes("{\"areas\": [,]}")
    assert parsed is None
    assert problem.startswith("docs/schema/notes.json is not valid JSON: Expecting value: line 1 column 12")
    assert problem.endswith("Fix the file, then run the command again.")
    results = core.checks_without_notes(problem)
    assert [ok for ok, _ in results] == [False, False, False, False]
    assert problem in results[2][1]
    code, lines = core.outcome(41, results)
    assert code == 1 and lines[-1] == "Schema docs at migration v41: 0 passed, 4 failed"
    assert core.files_to_write(built(), parsed) == {}


def test_notes_missing_or_not_an_object():
    assert core.parse_notes(None)[1].startswith("docs/schema/notes.json is missing.")
    assert "must hold one object" in core.parse_notes("[]")[1]


def test_guard():
    assert core.check_target("127.0.0.1", "vel_yantra_test_dev_schemadocs") is None
    assert core.check_target("localhost", "vel_yantra_test_s078c1_schemadocs") is None
    assert core.check_target("db.example.test", "vel_yantra_test_dev_schemadocs") == (
        "The schema docs were not built: refusing database host db.example.test; the schema docs database "
        "must be local (localhost, 127.0.0.1).")
    assert "must end in _schemadocs" in core.check_target("127.0.0.1", "vel_yantra_master")
