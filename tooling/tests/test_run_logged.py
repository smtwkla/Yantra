"""tooling/run_logged.py: the summary line of a test suite's run, and the log and exit code of a
real (tiny) command."""

import sys

import run_logged


class TestCounts:
    def test_pytest_last_line(self):
        out = "....\n========= 2 failed, 2275 passed, 3 skipped in 41.2s =========\n"
        assert run_logged.counts_of(out) == "2 failed, 2275 passed, 3 skipped"

    def test_vitest_tests_line_wins_over_files_line(self):
        out = " Test Files  14 passed (14)\n      Tests  114 passed (114)\n   Duration  10.29s\n"
        assert run_logged.counts_of(out) == "114 passed"

    def test_colour_codes_are_ignored(self):
        assert run_logged.counts_of("\x1b[32m3 passed\x1b[0m in 1s") == "3 passed"

    def test_no_tests_ran(self):
        assert run_logged.counts_of("bringing up nodes...\n\nno tests ran in 4.35s\n") == "no tests ran"

    def test_none_found(self):
        assert run_logged.counts_of("ImportError: no module\n") == "no test counts found"


class TestSummaryLine:
    def test_passed(self):
        line = run_logged.summary_line("backend", 0, 41.6, "5 passed in 1s", "C:/x/backend-tests.log")
        assert line == "== backend: PASSED in 42 s: 5 passed (log: C:/x/backend-tests.log)"

    def test_failed_names_the_exit_code(self):
        line = run_logged.summary_line("frontend", 1, 3, "1 failed", "f.log")
        assert line.startswith("== frontend: FAILED (exit 1) in 3 s: 1 failed")


class TestRun:
    def test_logs_the_output_appends_the_summary_and_keeps_the_exit_code(self, tmp_path, monkeypatch, capsys):
        summary = tmp_path / "summary.txt"
        monkeypatch.setenv("TEST_SUMMARY_FILE", str(summary))
        log = tmp_path / "logs" / "x.log"
        code = run_logged.run("x", log, [sys.executable, "-c", "print('7 passed'); raise SystemExit(3)"])
        assert code == 3
        assert log.read_text(encoding="utf-8") == "7 passed\n"
        assert "7 passed" in capsys.readouterr().out
        assert summary.read_text(encoding="utf-8").startswith("== x: FAILED (exit 3) in ")

    def test_usage(self):
        assert run_logged.main(["x", "log"]) == 2
