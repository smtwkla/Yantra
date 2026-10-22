"""tooling/steps/step_facts.py and step_check.py: the parsing behind /step ls and the checks
behind /step check.  No git and no files: the pure functions only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "steps"))

import step_check  # noqa: E402
import step_facts  # noqa: E402

README = """\
## Index

| ID | Title | Plan.MD phase | Status | Date |
|---|---|---|---|---|
| S001 | [Basic masters](S001-basic-masters/1-brief.md) — sites, units | 2 | Done — committed 817844c | 14-10-2026 |
| S027 | [Work notes](S027-work-notes/1-brief.md) — notes | 3 | Gate A (BR r1) | 22-10-2026 |

## Queued (not yet briefed)

| Idea | From | Note |
|---|---|---|
| S030 Calibration — instruments | user | later |
| Malware scanning of uploads | user | ClamAV |
"""
HASHES = ["b6b8dfb0123456789abcdef0123456789abcdef0", "3df667c0123456789abcdef0123456789abcdef0"]


# ---------------------------------------------------------------------------------------------
# step_facts
# ---------------------------------------------------------------------------------------------

class TestParseIndex:
    def test_index_rows_with_their_status_cell(self):
        steps, _ = step_facts.parse_index(README)
        assert steps == [("S001", "Basic masters", "S001-basic-masters", "Done — committed 817844c"),
                         ("S027", "Work notes", "S027-work-notes", "Gate A (BR r1)")]

    def test_queued_rows_with_an_id_only(self):
        _, queued = step_facts.parse_index(README)
        assert queued == [("S030", "S030 Calibration — instruments")]


def test_header_value():
    header = "```\nStep: S027 — Work notes\nTrack: full\nStatus: Gate A — awaiting the user\nBaseline: bbaed12\n```\n"
    assert step_facts.header_value(header, "Status") == "Gate A — awaiting the user"
    assert step_facts.header_value(header, "Baseline") == "bbaed12"
    assert step_facts.header_value("```\nStep: S001\n```\n", "Status") == ""


class TestLatestReview:
    def test_code_review_after_brief_review(self):
        names = ["1-brief.md", "2-brief-review-r3.md", "4-code-review-r1.md", "4-code-review-r2.md"]
        assert step_facts.latest_review(names) == ("4-code-review-r2.md", "CR r2")

    def test_staleness_round_after_the_brief_rounds(self):
        names = ["2-brief-review-r2.md", "2-brief-review-s1.md"]
        assert step_facts.latest_review(names) == ("2-brief-review-s1.md", "BR s1")

    def test_round_ten_after_round_nine(self):
        assert step_facts.latest_review(["4-code-review-r9.md", "4-code-review-r10.md"])[1] == "CR r10"

    def test_none(self):
        assert step_facts.latest_review(["1-brief.md", "s009-code.patch"]) == (None, "")


class TestVerdictLine:
    def test_the_paragraph_on_one_line_without_markup(self):
        text = "# Review\n\n**Verdict: no `blocker` or `major` finding is open.** Two\n`nit`s.\n\n## Findings\n"
        assert step_facts.verdict_line(text) == "Verdict: no blocker or major finding is open. Two nits."

    def test_cut_at_the_limit(self):
        line = step_facts.verdict_line("Verdict: " + "x" * 500)
        assert len(line) == step_facts.VERDICT_MAX and line.endswith("…")

    def test_none(self):
        assert step_facts.verdict_line("# Review\n\nNo verdict here.\n") == ""


class TestSubjectSteps:
    def test_one_step(self):
        assert step_facts.subject_steps("S018: Work the ticket - acknowledge;") == ["S018"]

    def test_several_steps_and_leading_spaces(self):
        assert step_facts.subject_steps("   S025, S019, S020: release safety;") == ["S025", "S019", "S020"]

    def test_plus_and_dash(self):
        assert step_facts.subject_steps("S007 + S008 - dialog guard") == ["S007", "S008"]

    def test_no_step_prefix(self):
        assert step_facts.subject_steps("doc;") == []
        assert step_facts.subject_steps("release v0.1.3") == []
        assert step_facts.subject_steps("fix S018's labour total") == []


def test_impl_report_files():
    text = "- `backend/tickets.py`: the route.\n- `frontend/src/views/tickets/NoteDialog.vue` (new)\n- `WORK_KEY`\n"
    assert step_facts.impl_report_files(text) == {"backend/tickets.py", "frontend/src/views/tickets/NoteDialog.vue"}


# ---------------------------------------------------------------------------------------------
# step_check
# ---------------------------------------------------------------------------------------------

def test_stage():
    assert step_check.stage("Done (committed b6b8dfb; checks: 7 auto)") == "done"
    assert step_check.stage("Gate B — code review r2 clean") == "gate b"
    assert step_check.stage("In code review (A1)") == "in code review"
    assert step_check.stage("Something else") == ""


class TestStageMatchesReadme:
    def test_same_stage_in_other_words(self):
        assert step_check.check_stage_matches_readme("Done (committed b6b8dfb)", "Done — committed b6b8dfb") == []

    def test_different_stage(self):
        [problem] = step_check.check_stage_matches_readme("Implementing (approved)", "In review (light track)")
        assert "(1)" in problem

    def test_an_unknown_form_is_not_judged(self):
        assert step_check.check_stage_matches_readme("Committed b6b8dfb", "see the brief") == []


class TestCommits:
    def test_committed_but_still_at_gate_b(self):
        [problem] = step_check.check_commits("Gate B — clean", ["b6b8dfb"], HASHES)
        assert "b6b8dfb" in problem and "(2)" in problem

    def test_a_hash_not_in_the_history(self):
        [problem] = step_check.check_commits("Done (committed 799851c)", ["c11a549"], HASHES)
        assert "799851c" in problem

    def test_consistent(self):
        assert step_check.check_commits("Committed b6b8dfb (22-10-2026)", ["b6b8dfb"], HASHES) == []
        assert step_check.check_commits("Approved 21-10-2026", [], HASHES) == []


class TestManualBoxes:
    def test_done_with_an_open_important_check(self):
        [problem] = step_check.check_manual_boxes("Done", "## Manual checks\n- [auto] a\n- [ ] b\n")
        assert "(3)" in problem

    def test_committed_with_every_check_resolved(self):
        [problem] = step_check.check_manual_boxes("Committed abc1234", "- [auto] a\n- [x] b — by KLA\n")
        assert "2 resolved" in problem and "(4)" in problem

    def test_committed_with_a_check_open(self):
        assert step_check.check_manual_boxes("Committed abc1234", "- [auto] a\n- [ ] b\n") == []

    def test_no_impl_report(self):
        assert step_check.check_manual_boxes("Done", "") == []


def test_unanswered_findings():
    review = "## Findings\n\n### BR1-01 (minor) — a\n\n### BR1-02 (nit) — b\n\nSee BR9-09 in text.\n"
    brief = "## Review log\n| BR1-01 a | minor | Accepted |\n"
    assert step_check.unanswered_findings([review], brief) == ["BR1-02"]
    assert step_check.unanswered_findings([review], brief + "| BR1-02 b | nit | Accepted |\n") == []


class TestBaseline:
    def test_approved_without_a_baseline(self):
        [problem] = step_check.check_baseline("Approved 22-10-2026", "Status: Approved\n", HASHES)
        assert "(6)" in problem

    def test_a_baseline_not_in_the_history(self):
        [problem] = step_check.check_baseline("Implementing", "Baseline: 1234567 + uncommitted S025\n", HASHES)
        assert "1234567" in problem

    def test_good_or_not_needed(self):
        assert step_check.check_baseline("Gate B", "Baseline: 3df667c + uncommitted S025\n", HASHES) == []
        assert step_check.check_baseline("Done", "", HASHES) == []


DEVICE_CHECKS = """\
## After each deploy

