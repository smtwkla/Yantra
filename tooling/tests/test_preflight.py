"""tooling/common/preflight.py (S049 § 1.4): the settings reader, the refusals, the lock, the sha
read once, "HEAD moved" and the failed write. Git, the test command and the stamp are stubbed."""

import subprocess
import sys
from pathlib import Path

import pytest

COMMON = Path(__file__).resolve().parent.parent / "common"
sys.path.insert(0, str(COMMON))  # as release.py finds its sibling (conftest adds only tooling/)

import preflight  # noqa: E402
import preflight_stamp as ps  # noqa: E402

SHA = "c" * 40
LATER_SHA = "d" * 40
CMD = r"tooling\release-tests.bat"

SECTION = """# CLAUDE.md

## Something else

- **Test command**: `wrong, another section`

## Pre-flight

- **Test command**: `tooling\\release-tests.bat`
- **Tests a clean copy of HEAD**: `yes`
- **Failure logs**: `scratch/release-tests/`

## After
- **Tests a clean copy of HEAD**: `no`
"""


# --- read_settings ---------------------------------------------------------------------------

def test_read_settings_strips_the_backticks_and_reads_only_its_section():
    assert preflight.read_settings(SECTION, {}) == {"test_cmd": CMD, "clean_copy": True}


def test_read_settings_without_backticks():
    text = "## Pre-flight\n- **Test command**: pytest -q\n- **Tests a clean copy of HEAD**: no\n"
    assert preflight.read_settings(text, {}) == {"test_cmd": "pytest -q", "clean_copy": False}


def test_read_settings_missing_section():
    assert preflight.read_settings("# CLAUDE.md\n\n## Release\n- **Test command**: `x`\n", {}) is None


def test_read_settings_missing_test_command():
    assert preflight.read_settings("## Pre-flight\n- **Tests a clean copy of HEAD**: `yes`\n", {}) is None


def test_read_settings_missing_clean_copy_is_no():
    assert preflight.read_settings("## Pre-flight\n- **Test command**: `x`\n", {}) == {
        "test_cmd": "x", "clean_copy": False}


# --- A1: the environment first, as release.py reads TEST_CMD ---------------------------------

def test_read_settings_test_cmd_set_wins_over_the_section():
    assert preflight.read_settings(SECTION, {"TEST_CMD": "pytest"}) == {
        "test_cmd": "pytest", "clean_copy": True}


def test_read_settings_test_cmd_unset_uses_the_section():
    assert preflight.read_settings(SECTION, {"OTHER": "x"})["test_cmd"] == CMD


def test_read_settings_test_cmd_empty_counts_as_unset():
    assert preflight.read_settings(SECTION, {"TEST_CMD": ""})["test_cmd"] == CMD
    assert preflight.read_settings(SECTION, {"TEST_CMD": "  "})["test_cmd"] == CMD


def test_read_settings_test_cmd_without_a_section():
    assert preflight.read_settings("", {"TEST_CMD": CMD}) == {"test_cmd": CMD, "clean_copy": False}


def test_read_settings_clean_copy_from_the_environment():
    assert preflight.read_settings(SECTION, {"PREFLIGHT_CLEAN_COPY": "no"})["clean_copy"] is False
    assert preflight.read_settings("", {"TEST_CMD": "x", "PREFLIGHT_CLEAN_COPY": "yes"})["clean_copy"] is True
    assert preflight.read_settings(SECTION, {"PREFLIGHT_CLEAN_COPY": ""})["clean_copy"] is True


# --- main, stubbed -----------------------------------------------------------------------------

