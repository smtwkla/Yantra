"""tooling/e2e/run_lanes.py: the levels, the lane plan, the lock and the lane summary line (S047),
the WebKit container (S046).  No Playwright and no database: the pure helpers only."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "e2e"))

import run_lanes  # noqa: E402

def test_lane_database_ends_in_e2e():
    assert run_lanes.lane_database(2) == "vel_yantra_lane2_e2e"


def test_summary_of_a_lane_log():
    log = "[1/9] …\n  1 failed\n    [phone-webkit] › e2e/x.spec.js:3:1 › y\n  8 passed (1.2m)\n"
    assert run_lanes.summary_of(log) == "1 failed, 8 passed"
    assert run_lanes.summary_of("crashed") == "no summary (see the log)"


def test_a_second_run_cannot_take_the_lock(tmp_path, monkeypatch):
    """The lock is exclusive: while one handle holds it, a second gets an OSError (and the run
    waits); once released, the second takes it."""
    lock_file = tmp_path / "e2e-run.lock"
    with run_lanes.one_run_at_a_time(lock_file):
        other = open(lock_file, "a+")
        try:
            try:
                run_lanes._lock(other)
                taken = True
            except OSError:
                taken = False
            assert not taken
        finally:
            other.close()
    other = open(lock_file, "a+")
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
        with pytest.raises(run_lanes.WebkitUnavailable) as stop:
            self._start(monkeypatch, tmp_path, lambda *a, **k: _Done())
        message = str(stop.value)
        assert "did not start in" not in message
        assert "stopped before it was ready" in message and "webkit.log" in message
        assert "E2E_WEBKIT=native" in message

    def test_a_failed_cache_folder_hand_over_stops_the_run(self, monkeypatch, tmp_path):
        def docker(*args, **kwargs):
            return _Done(1, stderr="boom") if "chown" in args else _Done()
        with pytest.raises(run_lanes.WebkitUnavailable) as stop:
            self._start(monkeypatch, tmp_path, docker)
        message = str(stop.value)
        assert "cache" in message and "boom" in message and "E2E_WEBKIT=native" in message

    def test_a_silent_hand_over_failure_message_starts_with_the_reason(self, monkeypatch, tmp_path):
        def docker(*args, **kwargs):
            return _Done(1) if "chown" in args else _Done()
        with pytest.raises(run_lanes.WebkitUnavailable) as stop:
            self._start(monkeypatch, tmp_path, docker)
        assert not str(stop.value).startswith("\n")


class TestLevels:
    """S047: --level=basic|normal|full; no flag is Normal; the level's projects only when none is named."""

    def test_no_flag_is_normal_and_the_flag_is_removed(self):
        assert run_lanes.read_level(["e2e/a.spec.js"]) == ("normal", ["e2e/a.spec.js"])
        assert run_lanes.read_level(["--level=full", "-g", "x"]) == ("full", ["-g", "x"])

    def test_an_unknown_level_is_refused(self):
        for args in (["--level=fast"], ["--level"], ["--level="]):
            with pytest.raises(run_lanes.Refused, match="Use --level=basic, normal or full."):
                run_lanes.read_level(args)

    def test_basic_is_the_smoke_tests_on_the_android_phone(self):
        args, env = run_lanes.expand_level("basic", [])
        assert args == ["--project=phone-chromium", "--grep", "@smoke"]
        assert env == {}

    def test_basic_refuses_a_grep(self):
        for grep in (["-g", "S044"], ["--grep", "x"], ["--grep=x"], ["--grep-invert", "x"], ["--grep-invert=x"]):
            with pytest.raises(run_lanes.Refused, match="Basic runs the smoke tests only"):
                run_lanes.expand_level("basic", grep)

    def test_normal_is_two_projects_with_the_device_filter(self):
        args, env = run_lanes.expand_level("normal", ["e2e/labels.spec.js"])
        assert args == ["--project=phone-chromium", "--project=desktop-chromium", "e2e/labels.spec.js"]
        assert env == {"E2E_LEVEL": "normal"}

    def test_an_explicit_project_wins_and_gets_no_device_filter(self):
        """BR1-01: --project=desktop-chromium at Normal runs every matching test there, not zero."""
        given = ["--project=desktop-chromium", "e2e/equipment.spec.js", "-g", "S044"]
        assert run_lanes.expand_level("normal", given) == (given, {})
        assert run_lanes.expand_level("normal", ["--project", "phone-chromium"]) == (["--project", "phone-chromium"], {})

    def test_full_adds_nothing(self):
        assert run_lanes.expand_level("full", ["e2e/a.spec.js"]) == (["e2e/a.spec.js"], {})

    def test_only_full_starts_the_webkit_container(self):
        def needs(level):
            return run_lanes.needs_webkit_server(run_lanes.expand_level(level, [])[0], "")
        assert (needs("basic"), needs("normal"), needs("full")) == (False, False, True)

    def test_a_refusal_stops_main_with_its_line(self, monkeypatch, capsys):
        monkeypatch.setattr(run_lanes, "main_scratch", lambda: pytest.fail("refused before the lock"))
        assert run_lanes.main(["--level=basic", "-g", "S044"]) == 1
        assert capsys.readouterr().out.strip() == run_lanes.BASIC_GREP


    def test_an_inherited_level_does_not_filter_an_explicit_project(self, monkeypatch, tmp_path):
        """CR1-05: E2E_LEVEL=normal left in the caller's shell must not reach playwright.config.js
        when the level did not choose the projects."""
        monkeypatch.setenv("E2E_LEVEL", "normal")
        monkeypatch.setattr(run_lanes, "main_scratch", lambda: tmp_path)
        seen = {}

        def fake_run(args, wanted, timings_file):
            seen["level"] = run_lanes.os.environ.get("E2E_LEVEL")
            return 0
        monkeypatch.setattr(run_lanes, "run", fake_run)
        assert run_lanes.main(["--project=desktop-chromium", "e2e/a.spec.js"]) == 0
        assert seen["level"] is None

    def test_the_normal_level_still_sets_the_device_filter(self, monkeypatch, tmp_path):
        monkeypatch.delenv("E2E_LEVEL", raising=False)
        monkeypatch.setattr(run_lanes, "main_scratch", lambda: tmp_path)
        seen = {}
        monkeypatch.setattr(run_lanes, "run", lambda *a: seen.update(level=run_lanes.os.environ.get("E2E_LEVEL")) or 0)
        assert run_lanes.main(["e2e/a.spec.js"]) == 0
        assert seen["level"] == "normal"
        monkeypatch.delenv("E2E_LEVEL", raising=False)


