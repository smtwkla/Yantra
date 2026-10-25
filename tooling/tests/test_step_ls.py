"""step_ls.shown: which steps `/step ls` lists (parked steps only on request, 25-10-2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "steps"))

from step_ls import shown  # noqa: E402

OPEN = "Implementing (approved 25-10-2026 by KLA)"
DONE = "Done (committed 120ca79, 25-10-2026)"
DROPPED = "Dropped 20-10-2026"
PARKED = "Parked 25-10-2026 by KLA"


def test_a_plain_listing_shows_open_steps_only():
    assert shown(OPEN, [])
    assert not shown(DONE, [])
    assert not shown(DROPPED, [])
    assert not shown(PARKED, [])
    assert not shown("Deferred to S060", [])


def test_deferred_shows_the_parked_steps_only():
    assert shown(PARKED, ["deferred"])
    assert shown("Deferred to S060", ["deferred"])
    assert not shown(OPEN, ["deferred"])
    assert not shown(DONE, ["deferred"])


def test_all_shows_every_step():
    for status in (OPEN, DONE, DROPPED, PARKED, ""):
        assert shown(status, ["all"])


def test_a_step_without_a_brief_is_open():
    assert shown("", [])