| # | What to do | Account | Network | Where | Done |
|---|---|---|---|---|---|
| D1 | Log in (S011) | test | Wi-Fi | Production | |

## Open checks by step

| # | Step | What to do | Account | Network | Where | Done |
|---|---|---|---|---|---|---|
| 8 | S016, S017, S018 | iPhone message | operator | either | either | |
| 10 | S019 | date picker | engineer | either | either | IT Admin, 23-10-2026 |
"""


def test_device_rows():
    assert step_check.device_rows(DEVICE_CHECKS) == [("8", ["S016", "S017", "S018"], ""),
                                                     ("10", ["S019"], "IT Admin, 23-10-2026")]


class TestDeviceRows:
    rows = step_check.device_rows(DEVICE_CHECKS)

    def test_a_row_done_but_not_ticked_in_the_report(self):
        [problem] = step_check.check_device_rows("S019", "Committed b6b8dfb", "- [ ] date picker\n", self.rows)
        assert "row(s) 10" in problem and "(7)" in problem

    def test_ticked_in_the_report_but_the_row_is_open(self):
        [problem] = step_check.check_device_rows("S017", "Done", "- [x] camera — by IT Admin\n", self.rows)
        assert "row(s) 8" in problem

    def test_consistent(self):
        assert step_check.check_device_rows("S019", "Done", "- [x] date picker — by IT Admin\n", self.rows) == []
        assert step_check.check_device_rows("S025", "Done", "- [ ] x\n", self.rows) == []


def test_check_folders():
    problems = step_check.check_folders(["S026-refusal-in-view", "S028-gone"],
                                        ["S026-refusal-in-view", "S026-work-notes", "S027-work-notes"])
    assert any("S028-gone does not exist" in p for p in problems)
    assert any("S026-work-notes has no README row" in p for p in problems)
    assert any("S026 is used by 2 folders" in p for p in problems)


class TestStageFiles:
    def test_gate_b_without_a_code_review(self):
        assert step_check.check_stage_files("Gate B", ["1-brief.md", "3-impl-report.md"], True) == [
            "Gate B but there is no code review (9)"]

    def test_done_without_an_impl_report(self):
        [problem] = step_check.check_stage_files("Done", ["1-brief.md"], False)
        assert "no 3-impl-report.md" in problem

    def test_an_impl_report_before_approval(self):
        [problem] = step_check.check_stage_files("Gate A", ["1-brief.md", "3-impl-report.md"], True)
        assert "exists" in problem
