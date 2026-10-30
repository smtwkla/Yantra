"""The daily schedule's pure core (S013 § 5.6, § 8 Pure)."""

from datetime import datetime

from scheduled_tasks import SCHEDULE, due_tasks, is_overdue, next_run

ENTRY = ("purge_access_log", "02:30")
SCHED = [ENTRY]


def at(day, hhmm):
    hours, minutes = hhmm.split(":")
    return datetime(2026, 10, day, int(hours), int(minutes))


def test_the_schedule_has_the_purge():
    assert ("purge_access_log", "02:30") in SCHEDULE


def test_the_improvement_alerts_at_eight_after_the_purge():
    """S074 § 5.2: the morning scan; the purge stays first (the tasks card's tasks[0])."""
    assert SCHEDULE == [("purge_access_log", "02:30"), ("improvement_alert_scan", "08:00")]


class TestDueTasks:

    def test_before_the_time(self):
        assert due_tasks(SCHED, {"purge_access_log": at(17, "02:30")}, at(18, "02:29")) == []

    def test_after_the_time_and_not_yet_enqueued(self):
        assert due_tasks(SCHED, {"purge_access_log": at(17, "02:30")}, at(18, "02:30")) == ["purge_access_log"]

    def test_never_enqueued(self):
        assert due_tasks(SCHED, {}, at(18, "09:00")) == ["purge_access_log"]
        assert due_tasks(SCHED, {"purge_access_log": None}, at(18, "09:00")) == ["purge_access_log"]

    def test_already_enqueued_today(self):
        assert due_tasks(SCHED, {"purge_access_log": at(18, "02:30")}, at(18, "02:35")) == []
        assert due_tasks(SCHED, {"purge_access_log": at(18, "11:00")}, at(18, "23:59")) == []

    def test_worker_down_over_the_time_runs_once_on_return(self):
        last = {"purge_access_log": at(17, "02:31")}
        assert due_tasks(SCHED, last, at(18, "08:00")) == ["purge_access_log"]
        last["purge_access_log"] = at(18, "08:00")   # enqueued on return
        assert due_tasks(SCHED, last, at(18, "08:00")) == []
        assert due_tasks(SCHED, last, at(18, "23:00")) == []

    def test_day_change(self):
        last = {"purge_access_log": at(18, "02:30")}
        assert due_tasks(SCHED, last, at(19, "00:01")) == []
        assert due_tasks(SCHED, last, at(19, "02:30")) == ["purge_access_log"]

    def test_an_enqueue_before_todays_time_does_not_count(self):
        # Enqueued at 01:00 today (a late run of yesterday's): today's 02:30 still runs
        assert due_tasks(SCHED, {"purge_access_log": at(18, "01:00")}, at(18, "03:00")) == ["purge_access_log"]


class TestNextRun:

    def test_today_when_not_yet_enqueued(self):
        assert next_run(ENTRY, {"purge_access_log": at(17, "02:30")}, at(18, "01:00")) == at(18, "02:30")

    def test_tomorrow_when_done_today(self):
        assert next_run(ENTRY, {"purge_access_log": at(18, "02:30")}, at(18, "03:00")) == at(19, "02:30")

    def test_in_the_past_when_the_worker_is_late(self):
        assert next_run(ENTRY, {}, at(18, "09:00")) == at(18, "02:30")


class TestOverdue:

    def test_within_five_minutes_is_not_overdue(self):
        assert not is_overdue(at(18, "02:30"), at(18, "02:35"))
        assert not is_overdue(at(19, "02:30"), at(18, "09:00"))

    def test_past_five_minutes_is_overdue(self):
        assert is_overdue(at(18, "02:30"), at(18, "02:36"))
        assert is_overdue(next_run(ENTRY, {}, at(18, "09:00")), at(18, "09:00"))
