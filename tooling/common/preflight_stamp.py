"""Pre-flight stamps: a git note that says the release's tests passed on one exact commit.

`/pre-flight` (tooling/common/preflight.py) runs the repo's test command on HEAD before the
maintenance window and, when it is green, writes a stamp on the tested commit. `release.py` then
skips its tests for that commit (`release_gate`), and carries the stamp to its release commit
when that commit changes only VERSION (`carry`), so a retry after a failed build or deploy does
not test again.

The stamp is a git note in refs/notes/preflight: plain `key: value` lines, readable with
`git notes --ref=preflight show HEAD`. Git does not push a notes ref unless it is named, so the
stamp stays on this machine. It is valid only for the commit it names, the same test command,
this computer, and STAMP_VALID_DAYS.

Pure core: stamp_text, parse, check, carry_text (plain data in and out, no git, no clock).
Shell: read, write, remove (a red run), head_sha, tree_clean, machine_name, release_gate, carry,
preflight_running, and the lock that preflight.py holds and release.py holds around its own test
run (release_lock). Every shell function that release.py calls catches its own
errors, so the gate can only skip tests, never fail a release.

Stdlib only; generic for every SMTW repo (lifted to smtw-common, S049).

CLI, for checks by hand (changes nothing):
    python tooling/common/preflight_stamp.py gate "<test command>"
"""

import contextlib
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

STAMP_VALID_DAYS = 7
# A stamp dated later than now by more than this is not valid (CR1-04): a clock that was wrong
# when the stamp was made must not lengthen its life. Small enough to be safe, large enough for
# the drift between two clock syncs.
CLOCK_SKEW = timedelta(minutes=5)
NOTES_REF = "preflight"
STAMP_VERSION = "1"
SUMMARY_MAX_LINES = 10
LOCK_NAME = "preflight.lock"
IST = timezone(timedelta(hours=5, minutes=30), "IST")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_SHORT = 7
# The keys of a stamp, in the order stamp_text writes them; `summary` may repeat.
_KEYS = ("preflight", "result", "commit", "tested_at", "test_cmd", "machine", "by",
         "carried_from", "summary")


# ---------------------------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------------------------

def short(sha):
    return (sha or "")[:_SHORT]


def ist_text(moment):
    """A time as users read it: DD-MM-YYYY HH:MM, in IST."""
    return moment.astimezone(IST).strftime("%d-%m-%Y %H:%M")


def expires_at(tested_at):
    return tested_at + timedelta(days=STAMP_VALID_DAYS)


def stamp_text(sha, tested_at, test_cmd, machine, by, summary=(), carried_from=None):
    """The note's text. `tested_at` is an aware datetime; it is written in IST, ISO 8601."""
    lines = [
        f"preflight: {STAMP_VERSION}",
        "result: passed",
        f"commit: {sha}",
        f"tested_at: {tested_at.astimezone(IST).isoformat(timespec='seconds')}",
        f"test_cmd: {test_cmd}",
        f"machine: {machine}",
        f"by: {by}",
    ]
    if carried_from:
        lines.append(f"carried_from: {carried_from}")
    for line in list(summary)[-SUMMARY_MAX_LINES:]:
        lines.append(f"summary: {line}")
    return "\n".join(lines) + "\n"


def parse(text):
    """The note's fields as a dict (`summary` a list of lines), or None when it is no stamp.

    Unknown keys are kept; a line without `key:` is ignored. A stamp needs at least
    `preflight` and `commit`."""
    if not text:
        return None
    fields = {"summary": []}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value[1:] if value.startswith(" ") else value
        if key == "summary":
            fields["summary"].append(value.rstrip())
        elif key and key not in fields:
            fields[key] = value.strip()
    if "preflight" not in fields or "commit" not in fields:
        return None
    return fields


