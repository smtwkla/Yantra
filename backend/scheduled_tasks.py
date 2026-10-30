"""The daily schedule — the pure part (S013 § 5.6).

The worker enqueues a scheduled task once a day at its IST time.  Whether a task is due is
decided from task_queue itself (the last time one of that type was enqueued), so a worker
that was down over the time runs it once when it comes back, and a restart never runs it
twice.  A small built-in schedule, not APScheduler (S013 § 7): every task so far is daily.
"""

from datetime import datetime, time, timedelta

# (task_type, "HH:MM" IST), daily
SCHEDULE = [
    ("purge_access_log", "02:30"),
    # S074: overdue countermeasures and ended watches, at the start of the working day (§ 9 Q1)
    ("improvement_alert_scan", "08:00"),
]

# The Background tasks card calls a task overdue when its next run is this far in the past
OVERDUE_MINUTES = 5


def _at(hhmm):
    hours, minutes = hhmm.split(":")
    return time(int(hours), int(minutes))


def todays_time(entry, now_ist):
    """Today's run time of a schedule entry, as a naive IST datetime."""
    return datetime.combine(now_ist.date(), _at(entry[1]))


def _enqueued_since(last, moment):
    return last is not None and last >= moment


def due_tasks(schedule, last_enqueued, now_ist):
    """The task types to enqueue now: today's time has passed and nothing of that type was
    enqueued since it.  ``last_enqueued`` maps a type to its last created_at (or None)."""
    due = []
    for entry in schedule:
        today = todays_time(entry, now_ist)
        if now_ist >= today and not _enqueued_since(last_enqueued.get(entry[0]), today):
            due.append(entry[0])
    return due


def next_run(entry, last_enqueued, now_ist):
    """Today's time when not yet enqueued since it (in the past when the worker is late),
    else tomorrow's."""
    today = todays_time(entry, now_ist)
    if _enqueued_since(last_enqueued.get(entry[0]), today):
        return today + timedelta(days=1)
    return today


def is_overdue(next_run_at, now_ist):
    """More than OVERDUE_MINUTES past its next run: is the worker running?"""
    return now_ist - next_run_at > timedelta(minutes=OVERDUE_MINUTES)
