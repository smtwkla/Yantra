"""The step files and git, read once: the facts behind `/step ls` (step_ls.py) and `/step check`
(step_check.py).  Pure parsing functions first (unit-tested), then the one gather() that reads
the files and runs git twice (one log, one status)."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS_DIR = ROOT / "docs" / "steps"
# Files every step touches: listed once, not under each step
SHARED_DOCS = ("docs/steps/INDEX.md", "docs/steps/device-checks.md")
HEADER_LINES = 15                       # the header block is the brief's first lines
VERDICT_MAX = 300                       # a verdict paragraph is cut here; the review file has the rest

STEP_ID = re.compile(r"S\d{3}")
INDEX_ROW = re.compile(r"^\| (S\d{3}) \| \[([^\]]+)\]\(([^)/]+)/")
QUEUED_ROW = re.compile(r"^\| (S\d{3})\b")
# A commit subject's step prefix: "S018: …", "S025, S019, S020: …", "S007 + S008 - …"; leading
# spaces too (b6b8dfb), which `git log --grep "^S0NN"` misses
SUBJECT_STEPS = re.compile(r"^\s*((?:S\d{3}\s*[,+&/]?\s*(?:and\s+)?)+)[:;\-–]")
REVIEW_FILE = re.compile(r"^(2-brief-review|4-code-review)-([rs])(\d+)\.md$")
FILE_PATH = re.compile(r"`([\w.\-]+(?:/[\w.\-\[\]]+)+\.\w+)`")


# ---------------------------------------------------------------------------------------------
# Pure parsing
# ---------------------------------------------------------------------------------------------

def parse_index(text):
    """INDEX.md text -> ([(id, title, folder, status cell)] of the Index table, [(id, idea)] of the
    Queued table's rows that carry a step ID; ideas without one are left out)."""
    steps, queued, in_queued = [], [], False
    for line in text.splitlines():
        if line.startswith("## Queued"):
            in_queued = True
        if in_queued:
            if QUEUED_ROW.match(line):
                cell = line.split("|")[1].strip()
                queued.append((cell[:4], cell))
        else:
            match = INDEX_ROW.match(line)
            if match:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                steps.append((*match.groups(), cells[3] if len(cells) > 3 else ""))
    return steps, queued


def header_value(header_text, name):
    """A brief's first lines -> the value of its ``name:`` line ("" when there is none)."""
    for line in header_text.splitlines():
        if line.startswith(f"{name}:"):
            return line[len(name) + 1:].strip()
    return ""


def latest_review(names):
    """A folder's file names -> (file name, label such as "CR r2") of the latest review, or
    (None, ""). Code reviews come after brief reviews; a staleness round (sN) after the rN."""
    best, best_key = None, None
    for name in names:
        match = REVIEW_FILE.match(name)
        if match:
            kind, round_kind, number = match.groups()
            key = (kind == "4-code-review", round_kind == "s", int(number))
            if best_key is None or key > best_key:
                best, best_key = name, key
    if best is None:
        return None, ""
    return best, f"{'CR' if best_key[0] else 'BR'} {'s' if best_key[1] else 'r'}{best_key[2]}"


def verdict_line(review_text):
    """A review's text -> its verdict paragraph (the line with "Verdict" up to the next blank
    line), markup removed, on one line and cut at VERDICT_MAX ("" if none)."""
    lines = review_text.splitlines()
    for i, line in enumerate(lines):
        if "Verdict" in line:
            paragraph = []
            for part in lines[i:]:
                if not part.strip():
                    break
                paragraph.append(part.strip())
            text = re.sub(r"[*`]", "", " ".join(paragraph))
            return text if len(text) <= VERDICT_MAX else text[:VERDICT_MAX - 1] + "…"
    return ""


def subject_steps(subject):
    """A commit subject -> the step IDs its prefix names (none for "doc;" or "release v0.1.3")."""
    match = SUBJECT_STEPS.match(subject)
    return STEP_ID.findall(match.group(1)) if match else []


def impl_report_files(text):
    """The repo-relative file paths an impl report names in backticks."""
    return set(FILE_PATH.findall(text))


# ---------------------------------------------------------------------------------------------
# The shell: files and git
# ---------------------------------------------------------------------------------------------

@dataclass
class Step:
    id: str
    title: str
    folder: str
    index_status: str
    header: str = ""                    # the brief's header block ("" without a brief)
    status: str = ""
    names: list = field(default_factory=list)
    commits: list = field(default_factory=list)     # short hashes, newest first
    impl_text: str = ""                 # "" without an impl report
    has_impl_report: bool = False
    changed: list = field(default_factory=list)     # its folder's changes, and an uncommitted
                                                    # step's impl-report files that changed

    @property
    def path(self):
        return STEPS_DIR / self.folder

    @property
    def has_brief(self):
        return bool(self.header)

    def text(self, name):
        return (self.path / name).read_text(encoding="utf-8")


@dataclass
class Facts:
    steps: list
    queued: list
    changed: dict                       # path -> two-letter status
    unclaimed: list
    hashes: list                        # every full commit hash reachable from HEAD
    folders: list                       # every S0NN-* folder in docs/steps


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def changed_paths():
    """One git status -> {repo-relative path: two-letter status}, untracked files listed singly."""
    paths = {}
    for line in git("status", "--porcelain", "-uall").splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths[path] = line[:2].strip() or "M"
    return paths


def read_head(path, lines=HEADER_LINES):
    with open(path, encoding="utf-8") as fh:
        return "".join(fh.readline() for _ in range(lines))


def gather():
    """Every index step, read once (the brief's header, the folder's names, the impl report),
    with its commits and working-tree changes."""
    index, queued = parse_index((STEPS_DIR / "INDEX.md").read_text(encoding="utf-8"))
    commits, hashes = {}, []
    for line in git("log", "--format=%H %s").splitlines():
        full_hash, _, subject = line.partition(" ")
        hashes.append(full_hash)
        for step_id in subject_steps(subject):
            commits.setdefault(step_id, []).append(full_hash[:7])
    changed = changed_paths()
    steps, claimed = [], set(SHARED_DOCS)
    for step_id, title, folder, index_status in index:
        step = Step(step_id, title, folder, index_status, commits=commits.get(step_id, []))
        brief = step.path / "1-brief.md"
        if brief.exists():
            step.header = read_head(brief)
            step.status = header_value(step.header, "Status")
        step.names = sorted(p.name for p in step.path.iterdir()) if step.path.is_dir() else []
        impl = step.path / "3-impl-report.md"
        step.has_impl_report = impl.exists()
        step.impl_text = impl.read_text(encoding="utf-8") if step.has_impl_report else ""
        prefix = f"docs/steps/{folder}/"
        # A committed step's files may be changed again by a later step: only an uncommitted
        # step claims the files its impl report names
        impl_files = set()
        if step.has_impl_report and not step.commits:
            impl_files = impl_report_files(step.impl_text) - set(SHARED_DOCS)
        step.changed = sorted(p for p in changed if p.startswith(prefix) or p in impl_files)
        claimed |= set(step.changed)
        steps.append(step)
    folders = sorted(p.name for p in STEPS_DIR.iterdir() if p.is_dir() and STEP_ID.match(p.name))
    unclaimed = sorted(p for p in changed if p not in claimed)
    return Facts(steps, queued, changed, unclaimed, hashes, folders)
