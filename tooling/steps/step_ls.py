"""`/step ls` facts in one run: what the step skill's § Listing table is built from, gathered
fast so the orchestrator (the LLM) builds the table, adds notes and spots what is wrong — instead
of reading every step file one call at a time.

    python tooling/steps/step_ls.py           steps not yet Done, Dropped or parked, and queued ones
    python tooling/steps/step_ls.py deferred  only the parked (deferred) steps
    python tooling/steps/step_ls.py all       every step

Per step: the index title and folder, the brief's Status line, the latest review and its
verdict paragraph, the commits whose subject names the step, whether an impl report exists,
and the working-tree changes in the step's folder or among the files its impl report names.
Then the shared docs changed, the step snapshots not yet adopted (refs/steps/), the step claims
(which session works on which step, live or dead; tooling/steps/step_claim.py), and the
working-tree changes no step claims.  It judges
nothing: no bulb, no next action."""

import sys

import step_claim
import step_snapshot
from step_facts import ROOT, SHARED_DOCS, gather, latest_review, verdict_line


CLOSED = ("done", "dropped")
PARKED = ("parked", "deferred")   # set aside by the user; the brief is kept for later


def shown(status, argv):
    """Whether a step with this Status line is listed: `all` lists every step, `deferred` only the
    parked ones, and no argument the open ones (not Done, Dropped or parked)."""
    if "all" in argv:
        return True
    state = status.lower()
    if "deferred" in argv:
        return state.startswith(PARKED)
    return not state.startswith(CLOSED + PARKED)


def main(argv):
    facts = gather()
    for step in facts.steps:
        if not shown(step.status, argv):
            continue
        review, label = latest_review(step.names)
        print(f"{step.id} | {step.title} | {step.folder}")
        print(f"  status: {step.status or '(no brief)'}")
        print(f"  review: {f'{label} — {verdict_line(step.text(review))}' if review else 'none'}")
        print(f"  commits: {', '.join(step.commits) or 'none'}")
        print(f"  impl report: {'yes' if step.has_impl_report else 'no'}")
        if step.changed:
            print(f"  working tree: {', '.join(f'{facts.changed[p]} {p}' for p in step.changed)}")
    shared = [p for p in SHARED_DOCS if p in facts.changed]
    print("shared step docs changed: " + (", ".join(shared) or "none"))
    only_parked = "deferred" in argv and "all" not in argv
    for step_id, idea in facts.queued if not only_parked else []:
        print(f"{step_id} | queued | {idea}")
    try:
        snaps = step_snapshot.listing(ROOT)
        print("snapshots not adopted (refs/steps/, oldest first): "
              + (", ".join(f"{i} {s[:7]}" for i, s, _ in snaps["unmerged"]) or "none"))
        if snaps["stale"]:
            print("  stale (HEAD moved another way): " + ", ".join(i for i, _, _ in snaps["stale"]))
    except step_snapshot.SnapshotError as error:
        print(f"snapshots: could not read ({error})")
    print("step claims (sessions at work):")
    for line in step_claim.cmd_show(None, step_claim.me_from_env()).splitlines():
        print(f"  {line}")
    print("unclaimed working-tree changes:" + ("" if facts.unclaimed else " none"))
    for path in facts.unclaimed:
        print(f"  {facts.changed[path]} {path}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
