"""tooling/e2e/run_lanes.py: how many lanes a run gets, and the lane summary line.  No
Playwright and no database: the pure helpers only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "e2e"))

import run_lanes  # noqa: E402

SPEC_COUNT = len(list((run_lanes.FRONTEND / "e2e").glob("*.spec.js")))


class TestLaneCount:
    def test_a_full_run_takes_the_lanes_asked_for(self):
        assert run_lanes.lane_count([], 6) == 6

    def test_one_spec_on_every_project_needs_three(self):
        assert run_lanes.lane_count(["e2e/labels.spec.js"], 6) == 3

    def test_one_spec_on_one_project_needs_one(self):
        assert run_lanes.lane_count(["e2e/labels.spec.js", "--project=phone-chromium"], 6) == 1

    def test_one_project_of_every_spec(self):
        assert run_lanes.lane_count(["--project=phone-webkit"], 20) == min(20, SPEC_COUNT)

    def test_never_more_than_asked(self):
        assert run_lanes.lane_count(["e2e/a.spec.js", "e2e/b.spec.js"], 4) == 4


def test_lane_database_ends_in_e2e():
    assert run_lanes.lane_database(2) == "vel_yantra_lane2_e2e"


def test_summary_of_a_lane_log():
    log = "[1/9] …\n  1 failed\n    [phone-webkit] › e2e/x.spec.js:3:1 › y\n  8 passed (1.2m)\n"
    assert run_lanes.summary_of(log) == "1 failed, 8 passed"
    assert run_lanes.summary_of("crashed") == "no summary (see the log)"


def test_a_second_run_cannot_take_the_lock(tmp_path, monkeypatch):
    """The lock is exclusive: while one handle holds it, a second gets an OSError (and the run
    waits); once released, the second takes it."""
    monkeypatch.setattr(run_lanes, "LOCK_FILE", tmp_path / "e2e-run.lock")
    with run_lanes.one_run_at_a_time():
        other = open(run_lanes.LOCK_FILE, "a+")
        try:
            try:
                run_lanes._lock(other)
                taken = True
            except OSError:
                taken = False
            assert not taken
        finally:
            other.close()
    other = open(run_lanes.LOCK_FILE, "a+")
    run_lanes._lock(other)
    run_lanes._unlock(other)
    other.close()