class TestListGroups:
    """CR1-01: a spec file that cannot load makes Playwright list no test; say why."""

    def _listed(self, monkeypatch, done):
        monkeypatch.setattr(run_lanes.subprocess, "run", lambda *a, **k: done)

    def test_a_load_error_is_returned_with_its_message(self, monkeypatch):
        report = {"suites": [], "errors": [{"message": "SyntaxError: Unexpected token ';' in bad.spec.js"}]}
        self._listed(monkeypatch, _Done(1, stdout=json.dumps(report)))
        groups, error = run_lanes.list_groups([])
        assert groups is None
        assert "SyntaxError: Unexpected token ';' in bad.spec.js" in error

    def test_a_failed_list_with_no_message_still_reports_the_exit_code(self, monkeypatch):
        self._listed(monkeypatch, _Done(1, stdout=json.dumps({"suites": [], "errors": []})))
        groups, error = run_lanes.list_groups([])
        assert groups is None
        assert "exit code 1" in error

    def test_a_good_list_returns_the_groups(self, monkeypatch):
        report = _report(("phone-chromium", "a.spec.js", [1000, 2000]))
        report["errors"] = []
        self._listed(monkeypatch, _Done(0, stdout=json.dumps(report)))
        assert run_lanes.list_groups([]) == ({("phone-chromium", "a.spec.js"): 2}, None)


    def test_the_list_command_passes_with_no_tests(self, monkeypatch):
        """CR2-01: without it Playwright exits 1 on an empty list and the 'No test matches' line is lost."""
        seen = {}

        def fake_run(command, *a, **k):
            seen["command"] = command
            return _Done(0, stdout=json.dumps({"suites": [], "errors": []}))
        monkeypatch.setattr(run_lanes.subprocess, "run", fake_run)
        assert run_lanes.list_groups(["-g", "nothing"]) == ({}, None)
        assert "--list" in seen["command"]
        assert "--pass-with-no-tests" in seen["command"]


