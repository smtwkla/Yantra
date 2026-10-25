"""tooling/steps/step_stats.py: the parsing behind /step stats.  No transcripts and no step
files: the pure functions only."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "steps"))

import step_stats  # noqa: E402

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
        assert step_stats.e2e_seconds(texts) == [225, 76]

    def test_before_the_lanes_playwright_minutes_and_unit_runs_ignored(self):
        texts = ["  147 passed (9.5m)", "  110 passed (12)", "  12 passed (28.2s)", "  180 passed (11.0m)"]
        assert step_stats.e2e_seconds(texts) == [570, 660]

    def test_a_lane_run_is_not_counted_twice_by_its_merged_total(self):
        assert step_stats.e2e_seconds(["  186 passed (4.0m)\nAll lanes done in 245 s"]) == [245]

    def test_invocations_full_or_targeted(self):
        commands = ['cmd //c "tooling/run-e2e-tests.bat"', "tooling/run-e2e-tests.bat e2e/notifications.spec.js",
                    "tooling/run-tests.bat", "cat tooling/run-e2e-tests.bat", "grep -n lanes tooling/run-e2e-tests.bat",
                    'cd /c/x && cmd //c "tooling/run-e2e-tests.bat e2e/a.spec.js" > out.txt']
        assert step_stats.e2e_invocations(commands) == (0, 0, 2, 1)
        # Before S047 a run with no spec file is the whole suite on three devices: full
        assert step_stats.e2e_invocations(commands, datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)) == (0, 0, 2, 1)

    def test_invocations_by_level_after_s047(self):
        """BR2-03: from S047 on no flag is Normal; a spec file is targeted at any level."""
        after = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)
        commands = ['cmd //c "tooling/run-e2e-tests.bat"', "tooling/run-e2e-tests.bat --level=basic",
                    "tooling/run-e2e-tests.bat --level=full", "tooling/run-e2e-tests.bat --level=normal",
                    "tooling/run-e2e-tests.bat --level=full e2e/labels.spec.js",
                    "tooling/run-e2e-tests.bat e2e/me.spec.js --project=desktop-chromium"]
        assert step_stats.e2e_invocations(commands, after) == (1, 2, 2, 1)

    def test_the_runs_cell_sums_each_level(self):
        runs = [step_stats.Run("S047", "coder", "x", e2e_basic=1, e2e_normal=2, e2e_targeted=5),
                step_stats.Run("S047", "code-reviewer", "y", e2e_targeted=1, e2e_full=1)]
        assert step_stats.e2e_runs_text(runs) == "1/2/6/1"


def test_invocations_in_subshells_and_with_a_timeout():
    commands = ["(tooling/run-e2e-tests.bat > scratch/e2e.log 2>&1; echo EXIT $? >> scratch/e2e.log)",
                "cd /c/x; timeout 580 tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js",
                "until grep -q EXIT scratch/e2e.log; do sleep 20; done"]
    assert step_stats.e2e_invocations(commands) == (0, 0, 1, 1)


def test_nits_as_a_short_list_are_counted():
    text = "### CR2-01 — major — x\n\n## Nits\n\n- **CR2-02** (nit) `a.py:3`: rename.\n- **CR2-03** (nit) `b.js:9`: comment.\n"
    assert step_stats.review_findings("4-code-review-r2.md", text) == {"major": 1, "nit": 2}
