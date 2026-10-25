"""tooling/common/preflight_stamp.py and its use in release.py (S049 § 1.3, § 1.5).

The pure core (stamp_text, parse, check, carry_text) is tested with plain data; the shell with
git stubbed; release.py's step 2 and 4 with its `run` faked, so no command runs, no version is
bumped and nothing is committed."""

import contextlib
import importlib.util
import subprocess
import sys
import time
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

COMMON = Path(__file__).resolve().parent.parent / "common"
sys.path.insert(0, str(COMMON))  # as release.py finds its sibling (conftest adds only tooling/)

import preflight_stamp as ps  # noqa: E402

SHA = "a" * 40
OTHER_SHA = "b" * 40
CMD = r"tooling\release-tests.bat"
MACHINE = "KLA-LAPTOP"
TESTED_AT = datetime(2026, 10, 25, 14, 30, tzinfo=ps.IST)


def a_stamp(sha=SHA, tested_at=TESTED_AT, cmd=CMD, machine=MACHINE, **kwargs):
    return ps.stamp_text(sha, tested_at, cmd, machine, "KLA", **kwargs)


def checked(note, now=TESTED_AT + timedelta(hours=1), sha=SHA, cmd=CMD, machine=MACHINE):
    return ps.check(note, sha, cmd, now, machine)


# --- stamp_text and parse ------------------------------------------------------------------

def test_stamp_text_round_trips_through_parse():
    text = a_stamp(summary=["== backend: PASSED", "== frontend: PASSED"], carried_from=OTHER_SHA)
    fields = ps.parse(text)
    assert fields["preflight"] == "1"
    assert fields["result"] == "passed"
    assert fields["commit"] == SHA
    assert fields["tested_at"] == "2026-10-25T14:30:00+05:30"
    assert fields["test_cmd"] == CMD
    assert fields["machine"] == MACHINE
    assert fields["by"] == "KLA"
    assert fields["carried_from"] == OTHER_SHA
    assert fields["summary"] == ["== backend: PASSED", "== frontend: PASSED"]


def test_stamp_text_keeps_the_last_ten_summary_lines():
    fields = ps.parse(a_stamp(summary=[f"line {n}" for n in range(15)]))
    assert fields["summary"] == [f"line {n}" for n in range(5, 15)]


def test_stamp_text_writes_tested_at_in_ist():
    utc_time = datetime(2026, 10, 25, 9, 0, tzinfo=ps.timezone.utc)
    assert "tested_at: 2026-10-25T14:30:00+05:30" in a_stamp(tested_at=utc_time)


def test_parse_refuses_text_that_is_no_stamp():
    assert ps.parse(None) is None
    assert ps.parse("") is None
    assert ps.parse("just some words\nmore words") is None
    assert ps.parse("result: passed\n") is None  # no preflight, no commit


# --- check: every rule of § 1.3 --------------------------------------------------------------

def test_check_accepts_a_fresh_stamp_and_says_so_in_ist():
    valid, reason = checked(a_stamp())
    assert valid
    assert reason == ("Tests passed in pre-flight on 25-10-2026 14:30 for aaaaaaa. "
                      "The release does not run them again.")


def test_check_without_a_note():
    assert checked(None) == (False, "No pre-flight stamp for aaaaaaa. The tests run now.")


def test_check_garbled_text():
    assert checked("@@@ not a stamp") == (
        False, "The pre-flight stamp of aaaaaaa cannot be read. The tests run now.")


def test_check_unknown_version():
    note = a_stamp().replace("preflight: 1", "preflight: 2")
    assert checked(note) == (False, "The pre-flight stamp of aaaaaaa cannot be read. The tests run now.")


def test_check_unreadable_time():
    note = a_stamp().replace("2026-10-25T14:30:00+05:30", "yesterday")
    assert not checked(note)[0]


def test_check_result_failed():
    note = a_stamp().replace("result: passed", "result: failed")
    assert checked(note) == (
        False, "The pre-flight stamp of aaaaaaa does not record a pass. The tests run now.")


def test_check_wrong_sha():
    assert checked(a_stamp(sha=OTHER_SHA)) == (
        False, "The pre-flight stamp on aaaaaaa names another commit. The tests run now.")


def test_check_one_minute_before_168_hours_is_valid():
    assert checked(a_stamp(), now=TESTED_AT + timedelta(hours=168) - timedelta(minutes=1))[0]


def test_check_one_minute_past_168_hours_is_too_old():
    valid, reason = checked(a_stamp(), now=TESTED_AT + timedelta(hours=168, minutes=1))
    assert not valid
    assert reason == ("The pre-flight stamp of aaaaaaa is more than 7 days old; a stamp is valid "
                      "for 7 days. The tests run now.")