class World:
    """The stubs: the branch, a clean tree or not, HEAD before and after the run, the command's
    exit code, and the write's answer."""

    def __init__(self, monkeypatch, tmp_path, *, clean_copy=True, branch="main", clean=True,
                 heads=(SHA, SHA), code=0, write_error=None, removed=(False, None)):
        self.ran = []
        self.written = []
        self.removed = []
        heads = list(heads)
        # `clean` is one answer for every call, or a list of answers in turn (before, after the run)
        cleans = list(clean) if isinstance(clean, (list, tuple)) else [clean]
        settings_file = tmp_path / "CLAUDE.md"
        settings_file.write_text(
            f"## Pre-flight\n- **Test command**: `{CMD}`\n"
            f"- **Tests a clean copy of HEAD**: `{'yes' if clean_copy else 'no'}`\n", encoding="utf-8")
        monkeypatch.setattr(preflight, "SETTINGS_FILE", settings_file)
        monkeypatch.delenv("TEST_CMD", raising=False)
        monkeypatch.delenv("PREFLIGHT_CLEAN_COPY", raising=False)
        monkeypatch.setattr(preflight, "current_branch", lambda: branch)
        monkeypatch.setattr(ps, "tree_clean", lambda: cleans.pop(0) if len(cleans) > 1 else cleans[0])
        monkeypatch.setattr(ps, "head_sha", lambda: heads.pop(0) if len(heads) > 1 else heads[0])
        monkeypatch.setattr(ps, "main_scratch", lambda: tmp_path / "scratch")
        monkeypatch.setattr(ps, "lock_path", lambda: tmp_path / "scratch" / ps.LOCK_NAME)

        def fake_run(cmd, log_path):
            self.ran.append((cmd, log_path))
            return code, ["== all: PASSED"]

        def fake_write(sha, cmd, tested_at, summary):
            self.written.append((sha, cmd, summary))
            return write_error

        def fake_remove(sha):
            self.removed.append(sha)
            return removed

        monkeypatch.setattr(preflight, "run_tests", fake_run)
        monkeypatch.setattr(ps, "write", fake_write)
        monkeypatch.setattr(ps, "remove", fake_remove)


def last_line(capsys):
    return capsys.readouterr().out.strip().splitlines()[-1]


def test_green_run_stamps_the_sha_read_before(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path)
    assert preflight.main() == 0
    assert world.written == [(SHA, CMD, ["== all: PASSED"])]
    assert world.ran[0][1] == tmp_path / "scratch" / "preflight" / "ccccccc.log"
    assert last_line(capsys).startswith("Pre-flight passed for ccccccc. Stamped until ")


