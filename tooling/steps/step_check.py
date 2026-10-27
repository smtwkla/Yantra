"""`/step check`: the step files checked against each other and git, read-only.  One line per
problem found; the orchestrator (the LLM) adds the judgements a script cannot make and proposes
the fixes.  Nothing is changed.

    python tooling/steps/step_check.py

The checks (the numbers are the skill's § Check):
 1. the brief's Status and its INDEX.md row are in the same stage;
 2. a commit names the step but the Status is not Committed or Done; a hash in the Status is
    not in git;
 3. Done, but an important check of the impl report is still open (`- [ ]`);
 4. Committed, every important check resolved, but not Done;
 5. every BR / BS finding of the brief reviews is answered in the brief;
 6. a step approved and not yet committed has a Baseline, and its commit exists;
 7. device-checks.md's Done column and the impl report's ticks agree (skipped without the file);
 8. every folder has an index row and every row a folder; no step ID is used twice;
 9. the files a stage needs exist (impl report, code review);
10. working-tree changes no step claims;
11. a step claim is dead (its session ended or went quiet), or claims a Done or Dropped step."""

import re
import sys

import step_claim
from step_facts import SHARED_DOCS, STEP_ID, STEPS_DIR, gather, header_value

# The stage a Status (or INDEX.md status cell) is in: its first words, in this order
STAGES = ("done", "dropped", "parked", "committed", "gate b", "gate a", "in code review", "implementing",
          "approved", "in review", "draft", "queued")
NOT_STARTED = ("draft", "in review", "gate a", "approved")
APPROVED_UNCOMMITTED = ("approved", "implementing", "in code review", "gate b")
HASH = re.compile(r"\b[0-9a-f]{7,40}\b")
OPEN_BOX = re.compile(r"^\s*- \[ \]", re.MULTILINE)
RESOLVED_BOX = re.compile(r"^\s*- \[(x|auto|skipped)\]", re.MULTILINE)
FINDING_HEADING = re.compile(r"^#{2,4}\s+(B[RS]\d+-\d+)\b", re.MULTILINE)
BRIEF_REVIEW = re.compile(r"^2-brief-review-[rs]\d+\.md$")


# ---------------------------------------------------------------------------------------------
# Pure checks (unit-tested)
# ---------------------------------------------------------------------------------------------

def stage(text):
    """A Status or a status cell -> its stage ("done", "gate a", …), or "" when unknown."""
    lowered = text.strip().lower()
    for name in STAGES:
        if lowered.startswith(name):
            return name
    return ""


def check_stage_matches_index(status, index_status):
    a, b = stage(status), stage(index_status)
    if a and b and a != b:
        return [f"INDEX row says \"{index_status[:70]}\", the brief says \"{status[:70]}\" (1)"]
    return []


def check_commits(status, commits, hashes):
    problems = []
    current = stage(status)
    if commits and current not in ("committed", "done", "dropped"):
        problems.append(f"commit {commits[0]} names the step, but the Status is \"{status[:60]}\" (2)")
    if current in ("committed", "done"):
        for short in HASH.findall(status):
            if not any(full.startswith(short) for full in hashes):
                problems.append(f"the Status names {short}, which is not in the current branch's history (2)")
    return problems


def check_manual_boxes(status, impl_text):
    """3 and 4, from the impl report's boxes: `- [ ]` is an important check still open."""
    if not impl_text:
        return []
    current, open_boxes = stage(status), len(OPEN_BOX.findall(impl_text))
    if current == "done" and open_boxes:
        return [f"Done, but the impl report has {open_boxes} open important check(s) `- [ ]` (3)"]
    if current == "committed" and not open_boxes:
        resolved = len(RESOLVED_BOX.findall(impl_text))
        return [f"Committed and no important check open ({resolved} resolved): set Done? (4)"]
    return []


def unanswered_findings(review_texts, brief_text):
    """The BR / BS finding IDs headed in the brief reviews that the brief never names."""
    ids = []
    for text in review_texts:
        ids += [i for i in FINDING_HEADING.findall(text) if i not in ids]
    return [i for i in ids if not re.search(rf"\b{re.escape(i)}\b", brief_text)]


def check_baseline(status, header, hashes):
    if stage(status) not in APPROVED_UNCOMMITTED:
        return []
    baseline = header_value(header, "Baseline")
    if not baseline:
        return ["approved and not committed, but the brief has no Baseline: line (6)"]
    return [f"Baseline names {short}, which is not in the current branch's history (6)"
            for short in HASH.findall(baseline) if not any(full.startswith(short) for full in hashes)]


