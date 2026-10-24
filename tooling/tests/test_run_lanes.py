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


class TestWebkitServer:
    """S046: when the WebKit container is needed, and what is asked of Docker."""

    def test_a_full_run_needs_it(self):
        assert run_lanes.needs_webkit_server([], "")
        assert run_lanes.needs_webkit_server(["e2e/labels.spec.js"], "")

    def test_a_run_naming_phone_webkit_needs_it(self):
        assert run_lanes.needs_webkit_server(["--project=phone-webkit"], "")
        assert run_lanes.needs_webkit_server(["--project", "phone-webkit"], "")

    def test_a_run_without_phone_webkit_starts_none(self):
        assert not run_lanes.needs_webkit_server(["--project=desktop-chromium"], "")
        assert not run_lanes.needs_webkit_server(["--project=phone-chromium", "--project=desktop-chromium"], "")

    def test_project_forms_as_playwright_reads_them(self):
        needs = run_lanes.needs_webkit_server
        assert needs(["--project=phone-*"], "")                                  # wildcard: may match it
        assert needs(["--project=Phone-WebKit"], "")                             # case-insensitive
        assert needs(["--project", "phone-chromium", "phone-webkit"], "")        # variadic
        assert needs(["--project", "phone-chromium", "--project", "phone-webkit"], "")
        assert not needs(["--project", "phone-chromium", "desktop-chromium"], "")
        assert not needs(["--project", "Desktop-Chromium", "e2e/a.spec.js"], "")
        assert not needs(["--project=desktop-chromium,phone-webkit"], "")        # no comma split: one unknown name

    def test_named_projects_reads_only_playwrights_forms(self):
        assert run_lanes.named_projects(["--project=a", "--project", "b", "c", "--other", "d"]) == ["a", "b", "c"]
        assert run_lanes.named_projects(["-p", "a", "x.spec.js"]) == []
        assert run_lanes.named_projects(["--project=a,b"]) == ["a,b"]

    def test_lane_count_uses_the_same_parse(self):
        assert run_lanes.lane_count(["e2e/a.spec.js", "--project", "phone-chromium", "desktop-chromium"], 6) == 2

    def test_native_mode_is_read_case_insensitively(self, monkeypatch):
        monkeypatch.setenv("E2E_WEBKIT", "Native")
        assert not run_lanes.needs_webkit_server([], run_lanes.webkit_mode())

    def test_native_mode_starts_none(self):
        assert not run_lanes.needs_webkit_server([], "native")
        assert not run_lanes.needs_webkit_server(["--project=phone-webkit"], "native")

    def test_the_version_is_the_installed_playwright_test(self, tmp_path):
        package = tmp_path / "node_modules" / "@playwright" / "test"
        package.mkdir(parents=True)
        (package / "package.json").write_text('{"version": "9.8.7"}', encoding="utf-8")
        assert run_lanes.playwright_version(tmp_path) == "9.8.7"

    def test_the_installed_version_is_readable(self):
        assert run_lanes.playwright_version().count(".") == 2

    def test_docker_run_arguments(self):
        command = run_lanes.webkit_run_command("1.64.1")
        assert "mcr.microsoft.com/playwright:v1.64.1-noble" in command
        assert "playwright@1.64.1" in command
        assert command[command.index("-p") + 1] == "127.0.0.1:3999:3000"     # loopback only
        assert {"--rm", "--init"} <= set(command)
        assert command[command.index("--user") + 1] == "pwuser"
        assert "-d" not in command                                           # attached: the log is the output

    def test_every_failure_message_names_the_cause_and_both_ways_out(self):
        for cause, words in [("pull", "downloaded"), ("port", "Port 3999 is in use"),
                             ("name", "docker rm -f yantra-e2e-webkit"), ("timeout", "webkit.log")]:
            message = run_lanes.webkit_failure(cause)
            assert words in message
            assert "--project=phone-chromium --project=desktop-chromium" in message
            assert "E2E_WEBKIT=native" in message


class _Done:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class _Exited:
    """A docker run process that has already stopped."""
    def poll(self):
        return 1

    def wait(self):
        return 1


class TestWebkitStart:
    def _start(self, monkeypatch, tmp_path, docker):
        monkeypatch.setattr(run_lanes, "LANE_LOGS", tmp_path)
        monkeypatch.setattr(run_lanes, "WEBKIT_LOG", tmp_path / "webkit.log")
        monkeypatch.setattr(run_lanes, "_docker", docker)
        monkeypatch.setattr(run_lanes, "_port_in_use", lambda: False)
        monkeypatch.setattr(run_lanes.subprocess, "Popen", lambda *a, **k: _Exited())
        with run_lanes.webkit_server("1.64.1"):
            pass

    def test_a_container_that_stops_early_is_not_called_a_timeout(self, monkeypatch, tmp_path):
        try:
            self._start(monkeypatch, tmp_path, lambda *a, **k: _Done())
        except run_lanes.WebkitUnavailable as stop:
            message = str(stop)
        else:
            raise AssertionError("expected WebkitUnavailable")
        assert "did not start in" not in message
        assert "stopped before it was ready" in message and "webkit.log" in message
        assert "E2E_WEBKIT=native" in message

    def test_a_failed_cache_folder_hand_over_stops_the_run(self, monkeypatch, tmp_path):
        def docker(*args, **kwargs):
            return _Done(1, stderr="boom") if "chown" in args else _Done()
        try:
            self._start(monkeypatch, tmp_path, docker)
        except run_lanes.WebkitUnavailable as stop:
            message = str(stop)
        else:
            raise AssertionError("expected WebkitUnavailable")
        assert "cache" in message and "boom" in message and "E2E_WEBKIT=native" in message