class TestLaneArguments:
    def test_split_keeps_option_values_and_drops_projects(self):
        args = ["--project=phone-chromium", "--project", "desktop-chromium", "-g", "S044", "e2e/a.spec.js",
                "--repeat-each", "3", "--timeout", "5000", "--retries=1", "--grep-invert", "slow", "e2e/b.spec.js"]
        positional, others = run_lanes.split_args(args)
        assert positional == ["e2e/a.spec.js", "e2e/b.spec.js"]
        assert others == ["-g", "S044", "--repeat-each", "3", "--timeout", "5000", "--retries=1", "--grep-invert", "slow"]

    def test_names_after_a_bare_project_are_projects(self):
        """Playwright's --project is variadic: what follows it, up to the next option, is a project name."""
        positional, others = run_lanes.split_args(["e2e/a.spec.js", "--project", "phone-chromium", "desktop-chromium"])
        assert positional == ["e2e/a.spec.js"]
        assert others == []

    def test_the_lane_leaves_out_the_shard_and_passes_the_rest(self):
        others = ["-g", "S044", "--shard=1/3", "--shard", "2/3", "--grep", "@smoke", "--repeat-each", "2", "--retries", "1"]
        assert run_lanes.lane_arguments(others) == ["-g", "S044", "--grep", "@smoke", "--repeat-each", "2", "--retries", "1"]

    def test_plain_spec_files_are_planned_and_a_line_falls_back(self):
        assert run_lanes.plannable([])
        assert run_lanes.plannable(["e2e/labels.spec.js", "readings.spec.js", "e2e\\me.spec.js"])
        assert not run_lanes.plannable(["e2e/labels.spec.js:42"])
        assert not run_lanes.plannable(["labels"])            # a filter, not a spec file


def _report(*groups):
    """A Playwright JSON report: groups of (project, file, [a duration in ms, or None for no result])."""
    by_file = {}
    for project, file, durations in groups:
        spec_tests = by_file.setdefault(file, [])
        for duration in durations:
            results = [] if duration is None else [{"duration": duration, "status": "passed"}]
            spec_tests.append({"projectName": project, "results": results})
    # each file's tests split over a describe block, to cover the nested suites
    return {"suites": [{"file": file, "specs": [{"file": file, "tests": tests[:1]}],
                        "suites": [{"specs": [{"file": file, "tests": tests[1:]}]}]}
                       for file, tests in by_file.items()]}


