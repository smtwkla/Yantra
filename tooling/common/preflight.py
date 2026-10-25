"""Pre-flight: run the release's tests on HEAD before the maintenance window, and stamp HEAD
when they pass, so the release does not run them again (S049).

    uv run --no-project python tooling/common/preflight.py

The test command is the environment's TEST_CMD, as release.py reads it (a run config sets the
same value as the Release run configs); when it is unset or empty, the `## Pre-flight` section of
the repo's .claude/CLAUDE.md gives it:
    - **Test command**: `<the release's TEST_CMD>`
    - **Tests a clean copy of HEAD**: `yes` | `no`
PREFLIGHT_CLEAN_COPY=yes|no overrides the second line the same way. "yes" lets pre-flight run with
uncommitted changes, because the command tests HEAD in its own worktree; a wrong "yes" would stamp
code the command did not test.

It never asks a question and never waits for input, so it can run unattended (a run config, a hook).

In order: the settings; one run at a time (scratch/preflight.lock in the main working folder);
the refusals (not on main; uncommitted changes when the command tests the working folder); the
sha of HEAD, read once; the test command, its output to the console and to
scratch/preflight/<short-sha>.log; HEAD read again; on red, any stamp on the sha removed (A2);
with "clean copy: no", the tree checked again; the stamp (preflight_stamp.write) on the sha read
before the run.

Exit codes: 0 passed and stamped; 1 the tests failed, the stamp failed, HEAD moved, or the
working tree changed during the run; 2 not run (no settings, another pre-flight or a release's
test run, a refusal, a file or system error).

Stdlib only; generic for every SMTW repo (lifted to smtw-common, S049).
"""

import collections
import os
import subprocess
import sys

import preflight_stamp as ps

SETTINGS_FILE = ps.REPO_ROOT / ".claude" / "CLAUDE.md"
SECTION = "## Pre-flight"
TEST_COMMAND_LINE = "- **Test command**:"
CLEAN_COPY_LINE = "- **Tests a clean copy of HEAD**:"
BRANCH = "main"

PASSED, FAILED, NOT_RUN = 0, 1, 2

NO_SETTINGS = ("This repo has no Pre-flight section in its CLAUDE.md. "
               "Add one with its test command, the release's TEST_CMD.")


# ---------------------------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------------------------

def _value(line, prefix):
    return line[len(prefix):].strip().strip("`").strip()


def _yes(value):
    return value.strip().lower() == "yes"