def _tested_at(fields):
    try:
        moment = datetime.fromisoformat(fields.get("tested_at", ""))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def check(note_text, head_sha, test_cmd, now, machine):
    """(valid, reason): may the release skip `test_cmd` for `head_sha`?

    `note_text` is the commit's note, or None (no note, or git failed: never valid).
    `now` is an aware datetime. The reason is one console line ending with what happens next."""
    sha = short(head_sha)
    run_now = "The tests run now."
    fields = parse(note_text)
    if fields is None:
        if note_text:
            return False, f"The pre-flight stamp of {sha} cannot be read. {run_now}"
        return False, f"No pre-flight stamp for {sha}. {run_now}"
    tested_at = _tested_at(fields)
    if fields.get("preflight") != STAMP_VERSION or tested_at is None:
        return False, f"The pre-flight stamp of {sha} cannot be read. {run_now}"
    if fields.get("result") != "passed":
        return False, f"The pre-flight stamp of {sha} does not record a pass. {run_now}"
    if fields.get("commit") != head_sha:
        return False, f"The pre-flight stamp on {sha} names another commit. {run_now}"
    if tested_at - now > CLOCK_SKEW:
        return False, (f"The pre-flight stamp of {sha} is dated later than now; this computer's "
                       f"clock may have been wrong. {run_now}")
    if now - tested_at > timedelta(days=STAMP_VALID_DAYS):
        days = (now - tested_at).days
        age = f"{days} days old" if days > STAMP_VALID_DAYS else f"more than {STAMP_VALID_DAYS} days old"
        return False, (f"The pre-flight stamp of {sha} is {age}; a stamp is valid for "
                       f"{STAMP_VALID_DAYS} days. {run_now}")
    if fields.get("test_cmd") != test_cmd:
        return False, f"The pre-flight stamp of {sha} was made with another test command. {run_now}"
    if fields.get("machine") != machine:
        return False, f"The pre-flight stamp of {sha} was made on another computer. {run_now}"
    return True, (f"Tests passed in pre-flight on {ist_text(tested_at)} for {sha}. "
                  "The release does not run them again.")


def carry_text(parent_note, parent_sha, changed_files, release_sha, test_cmd, now, machine):
    """The stamp for a release commit, or None.

    Carried only when the parent's stamp is valid and the release commit changes exactly VERSION.
    The carried stamp keeps the parent's tested_at, so it expires with the original."""
    if sorted(changed_files) != ["VERSION"]:
        return None
    valid, _reason = check(parent_note, parent_sha, test_cmd, now, machine)
    if not valid:
        return None
    fields = parse(parent_note)
    return stamp_text(release_sha, _tested_at(fields), fields["test_cmd"], fields["machine"],
                      fields.get("by", ""), fields["summary"], carried_from=parent_sha)


# ---------------------------------------------------------------------------------------------
# Shell: git, the clock, the computer
# ---------------------------------------------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          encoding="utf-8", errors="replace")


def _git_out(*args):
    """git's stdout, stripped, or None when git failed."""
    result = _git(*args)
    return result.stdout.strip() if result.returncode == 0 else None


def now_ist():
    return datetime.now(IST)


def machine_name():
    return platform.node()


def git_user():
    return _git_out("config", "user.name") or ""


def head_sha():
    """The full sha of HEAD, or None; never raises (release.py calls it)."""
    try:
        return _git_out("rev-parse", "HEAD")
    except Exception:
        return None


def tree_clean():
    """True when `git status --porcelain` prints nothing; False also when git fails."""
    try:
        result = _git("status", "--porcelain")
    except Exception:
        return False
    return result.returncode == 0 and not result.stdout.strip()


def read(sha):
    """The commit's note text, or None (no note: `git notes show` exits 1; or git failed)."""
    try:
        result = _git("notes", f"--ref={NOTES_REF}", "show", sha)
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def _add_note(sha, text):
    """Writes the note (replacing one). None on success, else git's message."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        note_file = f.name
    try:
        result = _git("notes", f"--ref={NOTES_REF}", "add", "-f", "-F", note_file, sha)
    finally:
        os.unlink(note_file)
    return None if result.returncode == 0 else _git_message(result)


def _git_message(result):
    return (result.stderr or result.stdout).strip() or f"git notes exited {result.returncode}"


def write(sha, test_cmd, tested_at=None, summary=()):
    """Stamps `sha`: its `test_cmd` passed at `tested_at` (default now) on this computer.

    Returns None on success, else the reason as text; never raises."""
    try:
        if not sha:
            return "the commit is not known"
        text = stamp_text(sha, tested_at or now_ist(), test_cmd, machine_name(), git_user(), summary)
        return _add_note(sha, text)
    except Exception as error:  # the release goes on whatever happens here (S049 § 1.5)
        return str(error) or type(error).__name__


def remove(sha):
    """Removes `sha`'s stamp, whatever its test command (S049 A2: a red run, so the newest result
    decides). Returns (removed, error): removed is True when a note was there and is gone; error
    is git's message or None. Never raises."""
    try:
        had_note = read(sha) is not None
        result = _git("notes", f"--ref={NOTES_REF}", "remove", "--ignore-missing", sha)
        if result.returncode != 0:
            return False, _git_message(result)
        return had_note, None
    except Exception as error:
        return False, str(error) or type(error).__name__


