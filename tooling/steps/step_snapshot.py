"""Step snapshots: one commit object per step at gate B, so the user can commit each step on its
own while the next step's coder carries on in the same working tree (decided 24-10-2026, KLA).

    python tooling/steps/step_snapshot.py snapshot S038 "S038: meters on models and equipment; v30;"
    python tooling/steps/step_snapshot.py list
    python tooling/steps/step_snapshot.py adopt S038
    python tooling/steps/step_snapshot.py diff S038 [--stat] [--all] [-- <path>…]   the step's change so far
    python tooling/steps/step_snapshot.py diff S038 --from-round 1 [--stat] [--all] [-- <path>…]
                                                                the change since round 1
    python tooling/steps/step_snapshot.py diff [S038] --base <commit> [--stat] [--all] [-- <path>…]
                                                                the change since <commit>
    python tooling/steps/step_snapshot.py diff S038 --worktree [--from-round 1] [--stat] [--all] [-- <path>…]
                                    the working files against the snapshot (or round 1) itself;
                                    "working tree equals refs/steps/S038" and exit 0, else exit 1
    (any diff: --by-folder gives one line per top-level folder instead of the diff)
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
``--all`` shows everything; the last line of the output names what was left out.

Since 31-10-2026 (the agents' feedback): ``diff --base <commit>`` compares the working files with
any commit, the same way and with the same exclusions: for a step with no snapshot yet whose base
is not HEAD (a brief's baseline), or to override the step's base. The step id may then be left
out; ``--base`` and ``--from-round`` do not go together.

Since 02-11-2026 (6 feedback items, S094–S102): ``diff S038 --worktree`` asks whether the working
files still equal the step's snapshot (refs/steps/S038), or with ``--from-round n`` its round ref.
A reviewer's ``git diff refs/steps/S038`` compares with the index, so every untracked new file
showed as deleted. It is the same diff as above with the snapshot itself as the base: the same
tree of the working files, the same exclusions and path filters. It prints "working tree equals
refs/steps/S038" and exits 0 when nothing shown differs, else the diff and exits 1.
``--by-folder`` (any diff) prints one line per top-level folder instead: files, lines added and
removed."""

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


ROOT_FILES = "(top level)"   # --by-folder's name for the files at the repo's root


def diff_base(repo, step_id, from_round=None, base=None, worktree=False):
    """The commit a diff starts from: the commit ``base``, or the round named, or (``worktree``)
    the step's snapshot itself, or the step's base. -> (sha, the ref's name or None)."""
    if base is not None:
        try:
            return git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"), base
        except SnapshotError:
            raise SnapshotError(f"no such commit: {base}") from None
    if from_round is not None:
        found = dict(rounds(repo, step_id))
        if from_round not in found:
            raise SnapshotError(f"{step_id} has no round {from_round}; it has: "
                                + (", ".join(str(n) for n in found) or "none"))
        return found[from_round], f"{ROUND_PREFIX}{step_id}-{from_round}"
    if worktree:
        existing = {row[0]: row[1] for row in snapshots(repo)}
        if step_id not in existing:
            raise SnapshotError(f"there is no snapshot of {step_id}")
        return existing[step_id], f"{REF_PREFIX}{step_id}"
    return step_base(repo, step_id), None


def by_folder(numstat):
    """``git diff --numstat`` lines -> one line per top-level folder (files, +added -removed), then
    a total. A binary file counts as a file with no lines."""
    folders = {}
    for line in numstat.splitlines():
        added, removed, path = line.split("\t", 2)
        folder = path.split("/", 1)[0] + "/" if "/" in path else ROOT_FILES
        files, plus, minus = folders.get(folder, (0, 0, 0))
        folders[folder] = (files + 1, plus + int(added.replace("-", "0")), minus + int(removed.replace("-", "0")))
    if not folders:
        return ""
    width = max(len(name) for name in folders)
    lines = [f"{name.ljust(width)}  {files} file(s), +{plus} -{minus}" for name, (files, plus, minus) in
             sorted(folders.items())]
    total = [sum(values[i] for values in folders.values()) for i in range(3)]
    lines.append(f"{total[0]} file(s) in {len(folders)} folder(s), +{total[1]} -{total[2]}")
    return "\n".join(lines)