class TestPlan:
    def test_groups_per_project_and_file_from_nested_suites(self):
        report = _report(("phone-chromium", "a.spec.js", [None, None, None]), ("desktop-chromium", "a.spec.js", [None]),
                         ("phone-chromium", "b.spec.js", [None]))
        assert run_lanes.groups_of(report) == {("phone-chromium", "a.spec.js"): 3, ("desktop-chromium", "a.spec.js"): 1,
                                               ("phone-chromium", "b.spec.js"): 1}

    def test_the_weight_is_the_tests_now_times_the_measured_seconds_per_test(self):
        """BR2-02: desktop × readings ran 32 tests in 96 s at Full; at Normal it lists 1 test."""
        timings = {"desktop-chromium readings.spec.js": {"tests": 32, "seconds": 96.0}}
        weights = run_lanes.group_weights({("desktop-chromium", "readings.spec.js"): 1}, timings)
        assert weights == {("desktop-chromium", "readings.spec.js"): 3.0}

    def test_an_unmeasured_group_takes_the_mean_per_test(self):
        timings = {"phone-chromium a.spec.js": {"tests": 10, "seconds": 40.0},
                   "phone-chromium b.spec.js": {"tests": 10, "seconds": 20.0}}
        weights = run_lanes.group_weights({("phone-chromium", "new.spec.js"): 4}, timings)
        assert weights == {("phone-chromium", "new.spec.js"): 12.0}           # 60 s / 20 tests × 4

    def test_nothing_measured_is_three_seconds_a_test(self):
        assert run_lanes.group_weights({("p", "a.spec.js"): 5}, {}) == {("p", "a.spec.js"): 15}

    def test_lpt_packs_longest_first_into_the_least_loaded_lane(self):
        weights = {("p", "a"): 90, ("p", "b"): 60, ("p", "c"): 50, ("p", "d"): 40, ("p", "e"): 30, ("p", "f"): 20}
        plan = run_lanes.plan_lanes(weights, 3)
        # a, b, c open the lanes; d joins c (50), e joins b (60), f joins the first of three at 90
        assert plan == [(110, [("p", "a"), ("p", "f")]), (90, [("p", "b"), ("p", "e")]), (90, [("p", "c"), ("p", "d")])]

    def test_a_few_large_groups_still_give_even_lanes(self):
        """S046's fault: --shard by count left half the lanes idle; by weight the lanes come out within 20 %."""
        sizes = [96, 60, 55, 50, 45, 40, 30, 25, 20, 15, 10, 10, 5, 5]
        totals = [total for total, _ in run_lanes.plan_lanes({("p", f"s{i}"): w for i, w in enumerate(sizes)}, 6)]
        assert max(totals) <= 1.2 * min(totals) or max(totals) == max(sizes)

    def test_more_lanes_than_groups(self):
        plan = run_lanes.plan_lanes({("p", "a"): 5, ("p", "b"): 3}, 6)
        assert [groups for _, groups in plan] == [[("p", "a")], [("p", "b")]]

    def test_the_plan_line_and_the_lane_env(self):
        groups = [("phone-chromium", "readings.spec.js"), ("desktop-chromium", "me.spec.js"),
                  ("phone-chromium", "me.spec.js")]
        assert run_lanes.plan_line(1, 84.4, groups) == (
            "lane 1 plan: 3 groups, 84 s (phone-chromium readings.spec.js, desktop-chromium me.spec.js, "
            "phone-chromium me.spec.js)")
        assert json.loads(run_lanes.lane_plan_env(groups)) == {
            "phone-chromium": ["readings.spec.js", "me.spec.js"], "desktop-chromium": ["me.spec.js"]}


class TestTimings:
    def test_measured_counts_the_tests_with_a_result_and_sums_seconds(self):
        report = _report(("phone-chromium", "a.spec.js", [1500, 2500, None]), ("phone-chromium", "b.spec.js", [0]))
        assert run_lanes.measured_groups(report) == {("phone-chromium", "a.spec.js"): (2, 4.0),
                                                     ("phone-chromium", "b.spec.js"): (1, 0.0)}

    def test_a_failed_test_is_not_measured(self):
        """A dead stack fails each test at its timeout: that time must not plan the next run."""
        report = _report(("phone-chromium", "a.spec.js", [1000, 11000]), ("phone-chromium", "b.spec.js", [11000]))
        tests = report["suites"][0]["suites"][0]["specs"][0]["tests"]
        tests[0]["results"][0]["status"] = "failed"                      # a.spec.js's second test
        report["suites"][1]["specs"][0]["tests"][0]["results"][0]["status"] = "timedOut"
        assert run_lanes.measured_groups(report) == {("phone-chromium", "a.spec.js"): (1, 1.0)}

    def test_the_update_replaces_the_groups_that_ran_and_keeps_the_others(self):
        old = {"phone-chromium a.spec.js": {"tests": 9, "seconds": 99.0},
               "phone-webkit a.spec.js": {"tests": 3, "seconds": 9.0}}
        new = run_lanes.updated_timings(old, {("phone-chromium", "a.spec.js"): (2, 4.04)})
        assert new == {"phone-chromium a.spec.js": {"tests": 2, "seconds": 4.0},
                       "phone-webkit a.spec.js": {"tests": 3, "seconds": 9.0}}
        assert old["phone-chromium a.spec.js"]["tests"] == 9                   # not changed in place

    def test_a_missing_or_broken_file_is_no_timings(self, tmp_path):
        assert run_lanes.read_json(tmp_path / "none.json") == {}
        (tmp_path / "bad.json").write_text("{", encoding="utf-8")
        assert run_lanes.read_json(tmp_path / "bad.json") == {}


