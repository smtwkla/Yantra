"""The worker: its lock, reconnecting, the schedule, the purge and the tasks card
(S013 § 5.5, § 5.6, § 8 Worker and Purge).

The lock name is a test one, for this run's database (tests/db_names.py): GET_LOCK names are
server-wide, and a dev worker on the same MariaDB holds yantra_worker:vel_yantra_master.
"""

import signal
from datetime import datetime

import pytest

import config
import task_handlers
import worker as worker_module
from local_db import LOCK_WORKER, get_local_db, named_lock
from task_handlers import purge_access_log
from tests.db_names import TEST_WORKER_LOCK as TEST_LOCK
from worker import Worker


def _run(sql, params=()):
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


@pytest.fixture
def empty_queue():
    _run("DELETE FROM task_queue")
    yield
    _run("DELETE FROM task_queue")


@pytest.fixture
def make_worker():
    made = []

    def make(clock=None):
        w = Worker(config.DB_CONFIG, lock_name=TEST_LOCK, **({"clock": clock} if clock else {}))
        made.append(w)
        return w
    yield make
    for w in made:
        w.close()


class TestLock:

    def test_the_default_name_carries_the_database(self):
        assert Worker(config.DB_CONFIG)._lock_name == named_lock(LOCK_WORKER, config.DB_CONFIG["database"])

    def test_taken_once(self, make_worker):
        first = make_worker()
        first.connect()
        assert first.holds_lock()
        assert first.holds_lock()   # asked again: still held, not re-taken
        other = get_local_db(config.DB_CONFIG)
        try:
            with other.cursor() as cur:
                cur.execute("SELECT GET_LOCK(%s, 0) AS got", (TEST_LOCK,))
                assert cur.fetchone()["got"] == 0
        finally:
            other.close()
        second = make_worker()
        second.connect()
        assert not second.holds_lock()
        assert second.run_once() is False

    def test_released_when_the_holder_closes(self, make_worker):
        first, second = make_worker(), make_worker()
        first.connect()
        second.connect()
        assert first.holds_lock() and not second.holds_lock()
        first.close()
        assert second.holds_lock()

    def test_retaken_after_a_dropped_connection(self, make_worker, empty_queue, monkeypatch):
        # The test is about the reconnect: no daily task may become due and run (CR1-01)
        monkeypatch.setattr(worker_module, "SCHEDULE", [])
        w = make_worker()
        w.connect()
        assert w.holds_lock()
        old_id = w.conn.thread_id()
        _run(f"KILL {int(old_id)}")
        assert w.run_once() is True   # pings, reconnects, takes the lock again, then works
        assert w.conn.thread_id() != old_id
        held_by = _run("SELECT IS_USED_LOCK(%s) AS id", (TEST_LOCK,))[0]["id"]
        assert held_by == w.conn.thread_id()

    def test_nothing_while_the_schema_is_down(self, make_worker, monkeypatch):
        monkeypatch.setattr(worker_module, "ensure_schema", lambda _config: "down")
        w = make_worker()
        assert w.run_once() is False
        assert w.conn is None   # never connected


class TestMainLoop:

    def test_an_unexpected_error_does_not_end_the_worker(self, monkeypatch, caplog):
        calls = []

        def run_once(self):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("bad schedule")
            self.stop()   # the second loop is reached: the worker carried on
            return True

        monkeypatch.setattr(Worker, "run_once", run_once)
        monkeypatch.setattr(worker_module, "WORKER_POLL_SECONDS", 0)
        old = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            with caplog.at_level("ERROR", logger="worker"):
                worker_module.main()
        finally:
            for s, handler in old.items():
                signal.signal(s, handler)
        assert len(calls) == 2
        assert any("ValueError" in (r.exc_text or "") or r.exc_info for r in caplog.records)


class TestSchedule:

    def test_due_task_enqueued_once_and_run(self, make_worker, empty_queue, monkeypatch):
        # Due at midnight on the database's clock, which also stamps created_at
        monkeypatch.setattr(worker_module, "SCHEDULE", [("purge_access_log", "00:00")])
        w = make_worker(clock=lambda: _run("SELECT NOW() AS now")[0]["now"])
        assert w.run_once() is True
        rows = _run("SELECT task_type, status FROM task_queue")
        assert [(r["task_type"], r["status"]) for r in rows] == [("purge_access_log", "done")]
        w.run_once()   # a second loop the same day enqueues nothing
        assert len(_run("SELECT id FROM task_queue")) == 1

    def test_not_before_the_time(self, make_worker, empty_queue):
        # created_at is the real NOW(); a clock early on a later day finds nothing due
        w = make_worker(clock=lambda: datetime(2099, 1, 1, 2, 29))
        w.connect()
        _run("INSERT INTO task_queue (task_type, status, created_at) VALUES ('purge_access_log', 'done', "
             "'2098-12-31 02:30:00')")
        assert w.enqueue_scheduled() == []