def compare(repo, base, tree, stat=False, paths=(), show_all=False, folders=False):
    """The diff from ``base`` to ``tree`` -> (the text shown, the left-out paths). The paths named,
    or everything (``show_all``), or everything but LEFT_OUT."""
    if paths or show_all:
        spec, left_out = list(paths or ["."]), []
    else:
        spec = [".", *(f":(exclude,glob){p}" for p in LEFT_OUT)]
        left_out = git(repo, "diff", "--name-only", base, tree, "--",
                       *(f":(glob){p}" for p in LEFT_OUT)).splitlines()
    if folders:
        # --no-renames: a rename's numstat path is "old => new", which names no one folder
        return by_folder(git(repo, "diff", "--numstat", "--no-renames", base, tree, "--", *spec)), left_out
    return git(repo, "diff", *(["--stat"] if stat else []), base, tree, "--", *spec), left_out


def with_note(shown, left_out):
    if not left_out:
        return shown
    note = (f"left out: {len(left_out)} file(s) of the step folders, docs/steps/INDEX.md, "
            "docs/steps/feedback-log.md or docs/roadmap/ (--all shows them)")
    return f"{shown}\n{note}" if shown else note


def diff(repo, step_id, from_round=None, stat=False, paths=(), show_all=False, base=None, folders=False):
    """The diff from the step's base (or the round named, or the commit ``base``) to the working
    files: the paths named, or everything (``show_all``), or everything but LEFT_OUT, with a last line
    that counts what was left out."""
    base, _ = diff_base(repo, step_id, from_round, base)
    return with_note(*compare(repo, base, working_tree(repo, base), stat, paths, show_all, folders))


def worktree_diff(repo, step_id, from_round=None, stat=False, paths=(), show_all=False, folders=False):
    """The working files against the step's snapshot (or the round named) itself -> (equal, text).
    Equal when nothing shown differs; the left-out files do not count, as in every diff."""
    base, ref = diff_base(repo, step_id, from_round, worktree=True)
    shown, left_out = compare(repo, base, working_tree(repo, base), stat, paths, show_all, folders)
    return not shown, with_note(shown or f"working tree equals {ref}", left_out)


def parse_diff_args(rest):
    """The arguments after ``diff S0NN``: [--stat] [--all] [--by-folder] [--worktree]
    [--from-round n | --base <commit>] [-- <path>…], in any order before the ``--``. Returns
    (stat, from_round, paths, show_all, base, worktree, folders), or None when an argument is wrong
    (``--worktree`` compares with the step's own snapshot or round, so not with ``--base``)."""
    paths = []
    if "--" in rest:
        cut = rest.index("--")
        rest, paths = rest[:cut], rest[cut + 1:]
    flags = ("--stat", "--all", "--worktree", "--by-folder")
    stat, show_all, worktree, folders = (flag in rest for flag in flags)
    rest = [a for a in rest if a not in flags]
    from_round = base = None
    if rest[:1] == ["--from-round"] and len(rest) == 2 and rest[1].isdigit():
        from_round, rest = int(rest[1]), []
    elif rest[:1] == ["--base"] and len(rest) == 2 and not rest[1].startswith("-") and not worktree:
        base, rest = rest[1], []
    return None if rest else (stat, from_round, paths, show_all, base, worktree, folders)


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
            # the step id may be left out with --base: the diff then needs no step's snapshot
            step_id, rest = (argv[1], argv[2:]) if STEP_ID.match(argv[1]) else (None, argv[1:])
            parsed = parse_diff_args(rest)
            if parsed is None or (step_id is None and parsed[4] is None):
                print(__doc__)
                return 2
            stat, from_round, paths, show_all, base, worktree, folders = parsed
            if worktree:   # a step id is there: --worktree never goes with --base
                equal, text = worktree_diff(repo, step_id, from_round, stat, paths, show_all, folders)
                print(text)
                return 0 if equal else 1
            print(diff(repo, step_id, from_round, stat, paths, show_all, base, folders))
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
