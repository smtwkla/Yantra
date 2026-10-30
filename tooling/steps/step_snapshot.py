"""Step snapshots: one commit object per step at gate B, so the user can commit each step on its
own while the next step's coder carries on in the same working tree (decided 24-10-2026, KLA).

    python tooling/steps/step_snapshot.py snapshot S038 "S038: meters on models and equipment; v30;"
    python tooling/steps/step_snapshot.py list
    python tooling/steps/step_snapshot.py adopt S038
    python tooling/steps/step_snapshot.py diff S038 [--stat] [--all] [-- <path>…]   the step's change so far
    python tooling/steps/step_snapshot.py diff S038 --from-round 1 [--stat] [--all] [-- <path>…]
                                                                the change since round 1
        (diff leaves out the step folders, docs/steps/INDEX.md, docs/steps/feedback-log.md and
        docs/roadmap/; --all shows them, and paths after -- replace that default)
    python tooling/steps/step_snapshot.py rounds S038

A snapshot is the whole working tree (tracked and untracked, .gitignore respected) written as a
commit under refs/steps/<step>, whose parent is the previous unmerged snapshot or HEAD. It never
touches HEAD, a branch, the user's index or the working files, and nothing is pushed.

``adopt`` makes a snapshot a commit of the current branch, oldest first: it checks that the
snapshot builds on HEAD and that nothing is staged, moves the branch to it and sets the index to
its files (``git reset --mixed``); the working files stay as they are.  A plain
``git merge --ff-only`` would refuse here, because the step's new files are still untracked.

Re-running ``snapshot`` for the newest unmerged step replaces it (a fix after gate B).  A step
already merged into HEAD, or one with a newer snapshot on top, is refused.

Rounds (27-10-2026, from the agents' feedback on S061 and S062): every ``snapshot`` also keeps its
commit as refs/step-rounds/<step>-<n>, n = 1, 2, … So when a fix round replaces the step's
snapshot, the earlier round is still there, and a verify review sees exactly the fix round's
change: ``diff S038 --from-round 1``. ``adopt`` removes the step's round refs.

``diff`` compares a tree of the working files (tracked and untracked, .gitignore respected, made
like a snapshot's, nothing written to the user's index) with the step's base: the snapshot it
builds on (or HEAD), or the round named. A plain ``git diff <ref>`` lists the step's untracked
files as deleted; this does not.

``diff`` leaves out the step's own folder, docs/steps/<step>-*/ (29-10-2026, from the agents'
feedback on S063 and S064): the reviewer reads the brief, the impl report and the reviews in full
anyway, and they were a third of a step's diff. Paths after ``--`` replace that default, e.g.
``diff S038 -- backend frontend``.

Since 30-10-2026 (16 feedback items): ``diff`` leaves out every step folder under docs/steps/,
docs/steps/INDEX.md, docs/steps/feedback-log.md and docs/roadmap/. The orchestrator edits other
steps' files while a coder works, so they land in the snapshot, but they are not the step's code.
The device-check list (docs/steps/device-checks.md) stays: a coder's docs pass adds rows to it.
``--all`` shows everything; the last line of the output names what was left out."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF_PREFIX = "refs/steps/"
ROUND_PREFIX = "refs/step-rounds/"
STEP_ID = re.compile(r"^S\d{3}$")
WRITTEN_BREAK = "\\n"  # the two characters backslash and n


class SnapshotError(Exception):
    """A refusal with a message for the orchestrator."""


def git(repo, *args, env=None):
    # errors="replace": a file with a byte that is not UTF-8 (a .bat with a cp1252 dash) must not stop
    # the diff.
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=env)
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


def working_tree(repo, base):
    """A tree object of the working files (tracked and untracked, .gitignore respected), built in
    a private index that starts from `base`; the user's index is not touched."""
    index = Path(git(repo, "rev-parse", "--git-path", "step-snapshot-index"))
    if not index.is_absolute():
        index = Path(repo) / index
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    try:
        git(repo, "read-tree", base, env=env)
        git(repo, "add", "-A", env=env)
        return git(repo, "write-tree", env=env)
    finally:
        index.unlink(missing_ok=True)


def rounds(repo, step_id):
    """[(round number, sha)] of the step's round refs, in round order."""
    out = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", f"{ROUND_PREFIX}{step_id}-*")
    found = []
    for line in out.splitlines():
        name, sha = line.split(" ", 1)
        number = name.rsplit("-", 1)[1]
        if number.isdigit():
            found.append((int(number), sha))
    return sorted(found)


def step_base(repo, step_id):
    """What the step builds on: its snapshot's parent, or the newest unmerged snapshot of another
    step, or HEAD."""
    existing = {row[0]: row[1] for row in snapshots(repo)}
    head = git(repo, "rev-parse", "HEAD")
    if step_id in existing and not is_ancestor(repo, existing[step_id], head):
        return git(repo, "rev-parse", f"{REF_PREFIX}{step_id}^")
    chain, _ = unmerged_chain(repo, head)
    others = [sha for i, sha, _ in chain if i != step_id]
    return others[-1] if others else head