def test_no_settings(monkeypatch, tmp_path, capsys):
    World(monkeypatch, tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# no section\n", encoding="utf-8")
    assert preflight.main() == 2
    assert last_line(capsys) == preflight.NO_SETTINGS


def test_not_on_main(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, branch="feature")
    assert preflight.main() == 2
    assert last_line(capsys) == "Pre-flight runs on main, as the release does. You are on feature."
    assert not world.ran


def test_dirty_tree_refused_when_the_command_tests_the_working_folder(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, clean_copy=False, clean=False)
    assert preflight.main() == 2
    assert last_line(capsys) == ("The working tree has uncommitted changes, and the test command "
                                 "tests the working folder. Commit or stash them, then run pre-flight again.")
    assert not world.ran


def test_dirty_tree_allowed_when_the_command_tests_a_clean_copy(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, clean_copy=True, clean=False)
    assert preflight.main() == 0
    out = capsys.readouterr().out
    assert "The working tree has uncommitted changes; the tests run on commit ccccccc only." in out
    assert world.written


def test_head_moved_during_the_run(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, heads=(SHA, LATER_SHA))
    assert preflight.main() == 1
    assert last_line(capsys) == ("A commit was made during pre-flight, so it is not clear which "
                                 "commit the tests ran on. No stamp. Run pre-flight again.")
    assert not world.written


def test_red_run(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, code=1)
    assert preflight.main() == 1
    assert last_line(capsys) == "Pre-flight failed for ccccccc: the test command exited 1. No stamp."
    assert not world.written
    assert world.removed == [SHA]  # A2: tried, but there was no stamp


def test_red_run_removes_the_earlier_stamp(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, code=1, removed=(True, None))
    assert preflight.main() == 1
    assert last_line(capsys) == ("Pre-flight failed for ccccccc: the test command exited 1. No stamp. "
                                 "Its earlier stamp is removed.")
    assert world.removed == [SHA]


def test_red_run_when_the_stamp_cannot_be_removed(monkeypatch, tmp_path, capsys):
    World(monkeypatch, tmp_path, code=1, removed=(False, "error: cannot lock ref"))
    assert preflight.main() == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[-2] == ("Any earlier pre-flight stamp of ccccccc could not be removed: error: cannot "
                         "lock ref. Remove it with: git notes --ref=preflight remove ccccccc")
    assert lines[-1] == "Pre-flight failed for ccccccc: the test command exited 1. No stamp."


def test_head_moved_removes_nothing(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, heads=(SHA, LATER_SHA), code=1)
    assert preflight.main() == 1
    assert last_line(capsys).startswith("A commit was made during pre-flight")
    assert not world.removed


def test_tree_changed_during_the_run_when_the_command_tests_the_working_folder(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path, clean_copy=False, clean=[True, False])
    assert preflight.main() == 1
    assert last_line(capsys) == ("The working tree changed during pre-flight, so the tests did not run "
                                 "on commit ccccccc alone. No stamp. Run pre-flight again.")
    assert not world.written


def test_tree_still_clean_after_the_run_stamps(monkeypatch, tmp_path):
    world = World(monkeypatch, tmp_path, clean_copy=False, clean=[True, True])
    assert preflight.main() == 0
    assert world.written


def test_an_os_error_ends_in_one_line_and_exit_2(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path)

    def broken_run(cmd, log_path):
        raise PermissionError(13, "Permission denied", str(log_path))

    monkeypatch.setattr(preflight, "run_tests", broken_run)
    assert preflight.main() == 2
    out = capsys.readouterr().out.strip().splitlines()
    assert out[-1].startswith("Pre-flight stopped because of a file or system error: ")
    assert "Permission denied" in out[-1] and out[-1].endswith(". No stamp.")
    assert not world.written


def test_failed_write(monkeypatch, tmp_path, capsys):
    World(monkeypatch, tmp_path, write_error="error: cannot lock ref")
    assert preflight.main() == 1
    assert last_line(capsys) == ("Pre-flight passed for ccccccc, but the stamp could not be written: "
                                 "error: cannot lock ref. The release will run its tests.")


def test_a_second_run_is_refused(monkeypatch, tmp_path, capsys):
    world = World(monkeypatch, tmp_path)
    lock = tmp_path / "scratch" / ps.LOCK_NAME
    lock.parent.mkdir(parents=True)
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
        assert preflight.main() == 2
    finally:
        holder.kill()
        holder.wait()
    assert last_line(capsys) == "Another pre-flight is running. Wait for it to finish."
    assert not world.ran


def test_run_tests_never_waits_for_input(tmp_path):
    command = subprocess.list2cmdline([sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"])
    code, last = preflight.run_tests(command, tmp_path / "x.log")
    assert (code, last) == (0, ["''"])


def test_run_tests_tees_the_output_and_keeps_the_last_lines(tmp_path, capsys):
    log = tmp_path / "out" / "x.log"
    command = subprocess.list2cmdline(
        [sys.executable, "-c", "import sys; [print('line', n) for n in range(15)]; sys.exit(3)"])
    code, last = preflight.run_tests(command, log)
    assert code == 3
    assert last == [f"line {n}" for n in range(5, 15)]
    assert "line 0" in log.read_text(encoding="utf-8")
    assert "line 14" in capsys.readouterr().out


def test_run_tests_kills_the_command_when_the_run_fails(tmp_path, monkeypatch):
    """CR2-02: an error while reading or logging must not leave the test command running."""
    class Stdout:
        def __iter__(self):
            raise OSError("pipe broke")

    class Process:
        stdout = Stdout()
        calls = []

        def poll(self):
            return None  # still running

        def kill(self):
            self.calls.append("kill")

        def wait(self):
            self.calls.append("wait")

    process = Process()
    monkeypatch.setattr(preflight.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(OSError, match="pipe broke"):
        preflight.run_tests("x", tmp_path / "x.log")
    assert process.calls == ["kill", "wait"]
