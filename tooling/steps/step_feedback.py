"""`/step feedback` facts in one run: the `## Feedback` items the step agents write at the end of
their files (advice, brief reviews, impl reports, code reviews; 25-10-2026), so the planner can
group what recurs and propose improvements.  It judges nothing.

    python tooling/steps/step_feedback.py            every step
    python tooling/steps/step_feedback.py S049 S054  only these steps

An item is a line `- <label>: <text>` under a heading whose text starts with "Feedback" (any level,
so a fix round's `### Feedback` counts too), up to the next heading of the same or a higher level.
Labels: waste, hindrance, rule, idea; `- none` is counted, not listed.  A line with another label
is listed as `other`, so nothing an agent wrote is lost."""

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS_DIR = ROOT / "docs" / "steps"
AGENT_FILES = ("0-advice-*.md", "2-brief-review-*.md", "3-impl-report.md", "4-code-review-*.md")
LABELS = ("waste", "hindrance", "rule", "idea")
HEADING = re.compile(r"^(#{2,6})\s+(.*)$")
ITEM = re.compile(r"^\s*-\s+`?(\w+)`?\s*(?::|—|-)?\s*(.*)$")


def feedback_items(text):
    """The (label, text) items of every Feedback section of one file; `none` items included."""
    items = []
    level = None                      # the heading level of the open Feedback section
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if heading.group(2).strip().lower().startswith("feedback"):
                level = depth
            elif level is not None and depth <= level:
                level = None
            continue
        if level is None:
            continue
        item = ITEM.match(line)
        if not item:
            continue
        label = item.group(1).lower()
        items.append((label if label in LABELS + ("none",) else "other", item.group(2).strip() or line.strip()))
    return items


def step_folders(wanted):
    for folder in sorted(p for p in STEPS_DIR.glob("S[0-9][0-9][0-9]-*") if p.is_dir()):
        if not wanted or folder.name[:4] in wanted:
            yield folder


def main(argv):
    wanted = {a.upper() for a in argv if re.fullmatch(r"(?i)S\d{3}", a)}
    counts = Counter()
    files_with = files_without = 0
    for folder in step_folders(wanted):
        files = sorted({f for pattern in AGENT_FILES for f in folder.glob(pattern)})
        for path in files:
            items = feedback_items(path.read_text(encoding="utf-8", errors="replace"))
            if not items:
                files_without += 1
                continue
            files_with += 1
            for label, text in items:
                counts[label] += 1
                if label != "none":
                    print(f"{folder.name[:4]} | {path.name} | {label} | {text}")
    summary = ", ".join(f"{counts[k]} {k}" for k in LABELS + ("other", "none") if counts[k])
    print(f"items: {summary or 'none'}")
    print(f"files with a Feedback section: {files_with}; without: {files_without}"
          " (files written before 25-10-2026 have none)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