def test_check_a_stamp_from_the_future_is_not_valid():
    """CR1-04: a clock that was wrong at stamp time must not lengthen the stamp's life."""
    too_far = TESTED_AT - ps.CLOCK_SKEW - timedelta(minutes=1)
    assert checked(a_stamp(), now=too_far) == (
        False, "The pre-flight stamp of aaaaaaa is dated later than now; this computer's clock "
               "may have been wrong. The tests run now.")


def test_check_tolerates_a_small_clock_skew():
    assert checked(a_stamp(), now=TESTED_AT - ps.CLOCK_SKEW + timedelta(minutes=1))[0]


def test_check_names_the_age_in_days():
    reason = checked(a_stamp(), now=TESTED_AT + timedelta(days=9, hours=2))[1]
    assert reason == ("The pre-flight stamp of aaaaaaa is 9 days old; a stamp is valid for 7 days. "
                      "The tests run now.")


def test_check_another_test_command():
    assert checked(a_stamp(cmd=r"tooling\run-tests.bat")) == (
        False, "The pre-flight stamp of aaaaaaa was made with another test command. The tests run now.")


def test_check_compares_the_command_exactly():
    assert not checked(a_stamp(cmd="tooling/release-tests.bat"))[0]


def test_check_another_machine():
    assert checked(a_stamp(machine="OTHER-PC")) == (
        False, "The pre-flight stamp of aaaaaaa was made on another computer. The tests run now.")


# --- carry_text ------------------------------------------------------------------------------

def carried(parent_note, changed):
    return ps.carry_text(parent_note, OTHER_SHA, changed, SHA, CMD,
                         TESTED_AT + timedelta(hours=1), MACHINE)


def test_carry_text_when_only_version_changed():
    text = carried(a_stamp(sha=OTHER_SHA, summary=["green"]), ["VERSION"])
    fields = ps.parse(text)
    assert fields["commit"] == SHA
    assert fields["carried_from"] == OTHER_SHA
    assert fields["tested_at"] == "2026-10-25T14:30:00+05:30"  # expires with the original
    assert fields["summary"] == ["green"]
    assert checked(text)[0]


def test_carry_text_not_when_other_files_changed():
    assert carried(a_stamp(sha=OTHER_SHA), ["VERSION", "pyproject.toml"]) is None


def test_carry_text_not_when_nothing_changed():
    assert carried(a_stamp(sha=OTHER_SHA), []) is None


def test_carry_text_not_from_an_invalid_parent_note():
    assert carried(a_stamp(sha=OTHER_SHA, cmd="pytest"), ["VERSION"]) is None
    assert carried(a_stamp(sha=SHA), ["VERSION"]) is None  # names the release, not the parent
    assert carried(None, ["VERSION"]) is None


# --- the shell, git stubbed --------------------------------------------------------------------

