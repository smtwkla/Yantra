"""tooling/steps/brief_facts.py: the pure parsing only (no git, no files)."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))

import brief_facts  # noqa: E402
import step_facts  # noqa: E402
from brief_facts import Ref, classify, extract_refs, is_test_path, summarise_hits  # noqa: E402


class TestClassify:
    def test_a_path_with_a_line_range(self):
        assert classify("backend/alerts_core.py:41-43") == Ref("path", "backend/alerts_core.py", 41, 43)

    def test_a_path_with_one_line(self):
        assert classify("backend/api_common.py:146") == Ref("path", "backend/api_common.py", 146, 146)

    def test_a_bare_file_name(self):
        assert classify("screens.spec.js") == Ref("file", "screens.spec.js")

    def test_a_test_id(self):
        assert classify("test_equipment_api.py::TestListing::test_row_fields") == Ref(
            "test", "test_equipment_api.py::TestListing::test_row_fields")

    def test_a_route_with_its_method(self):
        assert classify("GET /api/equipment/") == Ref("route", "/api/equipment")

    def test_a_call_keeps_the_function_name(self):
        assert classify('accessible_unit_ids(cur, "ticket:read")') == Ref("name", "accessible_unit_ids")

    def test_names_worth_grepping(self):
        assert classify("DOWN_STATES") == Ref("name", "DOWN_STATES")
        assert classify("listUrl") == Ref("name", "listUrl")
        assert classify("tickets._equipment_filter") == Ref("name", "tickets._equipment_filter")

    def test_plain_words_and_text_are_skipped(self):
        for token in ("down", "critical", "tickets=down|open", "u.id IN (ticket_units)", "None", "ticket:read"):
            assert classify(token) is None, token


class TestExtractRefs:
    def test_each_reference_once_in_order(self):
        text = "Use `DOWN_STATES` in `backend/equipment.py`, then `DOWN_STATES` again and `down`."
        assert extract_refs(text) == [Ref("name", "DOWN_STATES"), Ref("path", "backend/equipment.py")]


class TestIsTestPath:
    def test_test_folders_and_names(self):
        for path in ("backend/tests/conftest.py", "frontend/e2e/support/tickets.js",
                     "frontend/tests/ticketLabels.test.js", "tooling/tests/test_deploy.py"):
            assert is_test_path(path), path

    def test_code(self):
        for path in ("backend/tickets_core.py", "frontend/src/views/EquipmentView.vue", "tooling/steps/step_facts.py"):
            assert not is_test_path(path), path


class TestSummariseHits:
    def test_not_found(self):
        assert summarise_hits("NEW_NAME", []) == ["- `NEW_NAME`: not found"]

    def test_definition_code_and_tests_apart(self):
        hits = [
            "backend/tickets_core.py:334:DOWN_STATES = (RAISED, ACKNOWLEDGED)",
            "backend/tickets_core.py:793:        if critical and state in DOWN_STATES:",
            "backend/equipment.py:90:from tickets_core import DOWN_STATES",
            "backend/tests/test_tickets_core.py:12:    DOWN_STATES,",
        ]
        lines = summarise_hits("DOWN_STATES", hits)
        assert lines[0] == "- `DOWN_STATES`: defined at backend/tickets_core.py:334"
        assert lines[1] == "  - used in 2 code file(s): backend/tickets_core.py, backend/equipment.py"
        assert lines[2] == "  - used in 1 test file(s): backend/tests/test_tickets_core.py"

    def test_a_js_object_key_is_not_a_definition(self):
        lines = summarise_hits("in_progress", ['frontend/src/utils/ticketLabels.js:35:  in_progress: "In progress",'])
        assert lines[0] == "- `in_progress`: defined at none found"

    def test_a_long_list_is_cut(self):
        hits = [f"backend/m{i}.py:1:x = some_name()" for i in range(brief_facts.MAX_LISTED + 2)]
        assert summarise_hits("some_name", hits)[1].endswith("… (+2)")


# ---------------------------------------------------------------------------------------------
# S057: the folders come from the repo's Code folders setting
# ---------------------------------------------------------------------------------------------

@pytest.fixture
def git_args(monkeypatch):
    """brief_facts.grep without git: records the argument list and finds nothing."""
    seen = []

    def fake_run(args, **_kwargs):
        seen.append(args)
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(brief_facts.subprocess, "run", fake_run)
    return seen


def test_grep_searches_the_code_folders_given(git_args):
    brief_facts.grep("x_y", ["backend", "frontend/src"])
    assert git_args[0][-3:] == ["--", "backend", "frontend/src"]


def test_grep_without_folders_searches_the_repo_except_docs(git_args):
    brief_facts.grep("x_y", None)
    assert git_args[0][-3:] == ["--", ".", ":!docs"]


def test_a_module_is_looked_up_in_each_code_folder_then_in_the_step_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(brief_facts, "ROOT", tmp_path)
    for folder in ("app", "tooling/steps"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "app" / "orders.py").write_text("", encoding="utf-8")
    (tmp_path / "tooling" / "run_logged.py").write_text("", encoding="utf-8")
    (tmp_path / "tooling" / "steps" / "step_ls.py").write_text("", encoding="utf-8")
    hits = ["app/orders.py:1:x = 1"]
    assert summarise_hits("orders", hits, ["app", "tooling"])[0] == "- `orders`: defined at a module (app/orders.py)"
    assert "a module (tooling/run_logged.py)" in summarise_hits("run_logged", hits, ["app", "tooling"])[0]
    assert "a module (tooling/steps/step_ls.py)" in summarise_hits("step_ls", hits, None)[0]
    assert "a module" not in summarise_hits("orders", hits, None)[0]       # no folders: step tools only


def test_a_test_id_is_looked_up_at_the_root_then_in_each_code_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(brief_facts, "ROOT", tmp_path)
    (tmp_path / "web" / "tests").mkdir(parents=True)
    (tmp_path / "web" / "tests" / "test_a.py").write_text("def test_it(): pass\n", encoding="utf-8")
    (tmp_path / "test_root.py").write_text("def test_r(): pass\n", encoding="utf-8")
    assert brief_facts.check_test(Ref("test", "test_a.py::test_it"), ["web"]) == ["- `test_a.py::test_it`: exists"]
    assert brief_facts.check_test(Ref("test", "test_a.py::test_it"), None) == [
        "- `test_a.py::test_it`: **no such test file**"]
    assert brief_facts.check_test(Ref("test", "test_root.py::test_r"), None) == ["- `test_root.py::test_r`: exists"]
    assert "not found: test_gone" in brief_facts.check_test(Ref("test", "test_a.py::test_gone"), ["web"])[0]


def test_the_report_needs_the_settings_section(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(step_facts, "SETTINGS_FILE", tmp_path / "CLAUDE.md")        # no such file
    with pytest.raises(SystemExit) as stopped:
        brief_facts.main(["S001"])
    assert stopped.value.code == 2
    assert "no Step workflow section" in capsys.readouterr().err