def release_gate(test_cmd):
    """(valid, reason) for HEAD; never raises: any error is 'not valid', and the tests run."""
    try:
        sha = head_sha()
        if sha is None:
            return False, "Git could not read HEAD, so the pre-flight stamp is not checked. The tests run now."
        return check(read(sha), sha, test_cmd, now_ist(), machine_name())
    except Exception as error:
        return False, f"The pre-flight stamp could not be checked: {error}. The tests run now."


def carry(release_sha, test_cmd):
    """Carries the first parent's valid stamp to the release commit when it changes only VERSION.

    Returns the line to print, or None when there is nothing to carry; never raises."""
    try:
        if not release_sha:
            return "WARNING: the pre-flight stamp was not carried: the release commit is not known."
        parent = _git_out("rev-parse", f"{release_sha}^1")
        changed = _git_out("diff", "--name-only", parent or "", release_sha) if parent else None
        if parent is None or changed is None:
            return "WARNING: the pre-flight stamp was not carried: git could not compare the release commit."
        text = carry_text(read(parent), parent, changed.splitlines(), release_sha, test_cmd,
                          now_ist(), machine_name())
        if text is None:
            return None
        error = _add_note(release_sha, text)
        if error:
            return f"WARNING: the pre-flight stamp was not carried: {error}"
        return f"The pre-flight stamp of {short(parent)} is carried to the release commit {short(release_sha)}."
    except Exception as error:
        return f"WARNING: the pre-flight stamp was not carried: {error}"


# ---------------------------------------------------------------------------------------------
# The lock: one pre-flight at a time, and no release while one runs
# ---------------------------------------------------------------------------------------------
# A deliberate copy of the repo-specific e2e lock code (S049 BR2-07): generic code cannot import
# a repo's file.

def main_scratch():
    """The main working folder's scratch/ (the parent of git's common dir), so a worktree and
    the working folder share one lock. REPO_ROOT's own when git cannot tell."""
    try:
        common = _git_out("rev-parse", "--path-format=absolute", "--git-common-dir")
    except OSError:
        common = None
    return Path(common).parent / "scratch" if common else REPO_ROOT / "scratch"


def lock_path():
    return main_scratch() / LOCK_NAME


@contextlib.contextmanager
def held_lock(path):
    """Yields True while this process holds the lock at `path`; False when another process
    holds it (no waiting). Creates the folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    try:
        try:
            _lock(handle)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            _unlock(handle)
    finally:
        handle.close()


@contextlib.contextmanager
def release_lock():
    """The pre-flight lock for release.py's own TEST_CMD run (S049 A2), so a pre-flight started
    meanwhile is refused instead of removing the release's test worktree.

    Yields (got, error): (True, None) while this process holds the lock; (False, None) when a
    pre-flight holds it; (False, <the error>) when the lock could not be tried, and the release
    then runs its tests without it. An error of the lock code never raises; an error inside the
    block (the tests, an abort) passes through, and the lock is given back."""
    stack = contextlib.ExitStack()
    try:
        got, error = stack.enter_context(held_lock(lock_path())), None
    except Exception as exc:
        got, error = False, str(exc) or type(exc).__name__
    try:
        yield got, error
    finally:
        try:
            stack.close()
        except Exception:  # unlocking failed; closing the file in held_lock still frees the lock
            pass


def preflight_running():
    """True when another process holds the pre-flight lock; never raises (an error is False)."""
    try:
        path = lock_path()
        if not path.exists():
            return False
        with held_lock(path) as got_it:
            return not got_it
    except Exception:
        return False


def _lock(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def main(argv):
    if len(argv) != 2 or argv[0] != "gate":
        print('Usage: preflight_stamp.py gate "<test command>"   (prints what the release would decide)')
        return 2
    valid, reason = release_gate(argv[1])
    print(reason)
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