class TestMainScratch:
    """S047 § 1.6: the lock and the timings in the main working folder, found through git's common dir."""

    def test_from_this_repo_it_is_the_working_folders_scratch(self):
        common = run_lanes.subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                          cwd=run_lanes.ROOT, capture_output=True, text=True).stdout.strip()
        assert run_lanes.main_scratch() == Path(common).parent / "scratch"

    def test_a_worktree_gets_the_main_folders(self, monkeypatch, tmp_path):
        monkeypatch.setattr(run_lanes.subprocess, "run", lambda *a, **k: _Done(0, stdout="C:/Users/x/Yantra/.git\n"))
        assert run_lanes.main_scratch(tmp_path / "worktree") == Path("C:/Users/x/Yantra/scratch")

    def test_no_git_falls_back_to_its_own_scratch_with_a_line(self, monkeypatch, tmp_path, capsys):
        def no_git(*a, **k):
            raise FileNotFoundError("git")
        monkeypatch.setattr(run_lanes.subprocess, "run", no_git)
        assert run_lanes.main_scratch(tmp_path) == tmp_path / "scratch"
        lock = tmp_path / "scratch" / "e2e-run.lock"
        assert capsys.readouterr().out.strip() == f"Git did not find the main working folder, so the e2e lock is in {lock}."

    def test_not_a_repository_falls_back(self, monkeypatch, tmp_path):
        monkeypatch.setattr(run_lanes.subprocess, "run", lambda *a, **k: _Done(128, stderr="not a git repository"))
        assert run_lanes.main_scratch(tmp_path) == tmp_path / "scratch"


