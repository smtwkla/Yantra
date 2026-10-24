"""Step snapshots: one commit object per step at gate B, so the user can commit each step on its
own while the next step's coder carries on in the same working tree (decided 24-10-2026, KLA).

    python tooling/steps/step_snapshot.py snapshot S038 "S038: meters on models and equipment; v30;"
    python tooling/steps/step_snapshot.py list
    python tooling/steps/step_snapshot.py adopt S038

A snapshot is the whole working tree (tracked and untracked, .gitignore respected) written as a
commit under refs/steps/<step>, whose parent is the previous unmerged snapshot or HEAD. It never
touches HEAD, a branch, the user's index or the working files, and nothing is pushed.

``adopt`` makes a snapshot a commit of the current branch, oldest first: it checks that the
snapshot builds on HEAD and that nothing is staged, moves the branch to it and sets the index to
its files (``git reset --mixed``); the working files stay as they are.  A plain
``git merge --ff-only`` would refuse here, because the step's new files are still untracked.

Re-running ``snapshot`` for the newest unmerged step replaces it (a fix after gate B).  A step
already merged into HEAD, or one with a newer snapshot on top, is refused."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF_PREFIX = "refs/steps/"
STEP_ID = re.compile(r"^S\d{3}$")
WRITTEN_BREAK = "\\n"  # the two characters backslash and n


class SnapshotError(Exception):
    """A refusal with a message for the planner."""


def git(repo, *args, env=None):
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8",
                            env=env)
    if result.returncode != 0:
        raise SnapshotError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def is_ancestor(repo, older, newer):
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=repo,
                          capture_output=True).returncode == 0


def snapshots(repo):
    """[(step_id, sha, subject)] of every refs/steps/* ref, oldest first by commit time."""
    out = git(repo, "for-each-ref", "--sort=committerdate", "--format=%(refname:strip=2) %(objectname) %(subject)",
              REF_PREFIX)
    rows = []
    for line in out.splitlines():
        step_id, sha, *subject = line.split(" ", 2)
        rows.append((step_id, sha, subject[0] if subject else ""))
    return rows


def unmerged_chain(repo, head):
    """The unmerged snapshots that build on HEAD, oldest first; and the unmerged ones that don't."""
    on_head, stale = [], []
    for step_id, sha, subject in snapshots(repo):
        if is_ancestor(repo, sha, head):
            continue  # merged
        (on_head if is_ancestor(repo, head, sha) else stale).append((step_id, sha, subject))
    for (a_id, a_sha, _), (b_id, b_sha, _) in zip(on_head, on_head[1:]):
        if not is_ancestor(repo, a_sha, b_sha):
            raise SnapshotError(f"refs/steps/{a_id} and refs/steps/{b_id} do not form one chain; "
                                "merge or delete one before a new snapshot")
    return on_head, stale


def snapshot(repo, step_id, message):
    if not STEP_ID.match(step_id):
        raise SnapshotError(f"step id must look like S038, got {step_id!r}")
    if not message.startswith(f"{step_id}:"):
        raise SnapshotError(f"the message must start with '{step_id}:'")
    head = git(repo, "rev-parse", "HEAD")
    chain, stale = unmerged_chain(repo, head)
    ids = [row[0] for row in chain]
    existing = {row[0]: row[1] for row in snapshots(repo)}
    if step_id in existing and is_ancestor(repo, existing[step_id], head):
        raise SnapshotError(f"{step_id} is already merged into HEAD")
    if step_id in ids:
        if ids[-1] != step_id:
            raise SnapshotError(f"{step_id} has newer snapshots on top ({', '.join(ids[ids.index(step_id) + 1:])}); "
                                "it cannot be replaced")
        parent = git(repo, "rev-parse", f"{REF_PREFIX}{step_id}^")  # replace the tip
    else:
        parent = chain[-1][1] if chain else head

    index = Path(git(repo, "rev-parse", "--git-path", "step-snapshot-index"))
    if not index.is_absolute():
        index = Path(repo) / index
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    try:
        git(repo, "read-tree", parent, env=env)
        git(repo, "add", "-A", env=env)
        tree = git(repo, "write-tree", env=env)
    finally:
        index.unlink(missing_ok=True)
    if tree == git(repo, "rev-parse", f"{parent}^{{tree}}"):
        raise SnapshotError(f"nothing new since {parent[:7]}: the working tree matches it")
    # a .bat argument cannot hold a line break: a written backslash-n stands for one (the trailers)
    commit = git(repo, "commit-tree", tree, "-p", parent, "-m", message.replace(WRITTEN_BREAK, "\n"))
    git(repo, "update-ref", f"{REF_PREFIX}{step_id}", commit)
    stat = git(repo, "diff", "--stat", parent, commit).splitlines()
    return {"ref": f"{REF_PREFIX}{step_id}", "commit": commit, "parent": parent,
            "summary": stat[-1].strip() if stat else "", "stale": [row[0] for row in stale]}


def adopt(repo, step_id):
    existing = {row[0]: row[1] for row in snapshots(repo)}
    if step_id not in existing:
        raise SnapshotError(f"there is no snapshot of {step_id}")
    sha, head = existing[step_id], git(repo, "rev-parse", "HEAD")
    if is_ancestor(repo, sha, head):
        raise SnapshotError(f"{step_id} is already merged into HEAD")
    if not is_ancestor(repo, head, sha):
        raise SnapshotError(f"{step_id} does not build on HEAD (HEAD moved another way); re-snapshot it")
    if git(repo, "diff", "--cached", "--name-only"):
        raise SnapshotError("the index has staged changes; commit or unstage them first")
    git(repo, "reset", "-q", "--mixed", sha)
    return sha


def listing(repo):
    head = git(repo, "rev-parse", "HEAD")
    chain, stale = unmerged_chain(repo, head)
    merged = [row for row in snapshots(repo) if is_ancestor(repo, row[1], head)]
    return {"unmerged": chain, "stale": stale, "merged": merged}


def main(argv, repo=ROOT):
    try:
        if argv[:1] == ["snapshot"] and len(argv) == 3:
            r = snapshot(repo, argv[1], argv[2])
            print(f"{r['ref']} = {r['commit'][:7]} (parent {r['parent'][:7]}): {r['summary']}")
            if r["stale"]:
                print("note: unmerged snapshots that no longer build on HEAD: " + ", ".join(r["stale"]))
            print(f"adopt with: tooling/step-snapshot.bat adopt {argv[1]}")
            return 0
        if argv[:1] == ["adopt"] and len(argv) == 2:
            print(f"adopted {argv[1]}: HEAD is now {adopt(repo, argv[1])[:7]}")
            return 0
        if argv == ["list"]:
            r = listing(repo)
            print("unmerged, in order: " + (", ".join(f"{i} {s[:7]} {m}" for i, s, m in r["unmerged"]) or "none"))
            if r["stale"]:
                print("unmerged, not on HEAD (HEAD moved another way): " + ", ".join(i for i, _, _ in r["stale"]))
            print("merged: " + (", ".join(i for i, _, _ in r["merged"]) or "none"))
            return 0
        print(__doc__)
        return 2
    except SnapshotError as error:
        print(f"refused: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
