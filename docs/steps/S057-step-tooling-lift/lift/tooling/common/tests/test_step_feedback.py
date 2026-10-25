"""step_feedback.feedback_items: the agents' `## Feedback` items (25-10-2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))

from step_feedback import feedback_items  # noqa: E402

REPORT = """# S099 — Impl report

## Tests

- waste: not feedback, this is the Tests section

## Feedback

- waste: ran the whole suite twice (8 min)
- hindrance: cmd //c mangled the -g quote (2 runs)
- `rule`: two rules disagree on the e2e level (coder.md vs SKILL.md)
- idea — a .cmd helper for one test
- surprise: a label nobody defined
- none

## Fix rounds

### Round 1

- waste: still not feedback

#### Feedback

- waste: re-read the brief for one line
"""


def test_items_come_only_from_feedback_sections():
    items = feedback_items(REPORT)
    assert ("waste", "ran the whole suite twice (8 min)") in items
    assert ("waste", "re-read the brief for one line") in items
    assert all("not feedback" not in text for _, text in items)


def test_labels_in_backticks_and_with_a_dash_are_read():
    items = feedback_items(REPORT)
    assert ("rule", "two rules disagree on the e2e level (coder.md vs SKILL.md)") in items
    assert ("idea", "a .cmd helper for one test") in items


def test_an_unknown_label_is_kept_as_other_and_none_is_counted():
    labels = [label for label, _ in feedback_items(REPORT)]
    assert labels.count("other") == 1
    assert labels.count("none") == 1


def test_a_file_without_a_feedback_section_gives_nothing():
    assert feedback_items("# S001\n\n## Tests\n\n- waste: no\n") == []


def test_a_higher_heading_ends_the_section():
    text = "### Feedback\n\n- idea: one\n\n## Next\n\n- idea: not this\n"
    assert feedback_items(text) == [("idea", "one")]