def device_rows(text):
    """device-checks.md -> [(row number, [step ids], done cell)] of every table with a Step column."""
    rows, step_column = [], None
    for line in text.splitlines():
        if not line.startswith("|"):
            step_column = None if not line.strip() else step_column
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "Step" in cells:
            step_column = cells.index("Step")
        elif step_column is not None and cells and cells[0].isdigit():
            rows.append((cells[0], STEP_ID.findall(cells[step_column]), cells[-1]))
    return rows


def check_device_rows(step_id, status, impl_text, rows):
    """7: a row done while the report still has open boxes and no tick, or every row open while
    the report ticks a person's result."""
    mine = [(number, done) for number, steps, done in rows if step_id in steps]
    if not mine or not impl_text:
        return []
    done_rows = [number for number, done in mine if done]
    open_boxes = len(OPEN_BOX.findall(impl_text))
    ticked = len(re.findall(r"^\s*- \[(x|skipped)\]", impl_text, re.MULTILINE))
    if done_rows and open_boxes and not ticked:
        return [f"device-checks row(s) {', '.join(done_rows)} done, but the impl report ticks none (7)"]
    if ticked and not done_rows and stage(status) == "done":
        return [f"the impl report ticks {ticked} check(s), but device-checks row(s)"
                f" {', '.join(n for n, _ in mine)} have no Done (7)"]
    return []


def check_folders(index_folders, folders):
    """8: index rows without a folder, folders without a row, a step ID used twice."""
    problems = []
    for folder in index_folders:
        if folder not in folders:
            problems.append(f"the INDEX row's folder {folder} does not exist (8)")
    for folder in folders:
        if folder not in index_folders:
            problems.append(f"folder {folder} has no INDEX row (8)")
    seen = {}
    for folder in folders:
        seen.setdefault(folder[:4], []).append(folder)
    for step_id, names in seen.items():
        if len(names) > 1:
            problems.append(f"{step_id} is used by {len(names)} folders: {', '.join(names)} (8)")
    return problems


def check_claim(claim, live, reason, status):
    """Check 11 for one step claim: dead, or on a step that is closed."""
    problems = []
    if not live:
        problems.append(f"its claim is dead ({reason}): release it, or take it to carry on (11)")
    if stage(status) in ("done", "dropped"):
        problems.append(f"\"{stage(status)}\" but a claim is still held: release it (11)")
    return problems


def check_stage_files(status, names, has_impl_report):
    current = stage(status)
    problems = []
    if current in ("gate b", "committed", "done") and not has_impl_report:
        problems.append(f"\"{current}\" but there is no 3-impl-report.md (9)")
    if current == "gate b" and not any(n.startswith("4-code-review-") for n in names):
        problems.append("Gate B but there is no code review (9)")
    if current in NOT_STARTED and has_impl_report:
        problems.append(f"\"{current}\" but a 3-impl-report.md exists (9)")
    return problems


# ---------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------

def run():
    facts = gather()
    # A repo whose Device checks setting is none has no list: check 7 then has no rows to compare
    device_file = STEPS_DIR / "device-checks.md"
    rows = device_rows(device_file.read_text(encoding="utf-8")) if device_file.is_file() else []
    problems = []
    for step in facts.steps:
        if not step.has_brief:
            continue
        found = check_stage_matches_index(step.status, step.index_status)
        found += check_commits(step.status, step.commits, facts.hashes)
        found += check_manual_boxes(step.status, step.impl_text)
        reviews = [step.text(n) for n in step.names if BRIEF_REVIEW.match(n)]
        missing = unanswered_findings(reviews, step.text("1-brief.md")) if reviews else []
        if missing:
            found.append(f"brief-review finding(s) not answered in the brief: {', '.join(missing)} (5)")
        found += check_baseline(step.status, step.header, facts.hashes)
        found += check_device_rows(step.id, step.status, step.impl_text, rows)
        found += check_stage_files(step.status, step.names, step.has_impl_report)
        problems += [(step.id, p) for p in found]
    problems += [("index", p) for p in check_folders([s.folder for s in facts.steps], facts.folders)]
    problems += [("tree", f"{facts.changed[p]} {p}: no step claims it (10)") for p in facts.unclaimed]
    statuses = {step.id: step.status for step in facts.steps}
    me, now = step_claim.me_from_env(), step_claim.now_utc()
    for claim in step_claim.all_claims():
        live, reason = step_claim.liveness(claim, now, step_claim.owner_running(claim, me))
        problems += [(claim["step"], p) for p in check_claim(claim, live, reason, statuses.get(claim["step"], ""))]
    return problems, facts


def main(_argv):
    problems, facts = run()
    for where, problem in problems:
        print(f"{where}: {problem}")
    shared = [p for p in SHARED_DOCS if p in facts.changed]
    if shared:
        print(f"(shared step docs changed: {', '.join(shared)})")
    print(f"{len(problems)} problem(s) in {len(facts.steps)} steps" if problems
          else f"No problems found in {len(facts.steps)} steps.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
