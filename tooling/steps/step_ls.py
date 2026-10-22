"""`/step ls` facts in one run: what the step skill's § Listing table is built from, gathered
fast so the planner (the LLM) builds the table, adds notes and spots what is wrong — instead
of reading every step file one call at a time.

    python tooling/steps/step_ls.py          steps not yet Done or Dropped, and queued ones
    python tooling/steps/step_ls.py all      every step

Per step: the index title and folder, the brief's Status line, the latest review and its
verdict paragraph, the commits whose subject names the step, whether an impl report exists,
and the working-tree changes in the step's folder or among the files its impl report names.
Then the shared docs changed and the working-tree changes no step claims.  It judges
nothing: no bulb, no next action."""

import sys

from step_facts import SHARED_DOCS, gather, latest_review, verdict_line


def main(argv):
    show_all = "all" in argv
    facts = gather()
    for step in facts.steps:
        if not show_all and step.status.lower().startswith(("done", "dropped")):
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
    for step_id, idea in facts.queued:
        print(f"{step_id} | queued | {idea}")
    print("unclaimed working-tree changes:" + ("" if facts.unclaimed else " none"))
    for path in facts.unclaimed:
        print(f"  {facts.changed[path]} {path}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