class FakeGit:
    """Answers `_git(*args)` from a dict of the first two args; records every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        for prefix, (code, out) in self.answers.items():
            if args[:len(prefix)] == prefix:
                return subprocess.CompletedProcess(args, code, out, "fatal: stub" if code else "")
        return subprocess.CompletedProcess(args, 1, "", "fatal: not stubbed")


def raising(*_args):
    raise RuntimeError("git exploded")


@pytest.fixture
def this_machine(monkeypatch):
    monkeypatch.setattr(ps, "machine_name", lambda: MACHINE)
    monkeypatch.setattr(ps, "now_ist", lambda: TESTED_AT + timedelta(hours=1))


def test_read_is_none_when_git_finds_no_note(monkeypatch):
    monkeypatch.setattr(ps, "_git", FakeGit({("notes",): (1, "")}))
    assert ps.read(SHA) is None


def test_release_gate_valid(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", FakeGit({("rev-parse", "HEAD"): (0, SHA + "\n"),
                                             ("notes",): (0, a_stamp())}))
    assert ps.release_gate(CMD)[0]


def test_release_gate_without_a_note(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", FakeGit({("rev-parse", "HEAD"): (0, SHA + "\n"),
                                             ("notes",): (1, "")}))
    assert ps.release_gate(CMD) == (False, "No pre-flight stamp for aaaaaaa. The tests run now.")


def test_release_gate_when_git_cannot_read_head(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", FakeGit({}))
    valid, reason = ps.release_gate(CMD)
    assert not valid and reason.endswith("The tests run now.")


def test_release_gate_never_raises(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", raising)
    monkeypatch.setattr(ps, "head_sha", lambda: SHA)
    monkeypatch.setattr(ps, "read", raising)
    valid, reason = ps.release_gate(CMD)
    assert not valid
    assert reason == "The pre-flight stamp could not be checked: git exploded. The tests run now."


def test_write_adds_the_note_with_a_file(monkeypatch, this_machine):
    seen = {}

    def fake(*args):
        if args[:2] == ("config", "user.name"):
            return subprocess.CompletedProcess(args, 0, "KLA\n", "")
        seen["args"] = args
        seen["text"] = Path(args[-2]).read_text(encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(ps, "_git", fake)
    assert ps.write(SHA, CMD, TESTED_AT, ["all green"]) is None
    assert seen["args"][:5] == ("notes", "--ref=preflight", "add", "-f", "-F")
    assert seen["args"][-1] == SHA
    assert ps.check(seen["text"], SHA, CMD, TESTED_AT, MACHINE)[0]
    assert not Path(seen["args"][-2]).exists()  # the temporary file is gone


def test_write_returns_gits_message(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", FakeGit({("config",): (0, "KLA"), ("notes",): (1, "")}))
    assert ps.write(SHA, CMD) == "fatal: stub"


def test_write_never_raises(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", raising)
    assert ps.write(SHA, CMD) == "git exploded"
    assert ps.write(None, CMD) == "the commit is not known"


def test_remove_takes_the_stamp_off(monkeypatch):
    git = FakeGit({("notes", "--ref=preflight", "show"): (0, a_stamp()),
                   ("notes", "--ref=preflight", "remove"): (0, "")})
    monkeypatch.setattr(ps, "_git", git)
    assert ps.remove(SHA) == (True, None)
    assert ("notes", "--ref=preflight", "remove", "--ignore-missing", SHA) in git.calls


def test_remove_when_there_is_no_stamp(monkeypatch):
    git = FakeGit({("notes", "--ref=preflight", "show"): (1, ""),
                   ("notes", "--ref=preflight", "remove"): (0, "")})
    monkeypatch.setattr(ps, "_git", git)
    assert ps.remove(SHA) == (False, None)


def test_remove_returns_gits_message(monkeypatch):
    monkeypatch.setattr(ps, "_git", FakeGit({("notes", "--ref=preflight", "show"): (0, a_stamp()),
                                             ("notes", "--ref=preflight", "remove"): (1, "")}))
    assert ps.remove(SHA) == (False, "fatal: stub")


def test_remove_never_raises(monkeypatch):
    monkeypatch.setattr(ps, "_git", raising)
    assert ps.remove(SHA) == (False, "git exploded")


def test_carry_writes_the_carried_stamp(monkeypatch, this_machine):
    written = {}
    monkeypatch.setattr(ps, "_git", FakeGit({("rev-parse",): (0, OTHER_SHA + "\n"),
                                             ("diff",): (0, "VERSION\n"),
                                             ("notes",): (0, a_stamp(sha=OTHER_SHA))}))
    monkeypatch.setattr(ps, "_add_note", lambda sha, text: written.update(sha=sha, text=text))
    assert ps.carry(SHA, CMD) == "The pre-flight stamp of bbbbbbb is carried to the release commit aaaaaaa."
    assert written["sha"] == SHA
    assert ps.parse(written["text"])["carried_from"] == OTHER_SHA


def test_carry_nothing_when_more_than_version_changed(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", FakeGit({("rev-parse",): (0, OTHER_SHA + "\n"),
                                             ("diff",): (0, "VERSION\npyproject.toml\n"),
                                             ("notes",): (0, a_stamp(sha=OTHER_SHA))}))
    monkeypatch.setattr(ps, "_add_note", lambda *a: pytest.fail("no note may be written"))
    assert ps.carry(SHA, CMD) is None


def test_carry_never_raises(monkeypatch, this_machine):
    monkeypatch.setattr(ps, "_git", raising)
    assert ps.carry(SHA, CMD) == "WARNING: the pre-flight stamp was not carried: git exploded"


def test_preflight_running_sees_a_lock_held_elsewhere(monkeypatch, tmp_path):
    lock = tmp_path / "scratch" / ps.LOCK_NAME
    monkeypatch.setattr(ps, "lock_path", lambda: lock)
    assert not ps.preflight_running()  # no lock file: no pre-flight ever ran
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time; sys.path.insert(0, sys.argv[1]); import preflight_stamp as ps; "
         "from pathlib import Path\n"
         "with ps.held_lock(Path(sys.argv[2])) as got:\n"
         "    print(got, flush=True); time.sleep(30)",
         str(COMMON), str(lock)],
        stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "True"
        assert ps.preflight_running()
    finally:
        holder.kill()
        holder.wait()
    # Windows frees a killed process's lock a moment after it exits.
    deadline = time.monotonic() + 10
    while ps.preflight_running() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not ps.preflight_running()


def test_release_lock_is_held_inside_and_refuses_a_preflight(monkeypatch, tmp_path):
    lock = tmp_path / "scratch" / ps.LOCK_NAME
    monkeypatch.setattr(ps, "lock_path", lambda: lock)
    with ps.release_lock() as (got, error):
        assert (got, error) == (True, None)
        probe = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import preflight_stamp as ps; "
             "from pathlib import Path\n"
             "with ps.held_lock(Path(sys.argv[2])) as got: print(got)",
             str(COMMON), str(lock)], capture_output=True, text=True)
        assert probe.stdout.strip() == "False"  # a pre-flight started now is refused


def test_release_lock_while_a_preflight_holds_it(monkeypatch, tmp_path):
    lock = tmp_path / "scratch" / ps.LOCK_NAME
    lock.parent.mkdir(parents=True)
    monkeypatch.setattr(ps, "lock_path", lambda: lock)
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time; sys.path.insert(0, sys.argv[1]); import preflight_stamp as ps; "
         "from pathlib import Path\n"
         "with ps.held_lock(Path(sys.argv[2])) as got:\n"
         "    print(got, flush=True); time.sleep(30)",
         str(COMMON), str(lock)],
        stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "True"
        with ps.release_lock() as (got, error):
            assert (got, error) == (False, None)
    finally:
        holder.kill()
        holder.wait()


def test_release_lock_never_raises(monkeypatch):
    monkeypatch.setattr(ps, "lock_path", raising)
    with ps.release_lock() as (got, error):
        assert (got, error) == (False, "git exploded")


def test_preflight_running_never_raises(monkeypatch):
    monkeypatch.setattr(ps, "lock_path", raising)
    assert ps.preflight_running() is False


def test_gate_cli(monkeypatch, capsys):
    monkeypatch.setattr(ps, "release_gate", lambda cmd: (True, f"passed for {cmd}"))
    assert ps.main(["gate", CMD]) == 0
    assert capsys.readouterr().out == f"passed for {CMD}\n"
    assert ps.main(["something"]) == 2


# --- release.py: steps 2 and 4 (S049 § 1.5) ----------------------------------------------------

def load_release(monkeypatch, without_stamp_module=False):
    """A fresh release.py module; with `without_stamp_module`, `import preflight_stamp` fails."""
    if without_stamp_module:
        monkeypatch.setitem(sys.modules, "preflight_stamp", None)
    spec = importlib.util.spec_from_file_location("release_under_test", COMMON / "release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "load_dotenv", lambda *a, **k: None)
    return module


class FakeRun:
    """release.run, faked: answers git by command text; the test command passes or fails."""

    def __init__(self, test_cmd=CMD, test_code=0, commits_since_release=False, lock_state=None):
        self.test_cmd = test_cmd
        self.test_code = test_code
        self.commits_since_release = commits_since_release
        self.commands = []
        self.lock_state = lock_state
        self.locked_during_tests = None

    def __call__(self, cmd, **kwargs):
        self.commands.append(cmd)
        out, code = "", 0
        if cmd == "git rev-parse --abbrev-ref HEAD":
            out = "main\n"
        elif cmd.startswith("git log"):
            out = "S049: pre-flight\x01S049: pre-flight\n\x00release v0.1.9\x01release v0.1.9\x00" \
                if self.commits_since_release else ""
        elif cmd == self.test_cmd:
            code = self.test_code
            if self.lock_state is not None:
                self.locked_during_tests = self.lock_state["locked"]
        return subprocess.CompletedProcess(cmd, code, out, "")


@pytest.fixture
def release_env(monkeypatch):
    monkeypatch.setenv("TEST_CMD", CMD)
    monkeypatch.setenv("GIT_PUSH", "skip")
    for name in ("BUILD_SCRIPT", "DEPLOY_SCRIPT", "POST_BUMP_SCRIPT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sys, "argv", ["release.py"])


def fake_stamp_module(valid=False, running=False, lock=(True, None)):
    calls = []
    state = {"locked": False}

    @contextlib.contextmanager
    def release_lock():
        state["locked"] = lock[0]
        try:
            yield lock
        finally:
            state["locked"] = False

    module = types.SimpleNamespace(
        release_lock=release_lock,
        lock_state=state,
        preflight_running=lambda: running,
        release_gate=lambda cmd: (valid, "VALID" if valid else "NOT VALID. The tests run now."),
        head_sha=lambda: SHA,
        write=lambda sha, cmd: calls.append(("write", sha, cmd)),
        carry=lambda sha, cmd: calls.append(("carry", sha, cmd)),
    )
    return module, calls


def test_release_without_the_stamp_module_runs_its_tests(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch, without_stamp_module=True)
    assert release.preflight_stamp is None
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert CMD in fake.commands
    assert "The pre-flight check is not installed. The tests run now." in capsys.readouterr().out


def test_release_skips_its_tests_on_a_valid_stamp(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch)
    module, calls = fake_stamp_module(valid=True)
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert CMD not in fake.commands
    assert "VALID" in capsys.readouterr().out
    assert not [c for c in calls if c[0] == "write"]


def test_release_runs_its_tests_and_stamps_the_sha_read_before(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch)
    module, calls = fake_stamp_module(valid=False)
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert CMD in fake.commands
    assert ("write", SHA, CMD) in calls
    assert "NOT VALID. The tests run now." in capsys.readouterr().out


def test_release_aborts_while_a_preflight_runs(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch)
    module, _calls = fake_stamp_module(running=True)
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    with pytest.raises(SystemExit):
        release.main()
    assert CMD not in fake.commands
    assert not [c for c in fake.commands if "bump_ver" in c]
    assert "A pre-flight is still running on this computer" in capsys.readouterr().out


def test_release_holds_the_preflight_lock_while_its_tests_run(monkeypatch, release_env):
    """A2 / CR1-02: a pre-flight started during the release's tests is refused."""
    release = load_release(monkeypatch)
    module, _calls = fake_stamp_module(valid=False)
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun(lock_state=module.lock_state)
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert fake.locked_during_tests is True
    assert module.lock_state["locked"] is False  # given back after the run