def _log_row(age_days):
    _run("INSERT INTO access_log (ts, username, client_ip, is_internal, outcome, method, path, sighting_day,"
         " sighting_hash) VALUES (NOW() - INTERVAL %s DAY, 'purge_test', '10.9.9.9', 1, 'ok', 'GET', '/api/x',"
         " CURDATE() - INTERVAL %s DAY, SHA1(UUID()))", (age_days, age_days))


class TestPurge:

    @pytest.fixture
    def conn(self):
        _run("DELETE FROM access_log WHERE username = 'purge_test'")
        connection = get_local_db(config.DB_CONFIG)
        yield connection
        connection.close()
        _run("DELETE FROM access_log WHERE username = 'purge_test'")

    def _left(self):
        return [r["age"] for r in _run("SELECT DATEDIFF(NOW(), ts) AS age FROM access_log "
                                        "WHERE username = 'purge_test' ORDER BY ts")]

    def test_old_rows_go_new_rows_stay(self, conn, empty_queue):
        for age in (400, 366, 364, 1):
            _log_row(age)
        purge_access_log(conn, None, lambda: False)
        assert self._left() == [364, 1]

    def test_batches_and_the_stop_flag(self, conn, empty_queue, monkeypatch):
        monkeypatch.setattr(task_handlers, "PURGE_BATCH_ROWS", 2)
        for _ in range(5):
            _log_row(500)
        purge_access_log(conn, None, lambda: True)   # stops after the first batch
        assert len(self._left()) == 3
        purge_access_log(conn, None, lambda: False)  # the next run continues
        assert self._left() == []

    def test_old_done_tasks_go_the_last_per_type_and_failed_stay(self, conn, empty_queue):
        for task_type, status, age in [("t_a", "done", 200), ("t_a", "done", 100), ("t_a", "done", 10),
                                       ("t_b", "done", 300), ("t_b", "failed", 300), ("t_c", "done", 200)]:
            _run("INSERT INTO task_queue (task_type, status, created_at) "
                 "VALUES (%s, %s, NOW() - INTERVAL %s DAY)", (task_type, status, age))
        purge_access_log(conn, None, lambda: False)
        left = [(r["task_type"], r["status"], r["age"]) for r in _run(
            "SELECT task_type, status, DATEDIFF(NOW(), created_at) AS age FROM task_queue ORDER BY id")]
        # t_a: the 10-day row stays (recent and the last); t_b: the done row is old and not the
        # last (the failed one is), so it goes; t_c: old, but its type's last row, so it stays
        assert left == [("t_a", "done", 10), ("t_b", "failed", 300), ("t_c", "done", 200)]


class TestTasksCard:

    def test_never_run_is_overdue_after_the_time(self, role_client, empty_queue):
        body = role_client("it_admin").get("/api/settings/tasks").get_json()
        line = body["tasks"][0]
        assert line["task_type"] == "purge_access_log" and line["daily_at"] == "02:30"
        assert line["last_run"] is None and line["last_status"] is None
        now = _run("SELECT NOW() AS now")[0]["now"]
        assert line["overdue"] is (now > datetime.combine(now.date(), datetime.min.time()).replace(hour=2, minute=35))
        assert body["failed_count"] == 0

    def test_done_today_is_not_overdue(self, role_client, empty_queue):
        _run("INSERT INTO task_queue (task_type, status, created_at, completed_at) "
             "VALUES ('purge_access_log', 'done', NOW(), NOW())")
        _run("INSERT INTO task_queue (task_type, status) VALUES ('x', 'failed')")
        body = role_client("maint_manager").get("/api/settings/tasks").get_json()
        line = body["tasks"][0]
        assert line["last_status"] == "done" and line["last_run"] is not None and line["overdue"] is False
        assert body["failed_count"] == 1

    def test_engineer_may_not_read(self, role_client):
        assert role_client("maint_engineer").get("/api/settings/tasks").status_code == 403