# What ``diff`` leaves out by default: the workflow's own files, not the step's code.
LEFT_OUT = ("docs/steps/*/**", "docs/steps/INDEX.md", "docs/steps/feedback-log.md", "docs/roadmap/**")  # git globs


def diff(repo, step_id, from_round=None, stat=False, paths=(), show_all=False):
    """The diff from the step's base (or the round named) to the working files: the paths named, or
    everything (``show_all``), or everything but LEFT_OUT, with a last line that counts what was left
    out."""
    if from_round is None:
        base = step_base(repo, step_id)
    else:
        found = dict(rounds(repo, step_id))
        if from_round not in found:
            raise SnapshotError(f"{step_id} has no round {from_round}; it has: "
                                + (", ".join(str(n) for n in found) or "none"))
        base = found[from_round]
    tree = working_tree(repo, base)
    stat_flag = ["--stat"] if stat else []
    if paths or show_all:
        return git(repo, "diff", *stat_flag, base, tree, "--", *(paths or ["."]))
    shown = git(repo, "diff", *stat_flag, base, tree, "--", ".", *(f":(exclude,glob){p}" for p in LEFT_OUT))
    left_out = git(repo, "diff", "--name-only", base, tree, "--", *(f":(glob){p}" for p in LEFT_OUT)).splitlines()
    if not left_out:
        return shown
    note = (f"left out: {len(left_out)} file(s) of the step folders, docs/steps/INDEX.md, "
            "docs/steps/feedback-log.md or docs/roadmap/ (--all shows them)")
    return f"{shown}\n{note}" if shown else note


def parse_diff_args(rest):
    """The arguments after ``diff S0NN``: [--stat] [--all] [--from-round n] [-- <path>…], in any
    order before the ``--``. Returns (stat, from_round, paths, show_all), or None when an argument
    is wrong."""
    paths = []
    if "--" in rest:
        cut = rest.index("--")
        rest, paths = rest[:cut], rest[cut + 1:]
    stat, show_all = "--stat" in rest, "--all" in rest
    rest = [a for a in rest if a not in ("--stat", "--all")]
    from_round = None
    if rest[:1] == ["--from-round"] and len(rest) == 2 and rest[1].isdigit():
        from_round, rest = int(rest[1]), []
    return None if rest else (stat, from_round, paths, show_all)


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

    tree = working_tree(repo, parent)
    if tree == git(repo, "rev-parse", f"{parent}^{{tree}}"):
        raise SnapshotError(f"nothing new since {parent[:7]}: the working tree matches it")
    # a .bat argument cannot hold a line break: a written backslash-n stands for one (the trailers)
    commit = git(repo, "commit-tree", tree, "-p", parent, "-m", message.replace(WRITTEN_BREAK, "\n"))
    git(repo, "update-ref", f"{REF_PREFIX}{step_id}", commit)
    round_no = len(rounds(repo, step_id)) + 1
    git(repo, "update-ref", f"{ROUND_PREFIX}{step_id}-{round_no}", commit)
    stat = git(repo, "diff", "--stat", parent, commit).splitlines()
    return {"ref": f"{REF_PREFIX}{step_id}", "commit": commit, "parent": parent, "round": round_no,
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
    for number, _ in rounds(repo, step_id):
        git(repo, "update-ref", "-d", f"{ROUND_PREFIX}{step_id}-{number}")
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
            print(f"{r['ref']} = {r['commit'][:7]} (parent {r['parent'][:7]}, round {r['round']}): {r['summary']}")
            if r["stale"]:
                print("note: unmerged snapshots that no longer build on HEAD: " + ", ".join(r["stale"]))
            print(f"adopt with: tooling/step-snapshot.bat adopt {argv[1]}")
            return 0
        if argv[:1] == ["adopt"] and len(argv) == 2:
            print(f"adopted {argv[1]}: HEAD is now {adopt(repo, argv[1])[:7]}")
            return 0
        if argv[:1] == ["diff"] and len(argv) >= 2:
            parsed = parse_diff_args(argv[2:])
            if parsed is None:
                print(__doc__)
                return 2
            stat, from_round, paths, show_all = parsed
            print(diff(repo, argv[1], from_round, stat, paths, show_all))
            return 0
        if argv[:1] == ["rounds"] and len(argv) == 2:
            found = rounds(repo, argv[1])
            print(", ".join(f"{argv[1]}-{n} {s[:7]}" for n, s in found) or f"{argv[1]}: no rounds")
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
    # A Windows console or a redirected file is cp1252 by default; a brief's "→" stopped the diff
    # (S064 code reviews).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