def test_release_aborts_when_a_preflight_takes_the_lock_first(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch)
    module, _calls = fake_stamp_module(valid=False, lock=(False, None))
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    with pytest.raises(SystemExit):
        release.main()
    assert CMD not in fake.commands
    assert "A pre-flight is still running on this computer" in capsys.readouterr().out


def test_release_runs_its_tests_when_the_lock_cannot_be_taken(monkeypatch, release_env, capsys):
    release = load_release(monkeypatch)
    module, _calls = fake_stamp_module(valid=False, lock=(False, "disk full"))
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun()
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert CMD in fake.commands
    assert ("WARNING: the pre-flight lock could not be taken: disk full. The tests run without it."
            in capsys.readouterr().out)


def test_release_red_tests_still_abort(monkeypatch, release_env):
    release = load_release(monkeypatch)
    module, calls = fake_stamp_module(valid=False)
    monkeypatch.setattr(release, "preflight_stamp", module)
    monkeypatch.setattr(release, "run", FakeRun(test_code=1))
    with pytest.raises(SystemExit):
        release.main()
    assert not calls
    assert module.lock_state["locked"] is False  # the abort gives the lock back


def test_release_carries_the_stamp_after_its_commit(monkeypatch, release_env):
    release = load_release(monkeypatch)
    module, calls = fake_stamp_module(valid=True)
    monkeypatch.setattr(release, "preflight_stamp", module)
    fake = FakeRun(commits_since_release=True)
    monkeypatch.setattr(release, "run", fake)
    release.main()
    assert ("carry", SHA, CMD) in calls
    commit_at = next(i for i, c in enumerate(fake.commands) if c.startswith("git commit"))
    tag_at = next(i for i, c in enumerate(fake.commands) if c.startswith("git tag"))
    assert commit_at < tag_at


def test_release_goes_on_when_every_stamp_function_meets_a_git_error(monkeypatch, release_env, capsys):
    """The real module with git raising: the gate says 'not valid', write and carry warn,
    preflight_running says 'not running'; the release runs its tests and completes."""
    release = load_release(monkeypatch)
    monkeypatch.setattr(release.preflight_stamp, "_git", raising)
    fake = FakeRun(commits_since_release=True)
    monkeypatch.setattr(release, "run", fake)
    release.main()
    out = capsys.readouterr().out
    assert CMD in fake.commands
    assert "The tests run now." in out
    assert "WARNING: the pre-flight stamp could not be written" in out
    assert "WARNING: the pre-flight stamp was not carried" in out
    assert "WARNING: the pre-flight lock could not be taken: git exploded." in out
    assert "complete." in out