class TestRun:
    """run() with Playwright, the databases and the merge replaced: what each lane is given."""

    def _stub(self, monkeypatch, tmp_path, groups, results):
        seen = {}
        monkeypatch.setattr(run_lanes, "list_groups", lambda args: (groups, None))
        monkeypatch.setattr(run_lanes, "create_databases", lambda n: None)

        def lanes(lane_runs):
            seen["lanes"] = lane_runs
            return False
        monkeypatch.setattr(run_lanes, "run_lanes", lanes)
        monkeypatch.setattr(run_lanes, "merge", lambda: True)
        monkeypatch.setattr(run_lanes, "RESULTS_JSON", tmp_path / "results.json")
        (tmp_path / "results.json").write_text(json.dumps(results), encoding="utf-8")
        return seen

    def test_no_test_found_is_exit_1_with_its_line(self, monkeypatch, capsys, tmp_path):
        monkeypatch.setattr(run_lanes, "list_groups", lambda args: ({}, None))
        monkeypatch.setattr(run_lanes, "create_databases", lambda n: pytest.fail("no lanes for no tests"))
        assert run_lanes.run(["--project=desktop-chromium", "-g", "nothing"], 6, tmp_path / "t.json") == 1
        assert "No test matches these arguments: --project=desktop-chromium -g nothing." in capsys.readouterr().out

    def test_a_list_that_fails_is_exit_1_with_its_output(self, monkeypatch, capsys, tmp_path):
        monkeypatch.setattr(run_lanes, "list_groups", lambda args: (None, "SyntaxError in playwright.config.js"))
        assert run_lanes.run([], 6, tmp_path / "t.json") == 1
        assert "SyntaxError in playwright.config.js" in capsys.readouterr().out

    def test_planned_lanes_get_their_plan_and_no_pass_with_no_tests(self, monkeypatch, tmp_path):
        groups = {("phone-chromium", "a.spec.js"): 2, ("desktop-chromium", "a.spec.js"): 1}
        seen = self._stub(monkeypatch, tmp_path, groups, _report(("phone-chromium", "a.spec.js", [2000])))
        code = run_lanes.run(["--project=phone-chromium", "e2e/a.spec.js", "-g", "S0"], 6, tmp_path / "timings.json")
        assert code == 0
        assert [args for args, _env in seen["lanes"]] == [["-g", "S0"], ["-g", "S0"]]
        assert sorted(env["E2E_LANE_PLAN"] for _args, env in seen["lanes"]) == [
            '{"desktop-chromium": ["a.spec.js"]}', '{"phone-chromium": ["a.spec.js"]}']
        assert json.loads((tmp_path / "timings.json").read_text(encoding="utf-8")) == {
            "phone-chromium a.spec.js": {"tests": 1, "seconds": 2.0}}

    def test_a_test_named_by_line_falls_back_to_shard(self, monkeypatch, tmp_path, capsys):
        groups = {("phone-chromium", "a.spec.js"): 1, ("desktop-chromium", "a.spec.js"): 1}
        seen = self._stub(monkeypatch, tmp_path, groups, _report(("phone-chromium", "a.spec.js", [1000])))
        assert run_lanes.run(["e2e/a.spec.js:42"], 6, tmp_path / "t.json") == 0
        assert run_lanes.SHARD_FALLBACK in capsys.readouterr().out
        assert [args for args, _env in seen["lanes"]] == [["--shard=1/2", "--pass-with-no-tests", "e2e/a.spec.js:42"],
                                                         ["--shard=2/2", "--pass-with-no-tests", "e2e/a.spec.js:42"]]

    def test_a_run_where_no_test_ran_is_exit_1(self, monkeypatch, tmp_path, capsys):
        groups = {("phone-chromium", "a.spec.js"): 1, ("desktop-chromium", "a.spec.js"): 1}
        self._stub(monkeypatch, tmp_path, groups, {"suites": []})
        assert run_lanes.run(["e2e/a.spec.js:42"], 6, tmp_path / "t.json") == 1
        assert "No test ran." in capsys.readouterr().out

    def test_a_run_whose_tests_all_failed_is_a_failure_not_no_test(self, monkeypatch, tmp_path, capsys):
        groups = {("phone-chromium", "a.spec.js"): 1, ("desktop-chromium", "a.spec.js"): 1}
        report = _report(("phone-chromium", "a.spec.js", [11000]))
        report["suites"][0]["specs"][0]["tests"][0]["results"][0]["status"] = "failed"
        seen = self._stub(monkeypatch, tmp_path, groups, report)
        monkeypatch.setattr(run_lanes, "run_lanes", lambda lane_runs: True)      # a lane failed
        assert run_lanes.run(["e2e/a.spec.js"], 6, tmp_path / "t.json") == 1
        assert "No test ran." not in capsys.readouterr().out
        assert not (tmp_path / "t.json").exists()                                 # nothing measured
        assert seen == {}

    def test_one_group_runs_the_single_stack(self, monkeypatch, tmp_path):
        monkeypatch.setattr(run_lanes, "list_groups", lambda args: ({("phone-chromium", "a.spec.js"): 3}, None))
        monkeypatch.setattr(run_lanes, "single_stack", lambda args: 0)
        monkeypatch.setattr(run_lanes, "create_databases", lambda n: pytest.fail("no lanes for one group"))
        assert run_lanes.run(["e2e/a.spec.js"], 6, tmp_path / "t.json") == 0
