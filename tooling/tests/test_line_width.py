"""S094: every Python line of the repo is at most 120 characters.

The check is a function of a root and a list of paths, so the tests below feed it a temp tree.
The real-tree test feeds it the files git lists (tracked, plus new and not ignored).
Exempt, with the reason in the brief (§ 1): the `_MIGRATIONS` block of backend/local_db.py and the
frozen migration fixtures (applied migrations are never edited), and the files synced from
smtw-common (edited there only)."""

import subprocess
from pathlib import Path

import pytest

LIMIT = 120
ROOT = Path(__file__).resolve().parents[2]

MIGRATIONS_FILE = "backend/local_db.py"
MIGRATIONS_START = "_MIGRATIONS = ["
MIGRATIONS_END = "]"
FROZEN_FILES = (
    "backend/tests/fixtures/migrations_v41.py",
    "backend/tests/fixtures/migrations_v47.py",
)
# Synced from smtw-common (tooling/common/sync_common.py FILES and DIRS).
SYNCED_PREFIXES = (
    "tooling/common/",
    "tooling/steps/",
    "tooling/roadmap/",
    "tooling/deps/",
    ".claude/",
)


def is_exempt_file(rel_path):
    return rel_path in FROZEN_FILES or rel_path.startswith(SYNCED_PREFIXES)


def long_lines(root, rel_paths, limit=LIMIT):
    """Return (path, line number, length) for each line over `limit` characters, outside the exempt places."""
    rows = []
    for rel in rel_paths:
        if is_exempt_file(rel):
            continue
        text = (Path(root) / rel).read_text(encoding="utf-8")
        in_migrations = False
        for number, line in enumerate(text.splitlines(), start=1):
            if rel == MIGRATIONS_FILE:
                if line.startswith(MIGRATIONS_START):
                    in_migrations = True
                elif in_migrations and line == MIGRATIONS_END:
                    in_migrations = False
                    continue
            if in_migrations:
                continue
            if len(line) > limit:
                rows.append((rel, number, len(line)))
        if in_migrations:
            raise ValueError(f"{rel}: the _MIGRATIONS block has no closing '{MIGRATIONS_END}' at column 0")
    return rows


def python_files(root):
    """Tracked and new, not ignored, .py files (a step's new files are untracked until committed)."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py"],
        cwd=root, capture_output=True, text=True, check=True, encoding="utf-8",
    ).stdout
    # --cached also lists a file deleted in the working tree (agents never stage a deletion).
    return [rel for rel in out.splitlines() if (Path(root) / rel).is_file()]


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_repo_python_lines_fit():
    rows = long_lines(ROOT, python_files(ROOT))
    report = "\n".join(f"{path}:{number} is {length} characters" for path, number, length in rows)
    assert not rows, f"Python lines over {LIMIT} characters:\n{report}"


def test_long_line_is_reported_with_file_and_line(tmp_path):
    write(tmp_path, "a.py", "x = 1\n" + "y = '" + "a" * 130 + "'\n")
    assert long_lines(tmp_path, ["a.py"]) == [("a.py", 2, 136)]


def test_line_of_exactly_the_limit_passes(tmp_path):
    write(tmp_path, "a.py", "#" * LIMIT + "\n")
    assert long_lines(tmp_path, ["a.py"]) == []


def test_characters_count_not_bytes_and_crlf_is_ignored(tmp_path):
    write(tmp_path, "a.py", "# " + "—" * (LIMIT - 2) + "\r\n")
    assert long_lines(tmp_path, ["a.py"]) == []


def test_exempt_files_pass(tmp_path):
    long = "x = '" + "a" * 130 + "'\n"
    for rel in (*FROZEN_FILES, "tooling/common/x.py", "tooling/steps/x.py", "tooling/roadmap/x.py",
                "tooling/deps/x.py", ".claude/hooks/x.py"):
        write(tmp_path, rel, long)
    assert long_lines(tmp_path, [*FROZEN_FILES, "tooling/common/x.py", "tooling/steps/x.py",
                                 "tooling/roadmap/x.py", "tooling/deps/x.py", ".claude/hooks/x.py"]) == []


def test_migrations_block_is_exempt_and_ends_at_its_bracket(tmp_path):
    long = "    '" + "a" * 130 + "',\n"
    write(tmp_path, MIGRATIONS_FILE, "x = 1\n_MIGRATIONS = [\n" + long + "]\ny = '" + "b" * 130 + "'\n")
    assert long_lines(tmp_path, [MIGRATIONS_FILE]) == [(MIGRATIONS_FILE, 5, 136)]


def test_migrations_block_without_closing_bracket_fails_clearly(tmp_path):
    write(tmp_path, MIGRATIONS_FILE, "_MIGRATIONS = [\n    1,\n]  # end\n")
    with pytest.raises(ValueError, match="no closing"):
        long_lines(tmp_path, [MIGRATIONS_FILE])


def test_file_list_has_committed_and_untracked_and_leaves_out_ignored_and_deleted(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    write(tmp_path, ".gitignore", "ignored/\n")
    write(tmp_path, "committed.py", "x = 1\n")
    git("add", ".gitignore", "committed.py")
    git("-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-q", "-m", "t")
    write(tmp_path, "untracked.py", "x = 1\n")
    write(tmp_path, "ignored/skipped.py", "x = 1\n")
    write(tmp_path, "deleted.py", "x = 1\n")
    git("add", "deleted.py")
    (tmp_path / "deleted.py").unlink()  # in the index, gone from the working tree
    assert sorted(python_files(tmp_path)) == ["committed.py", "untracked.py"]
