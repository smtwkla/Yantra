"""tooling/steps/brief_facts.py: the pure parsing only (no git, no files)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "steps"))

import brief_facts  # noqa: E402
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
