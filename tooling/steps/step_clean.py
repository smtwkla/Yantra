"""Housekeeping for finished steps: deletes what the step workflow leaves behind once a step is
Committed, Done or Dropped. The step's record in docs/steps/S0NN-*/ is never touched.

    python tooling/steps/step_clean.py                every finished step: list what would go
    python tooling/steps/step_clean.py S063 S064      the same for these steps
    python tooling/steps/step_clean.py ... --apply    delete it

What goes, per step:
  - the top-level entries of scratch/ (files and folders) whose name carries the step's id as a
    word: S063-brief-r1.md, brief-facts-S063.md, backend-tests-s063cr2.log, test-summary-s063c1.txt,
    s063cr1-build/, s063_edit1.py, s063/ (case does not matter). An entry with no step id is never
    deleted: scratch/preflight/, step-claims/, the mermaid cache, the user's own files;
  - the step's round refs, refs/step-rounds/S063-<n>;
  - its snapshot ref, refs/steps/S063, when it is merged into HEAD or stale (HEAD moved another
    way). A snapshot still waiting to be adopted is kept.

A step that is not Committed, Done or Dropped (its brief's Status line, else its index row) is skipped; named
on the command line, it makes the run exit 1. Exit 0 otherwise, 2 for a usage error."""

import re
import shutil
import stat
import sys
from pathlib import Path

import step_snapshot
from step_facts import ROOT, STEPS_DIR, header_value, parse_index, read_head

CLOSED = ("committed", "done", "dropped")   # committed: code in git, checks may still be open
STEP_ARG = re.compile(r"^S\d{3}$")


def step_pattern(step_id):
    """A scratch name carries the step id as a word: at the start or after - _ . and not followed by
    another digit (s063 is not s0631). Case-insensitive: run names are lower case (s063cr1)."""
    return re.compile(rf"(?:^|[-_.]){re.escape(step_id)}(?!\d)", re.IGNORECASE)


def scratch_entries(scratch, step_id):
    """The top-level scratch entries that belong to the step, sorted."""
    if not scratch.is_dir():
        return []
    pattern = step_pattern(step_id)
    return sorted(p for p in scratch.iterdir() if pattern.search(p.name))


def size_of(path):
    """(files, bytes) under a path, following no links."""
    if path.is_file() or path.is_symlink():
        return 1, path.lstat().st_size
    files = total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            files += 1
            total += item.stat().st_size
    return files, total


def step_statuses(steps_dir):
    """{step id: status} of every index step: the brief's Status line, else the index row's cell."""
    index = steps_dir / "INDEX.md"
    if not index.is_file():
        return {}
    statuses = {}
    for step_id, _title, folder, index_status in parse_index(index.read_text(encoding="utf-8"))[0]:
        brief = steps_dir / folder / "1-brief.md"
        status = header_value(read_head(brief), "Status") if brief.is_file() else ""
        statuses[step_id] = status or index_status
    return statuses


def is_closed(status):
    return status.strip("* ").lower().startswith(CLOSED)


def step_refs(repo, step_id):
    """(refs to delete, a note on a kept snapshot ref or "")."""
    refs = [f"{step_snapshot.ROUND_PREFIX}{step_id}-{n}" for n, _ in step_snapshot.rounds(repo, step_id)]
    snaps = {row[0]: row[1] for row in step_snapshot.snapshots(repo)}
    note = ""
    if step_id in snaps:
        head = step_snapshot.git(repo, "rev-parse", "HEAD")
        sha = snaps[step_id]
        merged = step_snapshot.is_ancestor(repo, sha, head)
        on_head = step_snapshot.is_ancestor(repo, head, sha)
        if merged or not on_head:
            refs.append(f"{step_snapshot.REF_PREFIX}{step_id}")
        else:
            note = f"kept {step_snapshot.REF_PREFIX}{step_id}: not adopted yet"
    return refs, note


def _make_writable_and_retry(func, path, *_):
    Path(path).chmod(stat.S_IWRITE)   # a read-only file (a copied .git object, an npm cache) on Windows
    func(path)


def delete(path):
    if path.is_dir() and not path.is_symlink():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_make_writable_and_retry)
        else:
            shutil.rmtree(path, onerror=_make_writable_and_retry)
    else:
        path.unlink()


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def clean(step_ids, statuses, scratch, repo, apply, named):
    """Lists (and with apply, deletes) each step's leftovers. -> (output lines, exit code)."""
    lines, code = [], 0
    total_entries = total_files = total_bytes = total_refs = 0
    for step_id in step_ids:
        status = statuses.get(step_id)
        if status is None or not is_closed(status):
            if named:
                lines.append(f"{step_id}: skipped, not Committed, Done or Dropped (status: {status or 'not in the index'})")
                code = 1
            continue
        entries = scratch_entries(scratch, step_id)
        files = size = 0
        for entry in entries:
            f, b = size_of(entry)
            files, size = files + f, size + b
        try:
            refs, note = step_refs(repo, step_id)
        except step_snapshot.SnapshotError as error:
            refs, note = [], f"refs not read ({error})"
        if not entries and not refs and not note:
            continue
        failed = []
        if apply:
            for entry in entries:
                try:
                    delete(entry)
                except OSError as error:
                    failed.append(f"{entry.name} ({error.strerror or error})")
            for ref in refs:
                step_snapshot.git(repo, "update-ref", "-d", ref)
        parts = [f"scratch {len(entries)} entries, {files} files, {human(size)}" if entries else "scratch nothing"]
        parts.append(f"{len(refs)} refs" if refs else "no refs")
        if note:
            parts.append(note)
        lines.append(f"{step_id}: " + "; ".join(parts))
        if not apply:
            lines.extend(f"  {e.name}{'/' if e.is_dir() else ''}" for e in entries)
            lines.extend(f"  {r}" for r in refs)
        for item in failed:
            lines.append(f"  NOT deleted: {item}")
            code = 1
        total_entries += len(entries)
        total_files += files
        total_bytes += size
        total_refs += len(refs)
    verb = "deleted" if apply else "would delete (dry run; add --apply)"
    lines.append(f"{verb}: {total_entries} scratch entries ({total_files} files, {human(total_bytes)}), "
                 f"{total_refs} refs")
    return lines, code


def main(argv, root=ROOT):
    apply = "--apply" in argv
    args = [a for a in argv if a != "--apply"]
    if any(not STEP_ARG.match(a) for a in args):
        print(__doc__)
        return 2
    statuses = step_statuses(root / STEPS_DIR.relative_to(ROOT))
    if not statuses:
        print("This repo has no docs/steps/INDEX.md (or no steps in it): nothing to clean.")
        return 0
    step_ids = args or sorted(statuses)
    lines, code = clean(step_ids, statuses, root / "scratch", root, apply, named=bool(args))
    if not args:
        others = untagged(root / "scratch")
        lines.append(f"not tied to a step, never deleted ({len(others)}; the user may delete by hand): "
                     + (", ".join(others) or "none"))
    print("\n".join(lines))
    return code


# The workflow's own lasting scratch entries: not listed as untagged.
KEEP = re.compile(r"^(preflight|step-claims|mermaid|__pycache__|e2e-.*|.*\.lock|step-stats\.md|"
                  r"dependency-report\.md)$")
ANY_STEP = re.compile(r"(?:^|[-_.])S\d{3}(?!\d)", re.IGNORECASE)


def untagged(scratch):
    """The top-level scratch names with no step id, less the workflow's own lasting entries."""
    if not scratch.is_dir():
        return []
    return sorted(p.name for p in scratch.iterdir() if not ANY_STEP.search(p.name) and not KEEP.match(p.name))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