def read_section(text):
    """The two values of the `## Pre-flight` section, {'test_cmd': str | None,
    'clean_copy': bool | None}, or None when there is no such section. It runs from the heading
    to the next `## `; the values lose their backticks."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == SECTION)
    except StopIteration:
        return None
    found = {"test_cmd": None, "clean_copy": None}
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped.startswith(TEST_COMMAND_LINE):
            found["test_cmd"] = _value(stripped, TEST_COMMAND_LINE) or None
        elif stripped.startswith(CLEAN_COPY_LINE):
            found["clean_copy"] = _yes(_value(stripped, CLEAN_COPY_LINE))
    return found


def read_settings(text, environ):
    """{'test_cmd': str, 'clean_copy': bool}, or None when no test command is known.

    The environment comes first, as release.py reads TEST_CMD (S049 A1): TEST_CMD, then the
    section's Test command; PREFLIGHT_CLEAN_COPY (yes | no), then the section's line. An unset
    or empty variable counts as unset. A missing "clean copy" value is `no`, the side that
    refuses a dirty tree."""
    section = read_section(text or "") or {"test_cmd": None, "clean_copy": None}
    test_cmd = (environ.get("TEST_CMD") or "").strip() or section["test_cmd"]
    if not test_cmd:
        return None
    clean_env = (environ.get("PREFLIGHT_CLEAN_COPY") or "").strip()
    clean_copy = _yes(clean_env) if clean_env else bool(section["clean_copy"])
    return {"test_cmd": test_cmd, "clean_copy": clean_copy}


# ---------------------------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------------------------

def current_branch():
    try:
        return ps._git_out("rev-parse", "--abbrev-ref", "HEAD")
    except OSError:
        return None


def run_tests(test_cmd, log_path):
    """Runs the test command in the repo root (shell=True, as release.py runs TEST_CMD); its output
    goes to the console and the log. Returns (exit code, the last summary lines)."""
    last = collections.deque(maxlen=ps.SUMMARY_MAX_LINES)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as log:
        # stdin from nowhere: a command that asks a question gets end-of-file, never a wait (A1)
        process = subprocess.Popen(test_cmd, shell=True, cwd=ps.REPO_ROOT, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   encoding="utf-8", errors="replace")
        try:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                if line.strip():
                    last.append(line.rstrip())
            code = process.wait()
        finally:
            # An error here (a log that cannot be written) must not leave the test command running
            # after preflight.py ends (CR2-02); after a normal end this is a no-op.
            if process.poll() is None:
                process.kill()
                process.wait()
    return code, list(last)


def refusal(settings, dirty):
    """The line that stops the run before the tests, or None."""
    branch = current_branch()
    if branch != BRANCH:
        return f"Pre-flight runs on {BRANCH}, as the release does. You are on {branch or 'no branch'}."
    if dirty and not settings["clean_copy"]:
        return ("The working tree has uncommitted changes, and the test command tests the working "
                "folder. Commit or stash them, then run pre-flight again.")
    return None


def report_red(sha, code):
    """A red run: removes any stamp on `sha` (S049 A2: the newest result decides), then prints
    the red line, last, after the warning of a failed removal."""
    short = ps.short(sha)
    line = f"Pre-flight failed for {short}: the test command exited {code}. No stamp."
    removed, error = ps.remove(sha)
    if error:
        print(f"Any earlier pre-flight stamp of {short} could not be removed: {error}. "
              f"Remove it with: git notes --ref={ps.NOTES_REF} remove {short}")
    elif removed:
        line += " Its earlier stamp is removed."
    print(line)


def main():
    try:
        text = SETTINGS_FILE.read_text(encoding="utf-8")
    except OSError:
        text = ""
    settings = read_settings(text, os.environ)
    if settings is None:
        print(NO_SETTINGS)
        return NOT_RUN
    try:
        with ps.held_lock(ps.lock_path()) as got_lock:
            if not got_lock:
                print("Another pre-flight is running. Wait for it to finish.")
                return NOT_RUN
            return run_locked(settings)
    except OSError as error:  # scratch/ not writable, the command not startable (CR1-05)
        print(f"Pre-flight stopped because of a file or system error: {error}. No stamp.")
        return NOT_RUN


def run_locked(settings):
    dirty = not ps.tree_clean()
    refused = refusal(settings, dirty)
    if refused:
        print(refused)
        return NOT_RUN
    sha = ps.head_sha()
    if sha is None:
        print("Git could not read HEAD, so pre-flight cannot run. Check the repo with git status.")
        return NOT_RUN
    short = ps.short(sha)
    if dirty:
        print(f"The working tree has uncommitted changes; the tests run on commit {short} only.")
    log_path = ps.main_scratch() / "preflight" / f"{short}.log"
    print(f"Pre-flight runs {settings['test_cmd']} on {short}. Log: {log_path}")

    code, summary = run_tests(settings["test_cmd"], log_path)

    if ps.head_sha() != sha:
        print("A commit was made during pre-flight, so it is not clear which commit the tests ran "
              "on. No stamp. Run pre-flight again.")
        return FAILED
    if code != 0:
        report_red(sha, code)
        return FAILED
    if not settings["clean_copy"] and not ps.tree_clean():
        # The command tested the working folder, and it changed during the run (CR1-03).
        print(f"The working tree changed during pre-flight, so the tests did not run on commit "
              f"{short} alone. No stamp. Run pre-flight again.")
        return FAILED
    tested_at = ps.now_ist()
    error = ps.write(sha, settings["test_cmd"], tested_at, summary)
    if error:
        print(f"Pre-flight passed for {short}, but the stamp could not be written: {error}. "
              "The release will run its tests.")
        return FAILED
    print(f"Pre-flight passed for {short}. Stamped until {ps.ist_text(ps.expires_at(tested_at))}.")
    return PASSED


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
