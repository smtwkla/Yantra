"""The job queue: enqueue, claim, done, retries, stale claims, bad tasks (S013 § 5.5, § 8 Queue).

The queue table is emptied before each test: claim_next takes any due task.
"""

import pymysql
import pytest

import config
import task_handlers
from db_helpers import transaction
from local_db import get_local_db
from task_queue import claim_next, enqueue, mark_done, mark_failed, requeue_stale
from worker import Worker

TEST_LOCK = "yantra_worker_test"


@pytest.fixture
def conn():
    connection = get_local_db(config.DB_CONFIG)
    with connection.cursor() as cur:
        cur.execute("DELETE FROM task_queue")
    yield connection
    with connection.cursor() as cur:
        cur.execute("DELETE FROM task_queue")
    connection.close()


def _task(conn, task_id):
    with conn.cursor() as cur:
        cur.execute("SELECT *, NOW() AS now FROM task_queue WHERE id = %s", (task_id,))
        return cur.fetchone()


def _add(conn, task_type, **kwargs):
    with conn.cursor() as cur:
        return enqueue(cur, task_type, **kwargs)


@pytest.fixture
def worker():
    w = Worker(config.DB_CONFIG, lock_name=TEST_LOCK)
    yield w
    w.close()


class TestEnqueue:

    def test_rolled_back_with_the_callers_transaction(self, conn):
        with pytest.raises(RuntimeError):
            with transaction(conn), conn.cursor() as cur:
                enqueue(cur, "noop")
                raise RuntimeError("the business write failed")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM task_queue")
            assert cur.fetchone()["n"] == 0

    def test_defaults_and_payload(self, conn):
        task = _task(conn, _add(conn, "noop", payload={"a": 1}))
        assert task["status"] == "pending" and task["attempts"] == 0 and task["max_attempts"] == 3
        assert task["scheduled_for"] <= task["now"]

    def test_a_future_task_is_not_claimed(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT NOW() + INTERVAL 1 HOUR AS later")
            later = cur.fetchone()["later"]
        _add(conn, "noop", scheduled_for=later)
        assert claim_next(conn) is None


class TestClaimAndFinish:

    def test_claim_marks_running(self, conn):
        task_id = _add(conn, "noop", payload={"a": 1})
        claimed = claim_next(conn)
        assert claimed["id"] == task_id and claimed["attempts"] == 1 and claimed["payload"] == {"a": 1}
        row = _task(conn, task_id)
        assert row["status"] == "running" and row["attempts"] == 1 and row["locked_until"] > row["now"]
        assert claim_next(conn) is None

    def test_oldest_due_first(self, conn):
        first, second = _add(conn, "noop"), _add(conn, "noop")
        assert claim_next(conn)["id"] == first
        assert claim_next(conn)["id"] == second

    def test_done(self, conn):
        task_id = _add(conn, "noop")
        claim_next(conn)
        with conn.cursor() as cur:
            mark_done(cur, task_id)
        row = _task(conn, task_id)
        assert row["status"] == "done" and row["completed_at"] is not None and row["locked_until"] is None

    def test_failed_retries_with_backoff_then_fails(self, conn):
        task_id = _add(conn, "noop", max_attempts=2)
        claim_next(conn)
        assert mark_failed(conn, task_id, "boom 1") == "pending"
        row = _task(conn, task_id)
        assert row["last_error"] == "boom 1"
        backoff = (row["scheduled_for"] - row["now"]).total_seconds()
        assert 4 * 60 < backoff <= 5 * 60   # TASK_RETRY_BACKOFF_MINUTES x 1 attempt
        with conn.cursor() as cur:
            cur.execute("UPDATE task_queue SET scheduled_for = NOW() WHERE id = %s", (task_id,))
        claim_next(conn)
        assert mark_failed(conn, task_id, "boom 2") == "failed"
        row = _task(conn, task_id)
        assert row["status"] == "failed" and row["attempts"] == 2 and row["last_error"] == "boom 2"

    def test_no_retry_fails_at_once(self, conn):
        task_id = _add(conn, "noop")
        claim_next(conn)
        assert mark_failed(conn, task_id, "bad payload", retry=False) == "failed"

    def test_a_stale_claim_is_requeued(self, conn):
        stale, live = _add(conn, "noop"), _add(conn, "noop")
        claim_next(conn)
        claim_next(conn)
        with conn.cursor() as cur:
            cur.execute("UPDATE task_queue SET locked_until = NOW() - INTERVAL 1 MINUTE WHERE id = %s", (stale,))
            assert requeue_stale(cur) == 1
        assert _task(conn, stale)["status"] == "pending"
        assert _task(conn, live)["status"] == "running"

    def test_a_stale_claim_with_attempts_used_up_fails(self, conn):
        task_id = _add(conn, "noop", max_attempts=1)
        claim_next(conn)
        with conn.cursor() as cur:
            cur.execute("UPDATE task_queue SET locked_until = NOW() - INTERVAL 1 MINUTE WHERE id = %s", (task_id,))
            assert requeue_stale(cur) == 1
        row = _task(conn, task_id)
        assert row["status"] == "failed" and row["completed_at"] is not None and row["locked_until"] is None
        assert "worker lost the task" in row["last_error"]
        assert claim_next(conn) is None


class TestWorkerRuns:
    """Through Worker.run_one: the three transactions, retries, bad tasks."""

    def test_a_handler_runs_and_its_work_commits_with_done(self, conn, worker, monkeypatch):
        def handler(task_conn, payload, should_stop):
            with task_conn.cursor() as cur:
                enqueue(cur, "follow_up", payload=payload)
        monkeypatch.setitem(task_handlers.HANDLERS, "test_ok", handler)
        task_id = _add(conn, "test_ok", payload={"n": 7})
        worker.connect()
        assert worker.run_one() == task_id
        assert _task(conn, task_id)["status"] == "done"
        with conn.cursor() as cur:
            cur.execute("SELECT payload FROM task_queue WHERE task_type = 'follow_up'")
            assert cur.fetchone() is not None

    def test_a_failing_handler_rolls_back_and_retries(self, conn, worker, monkeypatch):
        def handler(task_conn, payload, should_stop):
            with task_conn.cursor() as cur:
                enqueue(cur, "never_kept")
            raise ValueError("boom")
        monkeypatch.setitem(task_handlers.HANDLERS, "test_fail", handler)
        task_id = _add(conn, "test_fail")
        worker.connect()
        for attempt in (1, 2, 3):
            with conn.cursor() as cur:
                cur.execute("UPDATE task_queue SET scheduled_for = NOW() WHERE id = %s", (task_id,))
            assert worker.run_one() == task_id
            row = _task(conn, task_id)
            assert row["attempts"] == attempt and "ValueError: boom" in row["last_error"]
        assert row["status"] == "failed"
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM task_queue WHERE task_type = 'never_kept'")
            assert cur.fetchone()["n"] == 0
        assert worker.run_one() is None

    @pytest.mark.parametrize("code", [1213, 1205])
    def test_a_deadlock_or_lock_timeout_is_a_task_failure(self, conn, worker, monkeypatch, code):
        def handler(task_conn, payload, should_stop):
            raise pymysql.err.OperationalError(code, "lock trouble")
        monkeypatch.setitem(task_handlers.HANDLERS, "test_lock", handler)
        task_id = _add(conn, "test_lock")
        worker.connect()
        assert worker.run_one() == task_id   # not re-raised: the connection is fine
        row = _task(conn, task_id)
        assert row["status"] == "pending" and str(code) in row["last_error"]

    def test_a_server_constraint_error_is_a_task_failure(self, conn, worker, monkeypatch):
        # 4025 ER_CONSTRAINT_FAILED is a server code above 3000, not a lost connection
        def handler(task_conn, payload, should_stop):
            raise pymysql.err.OperationalError(4025, "CONSTRAINT failed")
        monkeypatch.setitem(task_handlers.HANDLERS, "test_check", handler)
        task_id = _add(conn, "test_check")
        worker.connect()
        assert worker.run_one() == task_id
        row = _task(conn, task_id)
        assert row["status"] == "pending" and "4025" in row["last_error"]

    def test_a_failed_rollback_logs_the_original_cause(self, conn, worker, monkeypatch, caplog):
        def handler(task_conn, payload, should_stop):
            raise pymysql.err.OperationalError(2013, "Lost connection original cause")
        monkeypatch.setitem(task_handlers.HANDLERS, "test_rb", handler)
        task_id = _add(conn, "test_rb")
        worker.connect()

        def broken_rollback():
            worker.conn.close()
            raise pymysql.err.Error(0, "")   # what a dead connection raises
        monkeypatch.setattr(worker.conn, "rollback", broken_rollback)
        with caplog.at_level("ERROR"), pytest.raises(pymysql.err.Error):
            worker.run_one()
        assert "original cause" in caplog.text
        assert _task(conn, task_id)["status"] == "running"

    def test_a_lost_connection_is_re_raised(self, conn, worker, monkeypatch):
        def handler(task_conn, payload, should_stop):
            raise pymysql.err.OperationalError(2013, "Lost connection to MySQL server")
        monkeypatch.setitem(task_handlers.HANDLERS, "test_lost", handler)
        task_id = _add(conn, "test_lost")
        worker.connect()
        with pytest.raises(pymysql.err.OperationalError):
            worker.run_one()
        assert _task(conn, task_id)["status"] == "running"   # left for requeue_stale

    def test_an_unknown_type_fails_without_stopping_the_worker(self, conn, worker, monkeypatch):
        monkeypatch.setitem(task_handlers.HANDLERS, "test_ok", lambda *_args: None)
        unknown, good = _add(conn, "no_such_task"), _add(conn, "test_ok")
        worker.connect()
        assert worker.run_one() == unknown
        row = _task(conn, unknown)
        assert row["status"] == "failed" and row["attempts"] == 1 and "Unknown task type" in row["last_error"]
        assert worker.run_one() == good
        assert _task(conn, good)["status"] == "done"

    def test_a_bad_payload_fails_at_once(self, conn, worker):
        task_id = _add(conn, "purge_access_log", payload={"days": 1})
        worker.connect()
        worker.run_one()
        row = _task(conn, task_id)
        assert row["status"] == "failed" and row["attempts"] == 1 and "takes no payload" in row["last_error"]
