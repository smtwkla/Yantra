"""tooling/steps/step_snapshot.py on a throw-away git repo: a snapshot is a commit under
refs/steps/<step> that never moves HEAD, the user's index or the working files."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "steps"))

import step_snapshot as snap  # noqa: E402


def run(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    run(tmp_path, "init", "-q", "-b", "main")
    run(tmp_path, "config", "user.email", "test@example.test")
    run(tmp_path, "config", "user.name", "Test")
    run(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / ".gitignore").write_text("ignored.txt\n")
    (tmp_path / "a.txt").write_text("one\n")
    run(tmp_path, "add", ".")
    run(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def files_at(repo, ref):
    return set(run(repo, "ls-tree", "-r", "--name-only", ref).splitlines())


def test_a_snapshot_keeps_head_index_and_tree_and_holds_untracked_files(repo):
    (repo / "a.txt").write_text("two\n")
    (repo / "new.txt").write_text("new\n")
    (repo / "ignored.txt").write_text("x\n")
    run(repo, "add", "a.txt")  # the user's own staging must survive
    head, status = run(repo, "rev-parse", "HEAD"), run(repo, "status", "--porcelain")

    result = snap.snapshot(repo, "S001", "S001: first step;")

    assert run(repo, "rev-parse", "HEAD") == head
    assert run(repo, "status", "--porcelain") == status
    assert result["parent"] == head
    assert files_at(repo, "refs/steps/S001") == {".gitignore", "a.txt", "new.txt"}
    assert run(repo, "log", "-1", "--format=%s", "refs/steps/S001") == "S001: first step;"


def test_the_next_snapshot_builds_on_the_last_unmerged_one(repo):
    (repo / "a.txt").write_text("two\n")
    first = snap.snapshot(repo, "S001", "S001: one;")
    (repo / "b.txt").write_text("b\n")
    second = snap.snapshot(repo, "S002", "S002: two;")
    assert second["parent"] == first["commit"]
    assert run(repo, "diff", "--name-only", first["commit"], second["commit"]) == "b.txt"


def test_after_a_fast_forward_the_next_snapshot_builds_on_head(repo):
    (repo / "a.txt").write_text("two\n")
    first = snap.snapshot(repo, "S001", "S001: one;")
    snap.adopt(repo, "S001")
    assert run(repo, "rev-parse", "HEAD") == first["commit"]
    assert snap.listing(repo)["merged"][0][0] == "S001"
    (repo / "b.txt").write_text("b\n")
    assert snap.snapshot(repo, "S002", "S002: two;")["parent"] == first["commit"]


def test_the_newest_snapshot_is_replaced_on_its_own_parent(repo):
    (repo / "a.txt").write_text("two\n")
    first = snap.snapshot(repo, "S001", "S001: one;")
    (repo / "a.txt").write_text("three\n")
    again = snap.snapshot(repo, "S001", "S001: one, fixed;")
    assert again["parent"] == first["parent"]
    assert run(repo, "rev-parse", "refs/steps/S001") == again["commit"]


def test_refusals(repo):
    with pytest.raises(snap.SnapshotError, match="nothing new"):
        snap.snapshot(repo, "S001", "S001: nothing;")
    with pytest.raises(snap.SnapshotError, match="must start"):
        snap.snapshot(repo, "S001", "no prefix")
    with pytest.raises(snap.SnapshotError, match="look like"):
        snap.snapshot(repo, "step1", "step1: x")
    (repo / "a.txt").write_text("two\n")
    snap.snapshot(repo, "S001", "S001: one;")
    (repo / "b.txt").write_text("b\n")
    snap.snapshot(repo, "S002", "S002: two;")
    with pytest.raises(snap.SnapshotError, match="newer snapshots"):
        snap.snapshot(repo, "S001", "S001: again;")
    snap.adopt(repo, "S001")
    snap.adopt(repo, "S002")
    with pytest.raises(snap.SnapshotError, match="already merged"):
        snap.snapshot(repo, "S001", "S001: again;")


def test_a_head_that_moved_another_way_leaves_the_old_snapshots_stale(repo):
    (repo / "a.txt").write_text("two\n")
    snap.snapshot(repo, "S001", "S001: one;")
    run(repo, "commit", "-q", "-am", "the user's own commit")
    (repo / "b.txt").write_text("b\n")
    result = snap.snapshot(repo, "S002", "S002: two;")
    assert result["parent"] == run(repo, "rev-parse", "HEAD")
    assert result["stale"] == ["S001"]
    assert [row[0] for row in snap.listing(repo)["stale"]] == ["S001"]


def test_adopt_moves_the_branch_and_keeps_the_working_files(repo):
    (repo / "a.txt").write_text("two\n")
    (repo / "new.txt").write_text("new\n")
    first = snap.snapshot(repo, "S001", "S001: one;")
    (repo / "later.txt").write_text("later\n")  # the next step's work, not yet snapshotted
    assert snap.adopt(repo, "S001") == first["commit"]
    assert run(repo, "rev-parse", "HEAD") == first["commit"]
    assert (repo / "later.txt").read_text() == "later\n"
    assert run(repo, "status", "--porcelain") == "?? later.txt"
    with pytest.raises(snap.SnapshotError, match="already merged"):
        snap.adopt(repo, "S001")


def test_adopt_refuses_staged_changes_and_a_moved_head(repo):
    (repo / "a.txt").write_text("two\n")
    snap.snapshot(repo, "S001", "S001: one;")
    (repo / "c.txt").write_text("c\n")
    run(repo, "add", "c.txt")
    with pytest.raises(snap.SnapshotError, match="staged"):
        snap.adopt(repo, "S001")
    run(repo, "commit", "-q", "-m", "the user's own commit")
    with pytest.raises(snap.SnapshotError, match="does not build on HEAD"):
        snap.adopt(repo, "S001")


def test_a_written_line_break_becomes_one(repo):
    (repo / "a.txt").write_text("two\n")
    snap.snapshot(repo, "S001", r"S001: one;\n\nCo-Authored-By: X <x@example.test>")
    assert run(repo, "log", "-1", "--format=%B", "refs/steps/S001") == "S001: one;\n\nCo-Authored-By: X <x@example.test>"
