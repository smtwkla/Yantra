"""tooling/steps/step_stats.py: the parsing behind /step stats.  No transcripts and no step
files: the pure functions only."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))

import step_facts  # noqa: E402
import step_stats  # noqa: E402

# Yantra's five Browser-test entries, as step_facts.read_step_settings gives them
YANTRA = {"Browser-test wrapper": "`run-e2e-tests.bat`",
          "Browser-test levels": "`basic` `normal` `targeted` `full`",
          "Browser-test spec files": "`.spec.js`",
          "Browser-test default level": "`normal` `full` `2026-10-25T05:50Z`",
          "Browser-test total line": r"`All lanes done in (\d+) s`"}
CONFIG = step_stats.e2e_config(YANTRA)

CODE_REVIEW_R2 = """# Review r2

### CR1-01 (blocker): verified fixed

### CR2-01 — major — `frontend/e2e/equipment.spec.js`

### CR2-02 — nit — wording

### CR2-03 (minor) — the label
"""


class TestReviewFindings:
    def test_only_this_rounds_findings_by_severity(self):
        assert step_stats.review_findings("4-code-review-r2.md", CODE_REVIEW_R2) == {"major": 1, "nit": 1, "minor": 1}

    def test_a_brief_review_with_the_severity_in_backticks(self):
        text = "### BR1-01 — Codes go beyond Plan.MD — `major`\n\n### BR1-02 — tests — `minor`\n"
        assert step_stats.review_findings("2-brief-review-r1.md", text) == {"major": 1, "minor": 1}

    def test_a_staleness_round(self):
        text = "### BS1-01 — `major` — A1 missing\n### BS1-02 — `nit` — path\n"
        assert step_stats.review_findings("2-brief-review-s1.md", text) == {"major": 1, "nit": 1}

    def test_unrated_and_not_a_review(self):
        assert step_stats.review_findings("4-code-review-r1.md", "### CR1-01 — something\n") == {"unrated": 1}
        assert step_stats.review_findings("3-impl-report.md", CODE_REVIEW_R2) == {}


def test_round_kind():
    assert step_stats.round_kind("2-brief-review-r2.md") == "BR"
    assert step_stats.round_kind("2-brief-review-s1.md") == "BS"
    assert step_stats.round_kind("4-code-review-r3.md") == "CR"
    assert step_stats.round_kind("1-brief.md") is None


def test_rejected_answers_in_the_review_log_only():
    brief = "Rejected ideas: none.\n\n## Review log\n| BR1-01 | minor | **Rejected**: no |\n| BR1-02 | nit | Rejected — out of scope |\n| BR1-03 | nit | **Accepted** |\n"
    assert step_stats.rejected_answers(brief) == 2
    assert step_stats.rejected_answers("no log") == 0


def test_step_of():
    assert step_stats.step_of("S021 code review r1") == "S021"
    assert step_stats.step_of("Fix round: five minor findings") is None


def test_message_usage_counts_each_message_once():
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 5}
    lines = [json.dumps({"message": {"id": "m1", "model": "claude-opus-5-5", "usage": usage}})] * 3
    lines.append(json.dumps({"message": {"id": "m2", "model": "claude-opus-5-5", "usage": usage}}))
    lines.append("not json")
    found = step_stats.message_usage(lines)
    assert set(found) == {"m1", "m2"}
    assert step_stats.token_totals(found) == {"new_input": 20, "cache_write": 200, "cache_read": 2000, "output": 10}


class TestE2e:
    def test_lane_runs_and_a_repeated_read_counts_once(self):
        texts = ["6 lanes …\nAll lanes done in 225 s", "tail again: All lanes done in 225 s", "All lanes done in 76 s"]
        assert step_stats.e2e_seconds(texts, CONFIG.total_line) == [225, 76]

    def test_before_the_lanes_playwright_minutes_and_unit_runs_ignored(self):
        texts = ["  147 passed (9.5m)", "  110 passed (12)", "  12 passed (28.2s)", "  180 passed (11.0m)"]
        assert step_stats.e2e_seconds(texts, CONFIG.total_line) == [570, 660]
        assert step_stats.e2e_seconds(texts) == [570, 660]          # a repo without a total line

    def test_a_lane_run_is_not_counted_twice_by_its_merged_total(self):
        assert step_stats.e2e_seconds(["  186 passed (4.0m)\nAll lanes done in 245 s"], CONFIG.total_line) == [245]

    def test_invocations_full_or_targeted(self):
        commands = ['cmd //c "tooling/run-e2e-tests.bat"', "tooling/run-e2e-tests.bat e2e/notifications.spec.js",
                    "tooling/run-tests.bat", "cat tooling/run-e2e-tests.bat", "grep -n lanes tooling/run-e2e-tests.bat",
                    'cd /c/x && cmd //c "tooling/run-e2e-tests.bat e2e/a.spec.js" > out.txt']
        assert step_stats.e2e_invocations(commands, CONFIG) == {"basic": 0, "normal": 0, "targeted": 2, "full": 1}
        # Before S047 a run with no spec file is the whole suite on three devices: full
        before = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)
        assert step_stats.e2e_invocations(commands, CONFIG, before) == {"basic": 0, "normal": 0, "targeted": 2, "full": 1}

    def test_invocations_by_level_after_s047(self):
        """BR2-03: from S047 on no flag is Normal; a spec file is targeted at any level."""
        after = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)
        commands = ['cmd //c "tooling/run-e2e-tests.bat"', "tooling/run-e2e-tests.bat --level=basic",
                    "tooling/run-e2e-tests.bat --level=full", "tooling/run-e2e-tests.bat --level=normal",
                    "tooling/run-e2e-tests.bat --level=full e2e/labels.spec.js",
                    "tooling/run-e2e-tests.bat e2e/me.spec.js --project=desktop-chromium"]
        assert step_stats.e2e_invocations(commands, CONFIG, after) == {"basic": 1, "normal": 2, "targeted": 2, "full": 1}

    def test_the_runs_cell_sums_each_level(self):
        runs = [step_stats.Run("S047", "coder", "x", e2e={"basic": 1, "normal": 2, "targeted": 5}),
                step_stats.Run("S047", "code-reviewer", "y", e2e={"targeted": 1, "full": 1})]
        assert step_stats.e2e_runs_text(runs, CONFIG) == "1/2/6/1"


class TestE2eConfig:
    def test_yantras_entries(self):
        assert CONFIG.levels == ("basic", "normal", "targeted", "full")
        assert CONFIG.letters == "b/n/t/f"
        assert CONFIG.default_level == "normal"
        assert CONFIG.history == (("full", datetime(2026, 10, 25, 5, 50, tzinfo=timezone.utc)),)

    def test_two_levels_and_no_total_line(self):
        config = step_stats.e2e_config({"Browser-test wrapper": "`run-ui.sh`", "Browser-test levels": "`targeted` `normal`",
                                        "Browser-test spec files": "`.test.ts`", "Browser-test total line": None})
        assert config.letters == "t/n"
        assert config.default_level == "normal"         # missing: the first level other than targeted
        commands = ["tooling/run-ui.sh", "./run-ui.sh src/a.test.ts", "tooling/run-ui.sh --level=normal"]
        assert step_stats.e2e_invocations(commands, config) == {"targeted": 1, "normal": 2}
        assert step_stats.e2e_seconds(["All lanes done in 9 s"], config.total_line) == []

    def test_no_spec_files_entry_means_no_run_is_targeted(self):
        config = step_stats.e2e_config({"Browser-test wrapper": "`run-ui.sh`", "Browser-test levels": "`targeted` `normal`"})
        assert step_stats.e2e_invocations(["./run-ui.sh a.spec.js"], config) == {"targeted": 0, "normal": 1}

    def test_levels_with_the_same_first_letter_are_refused(self, capsys):
        with pytest.raises(SystemExit) as stopped:
            step_stats.e2e_config({"Browser-test wrapper": "`run.bat`", "Browser-test levels": "`full` `fast` `basic`"})
        assert stopped.value.code == 2
        assert "full and fast start with the same letter" in capsys.readouterr().err

    def test_a_time_that_is_not_a_date_is_refused(self, capsys):
        with pytest.raises(SystemExit) as stopped:
            step_stats.e2e_config({"Browser-test wrapper": "`run.bat`", "Browser-test levels": "`normal` `full`",
                                   "Browser-test default level": "`normal` `full` `yesterday`"})
        assert stopped.value.code == 2
        assert "yesterday" in capsys.readouterr().err

    def test_a_default_level_that_is_not_a_level_is_refused(self, capsys):
        for words in ("`norml`", "`normal` `ful` `2026-10-25T05:50Z`"):
            with pytest.raises(SystemExit) as stopped:
                step_stats.e2e_config({"Browser-test wrapper": "`run.bat`", "Browser-test levels": "`normal` `full`",
                                       "Browser-test default level": words})
            assert stopped.value.code == 2
            assert "is not one of the browser-test levels" in capsys.readouterr().err

    def test_a_level_without_a_time_is_refused(self, capsys):
        with pytest.raises(SystemExit) as stopped:
            step_stats.e2e_config({"Browser-test wrapper": "`run.bat`", "Browser-test levels": "`normal` `full`",
                                   "Browser-test default level": "`normal` `full`"})
        assert stopped.value.code == 2
        assert "no date and time" in capsys.readouterr().err

    def test_a_total_line_without_one_group_is_refused(self, capsys):
        for line in (r"`done in \d+ s`", r"`(\d+) of (\d+)`", "`(unclosed`"):
            with pytest.raises(SystemExit) as stopped:
                step_stats.e2e_config({"Browser-test wrapper": "`run.bat`", "Browser-test levels": "`normal` `full`",
                                       "Browser-test total line": line})
            assert stopped.value.code == 2
            assert "browser-test total line" in capsys.readouterr().err

    def test_no_wrapper_or_no_levels_counts_no_browser_runs(self):
        assert step_stats.e2e_config({}) is None
        assert step_stats.e2e_config({"Browser-test wrapper": None, "Browser-test levels": "`a`"}) is None
        assert step_stats.e2e_config({"Browser-test wrapper": "`run.bat`"}) is None


def test_the_report_has_no_e2e_columns_without_a_wrapper(tmp_path, monkeypatch):
    (tmp_path / "S001-x").mkdir()
    (tmp_path / "INDEX.md").write_text("## Index\n\n| S001 | [X](S001-x/1-brief.md) — x | 1 | Done | 25-10-2026 |\n", encoding="utf-8")
    monkeypatch.setattr(step_facts, "STEPS_DIR", tmp_path)
    monkeypatch.setattr(step_stats, "read_runs", lambda config=None: [])
    monkeypatch.setattr(step_facts, "git", lambda *args: "")
    without = step_stats.build_report(None, None)
    assert "E2E" not in without
    assert "E2E runs (b/n/t/f)" in step_stats.build_report(None, CONFIG)


def test_the_report_needs_the_settings_section(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(step_facts, "SETTINGS_FILE", tmp_path / "CLAUDE.md")        # no such file
    with pytest.raises(SystemExit) as stopped:
        step_stats.main([])
    assert stopped.value.code == 2
    assert "no Step workflow section" in capsys.readouterr().err


def test_invocations_in_subshells_and_with_a_timeout():
    commands = ["(tooling/run-e2e-tests.bat > scratch/e2e.log 2>&1; echo EXIT $? >> scratch/e2e.log)",
                "cd /c/x; timeout 580 tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js",
                "until grep -q EXIT scratch/e2e.log; do sleep 20; done"]
    assert step_stats.e2e_invocations(commands, CONFIG) == {"basic": 0, "normal": 0, "targeted": 1, "full": 1}


def test_nits_as_a_short_list_are_counted():
    text = "### CR2-01 — major — x\n\n## Nits\n\n- **CR2-02** (nit) `a.py:3`: rename.\n- **CR2-03** (nit) `b.js:9`: comment.\n"
    assert step_stats.review_findings("4-code-review-r2.md", text) == {"major": 1, "nit": 2}
