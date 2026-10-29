"""`/step feedback` facts in one run: the `## Feedback` items the step agents write at the end of
their files (advice, brief reviews, impl reports, code reviews; 25-10-2026), so the orchestrator can
group what recurs and propose improvements.  It judges nothing.

    python tooling/steps/step_feedback.py              every step
    python tooling/steps/step_feedback.py S049 S054    only these steps
    python tooling/steps/step_feedback.py --new        only the items not yet in the feedback log
    python tooling/steps/step_feedback.py --rows       the same, as rows to paste into the log
    python tooling/steps/step_feedback.py --themes     the log's rows counted by theme

An item is a line `- <label>: <text>` under a heading whose text starts with "Feedback" (any level,
so a fix round's `### Feedback` counts too), up to the next heading of the same or a higher level.
An item may go on over indented lines (the files are wrapped at about 100 columns).
Labels: waste, hindrance, rule, idea; `- none` is counted, not listed.  A line with another label
is listed as `other`, so nothing an agent wrote is lost.

The feedback log (`docs/steps/feedback-log.md`, 27-10-2026) records what was decided on each item
read: a table row `| step | file | label | item | theme | decision |`.  An item is read when the log
holds a row with its step, file and text (spaces folded), or with the start of the text: rows
written before 29-10-2026 hold a wrapped item's first line only, as the tool then cut it there.  The text, not the file, is the
key, because a fix round adds new items to an impl report that was read before.

Themes (29-10-2026, from the advice on the agents' feedback): the theme cell is a short tag the
orchestrator writes at triage (`facts-path`, `shell-heredoc`, …), so items about one problem from
different steps can be counted.  `--themes` counts the rows per theme and their decisions, and
marks a theme whose last two decisions were `noted`: the skill asks for `acted` or `dropped` then.
A row of five cells (before 29-10-2026) has no theme."""

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS_DIR = ROOT / "docs" / "steps"
LOG = STEPS_DIR / "feedback-log.md"
CELL_SPLIT = re.compile(r"(?<!\\)\|")
AGENT_FILES = ("0-advice-*.md", "2-brief-review-*.md", "3-impl-report.md", "4-code-review-*.md")
LABELS = ("waste", "hindrance", "rule", "idea")
HEADING = re.compile(r"^(#{2,6})\s+(.*)$")
LOG_DATE = re.compile(r"^##\s+(\d{2}-\d{2}-\d{4})")
DECISION = re.compile(r"(?:^|;\s*)(acted|dropped|noted)\b")
ITEM = re.compile(r"^\s*-\s+`?(\w+)`?\s*(?::|—|-)?\s*(.*)$")


def feedback_items(text):
    """The (label, text) items of every Feedback section of one file; `none` items included.  An
    indented line after an item goes on with it."""
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
        if item:
            label = item.group(1).lower()
            items.append([label if label in LABELS + ("none",) else "other", item.group(2).strip() or line.strip()])
        elif items and line[:1].isspace() and line.strip():
            items[-1][1] += " " + line.strip()
    return [tuple(i) for i in items]


def step_folders(wanted):
    for folder in sorted(p for p in STEPS_DIR.glob("S[0-9][0-9][0-9]-*") if p.is_dir()):
        if not wanted or folder.name[:4] in wanted:
            yield folder


def item_key(step, file, text):
    return step.upper(), file, " ".join(text.split())


def log_rows(log_text):
    """Every table row whose first cell is a step ID -> (date of its section, its cells)."""
    date = ""
    for line in log_text.splitlines():
        heading = LOG_DATE.match(line)
        if heading:
            date = heading.group(1)
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in CELL_SPLIT.split(line.strip())[1:-1]]
        if len(cells) >= 4 and re.fullmatch(r"(?i)S\d{3}", cells[0]):
            yield date, cells


def read_keys(log_text):
    """The keys of the items the log holds."""
    return {item_key(cells[0], cells[1], cells[3]) for _, cells in log_rows(log_text)}


def is_read(keys, step, file, text):
    key = item_key(step, file, text)
    return key in keys or any(k[:2] == key[:2] and key[2].startswith(k[2]) for k in keys)


def log_row(step, file, label, text):
    """A log row for one item, the theme and decision cells left empty for the orchestrator."""
    return f"| {step} | {file} | {label} | {' '.join(text.split()).replace('|', chr(92) + '|')} |  |  |"


def themes(log_text):
    """The log's rows per theme -> lines: count, steps, decisions, and a mark when the last two
    decisions were `noted` (a problem that came back after it was read and left)."""
    found = {}
    for date, cells in log_rows(log_text):
        if len(cells) < 6 or not cells[4]:
            continue
        # A cell may hold a later decision after the first: "noted; acted 29-10-2026: …".
        decisions = DECISION.findall(cells[5].lower())
        decision = decisions[-1] if decisions else "undecided"
        found.setdefault(cells[4], []).append((date, cells[0].upper(), decision))
    lines = []
    for theme, rows in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        decisions = Counter(d for _, _, d in rows)
        steps = sorted({s for _, s, _ in rows})
        last = max((d for d, _, _ in rows), key=lambda d: d[6:] + d[3:5] + d[:2], default="")
        mark = "  ← noted twice: act or drop" if [d for _, _, d in rows][-2:] == ["noted", "noted"] else ""
        lines.append(f"{theme}: {len(rows)} item(s) in {len(steps)} step(s) ({', '.join(steps)}); "
                     + ", ".join(f"{k} ×{v}" for k, v in decisions.most_common())
                     + (f"; last {last}" if last else "") + mark)
    return lines or ["no row has a theme yet"]


def main(argv):
    wanted = {a.upper() for a in argv if re.fullmatch(r"(?i)S\d{3}", a)}
    log_text = LOG.read_text(encoding="utf-8") if LOG.is_file() else ""
    if "--themes" in argv:
        print("\n".join(themes(log_text)))
        return 0
    rows = "--rows" in argv
    only_new = rows or "--new" in argv
    keys = read_keys(log_text)
    counts = Counter()
    files_with = files_without = unread = listed = 0
    for folder in step_folders(wanted):
        step = folder.name[:4]
        files = sorted({f for pattern in AGENT_FILES for f in folder.glob(pattern)})
        for path in files:
            items = feedback_items(path.read_text(encoding="utf-8", errors="replace"))
            if not items:
                files_without += 1
                continue
            files_with += 1
            for label, text in items:
                counts[label] += 1
                if label == "none":
                    continue
                listed += 1
                is_new = not is_read(keys, step, path.name, text)
                unread += is_new
                if rows and is_new:
                    print(log_row(step, path.name, label, text))
                elif is_new or not only_new:
                    print(f"{step} | {path.name} | {label} | {text}")
    summary = ", ".join(f"{counts[k]} {k}" for k in LABELS + ("other", "none") if counts[k])
    print(f"items: {summary or 'none'}")
    print(f"unread: {unread} of {listed} (read = a row in {LOG.relative_to(ROOT).as_posix()}"
          f"{'' if LOG.is_file() else ', which does not exist yet'})")
    print(f"files with a Feedback section: {files_with}; without: {files_without}"
          " (files written before 25-10-2026 have none)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
