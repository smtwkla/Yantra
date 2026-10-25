"""Facts behind a brief's claims about the code, in one run (adopted 23-10-2026 from S029's
/step stats: most brief-review findings were facts the orchestrator had not checked — a constant
that already existed, a test the change breaks).  The orchestrator runs it before review round 1
and fixes the brief from it; the brief reviewer gets the output and verifies the brief's
claims from it instead of finding each one again.

    python tooling/steps/brief_facts.py S029                   the step's 1-brief.md
    python tooling/steps/brief_facts.py docs/steps/…/1-brief.md

Reads every `backticked` reference in the brief:
  - a file path (with an optional :line or :from-to): exists, and has that many lines;
  - a bare file name (`screens.spec.js`): where files of that name are;
  - a test id (file::Class::name): the file exists and names it;
  - an API route (/api/…): the test files that call it;
  - a code name (snake_case, CamelCase, CONSTANT, dotted module.name): where it is defined,
    how many other code files use it, and which test files use it.
Plain words in backticks (`down`, `critical`) are skipped: too common to grep usefully.
It judges nothing: "not found" may be right for a name the brief says is new.
Writes the same text to scratch/brief-facts-<step>.md."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS_DIR = ROOT / "docs" / "steps"
SEARCH_DIRS = ("backend", "frontend/src", "frontend/e2e", "frontend/tests", "tooling")
MAX_LISTED = 8                          # files or lines listed per name; the count says the rest

BACKTICKED = re.compile(r"`([^`\n]+)`")
PATH = re.compile(r"^([\w.\-]+(?:/[\w.\-\[\]]+)*\.\w+)(?::(\d+)(?:-(\d+))?)?$")
TEST_ID = re.compile(r"^([\w.\-/]*\w)::([\w:]+)$")
ROUTE = re.compile(r"^(?:(?:GET|POST|PUT|PATCH|DELETE) )?(/api/[\w\-/<>]+)")
BARE_FILE = re.compile(r"^[\w.\-]+\.(py|js|vue|md|bat|json|ya?ml|sql|toml)$")
CALL = re.compile(r"^([A-Za-z_][\w.]*)\(")
NAME = re.compile(r"^[A-Za-z_][\w.]*$")
# Worth grepping: has an underscore, an inner capital, or a dot (module.name); not a plain word
DISTINCT_NAME = re.compile(r"_|[a-z][A-Z]|\.")
TEST_PATH = re.compile(r"(^|/)(tests|e2e)/|(^|/)test_|\.(spec|test)\.\w+$")


@dataclass(frozen=True)
class Ref:
    kind: str           # path | file (a bare file name) | test | route | name
    value: str
    first_line: int = 0
    last_line: int = 0


# ---------------------------------------------------------------------------------------------
# Pure parsing
# ---------------------------------------------------------------------------------------------

def classify(token):
    """One backticked text -> a Ref, or None when it is not worth checking."""
    token = token.strip()
    match = TEST_ID.match(token)
    if match and "/" in match.group(1) or (match and "." in match.group(1)):
        return Ref("test", token)
    match = PATH.match(token)
    if match and "/" in match.group(1):
        first = int(match.group(2) or 0)
        return Ref("path", match.group(1), first, int(match.group(3) or first))
    if BARE_FILE.match(token):
        return Ref("file", token)
    match = ROUTE.match(token)
    if match:
        return Ref("route", match.group(1).rstrip("/"))
    match = CALL.match(token)
    name = match.group(1) if match else token
    if NAME.match(name) and DISTINCT_NAME.search(name) and not name.endswith("."):
        return Ref("name", name)
    return None


def extract_refs(text):
    """Brief text -> its distinct Refs, in order of first mention."""
    seen, refs = set(), []
    for token in BACKTICKED.findall(text):
        ref = classify(token)
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def is_test_path(path):
    return bool(TEST_PATH.search(path))


def definition_pattern(name):
    """A regex for the lines that define ``name`` (Python or JavaScript)."""
    word = re.escape(name)
    return re.compile(rf"(def|class|function|const|let|var)\s+{word}\b|^\s*{word}\s*=[^=]|"
                      rf"export\s+(default\s+)?(async\s+)?(function|const|class)\s+{word}\b")


def summarise_hits(name, hits):
    """git grep lines ("path:line:text") for ``name`` -> its report lines."""
    short = name.rsplit(".", 1)[-1]
    defines = definition_pattern(short)
    definitions, code_files, test_files = [], [], []
    for hit in hits:
        path, line, text = (hit.split(":", 2) + ["", ""])[:3]
        if defines.search(text):
            definitions.append(f"{path}:{line}")
        if is_test_path(path):
            if path not in test_files:
                test_files.append(path)
        elif path not in code_files:
            code_files.append(path)
    if not hits:
        return [f"- `{name}`: not found"]
    module = next((f"{d}/{short}.py" for d in ("backend", "tooling/steps") if (ROOT / d / f"{short}.py").is_file()), None)
    where = f"a module ({module})" if module else (listing(definitions) or "none found")
    lines = [f"- `{name}`: defined at {where}"]
    lines.append(f"  - used in {len(code_files)} code file(s): {listing(code_files) or '—'}")
    lines.append(f"  - used in {len(test_files)} test file(s): {listing(test_files) or '—'}")
    return lines


def listing(items):
    shown = ", ".join(items[:MAX_LISTED])
    return shown + (f", … (+{len(items) - MAX_LISTED})" if len(items) > MAX_LISTED else "")


# ---------------------------------------------------------------------------------------------
# Files and git
# ---------------------------------------------------------------------------------------------

def grep(pattern, fixed=True, word=True, dirs=SEARCH_DIRS):
    """Tracked and untracked (not ignored) files under ``dirs`` -> 'path:line:text' lines."""
    args = ["git", "grep", "-n", "-I", "--untracked"]
    args += ["-F"] if fixed else ["-E"]
    args += ["-w"] if word else []
    args += ["-e", pattern, "--", *dirs]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode > 1:            # 1 = no match
        raise RuntimeError(result.stderr.strip())
    return [line for line in result.stdout.splitlines() if "__pycache__" not in line]


def check_path(ref):
    path = ROOT / ref.value
    if not path.is_file():
        return [f"- `{ref.value}`: **no such file**"]
    count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if ref.last_line > count:
        return [f"- `{ref.value}`: **has {count} lines**, the brief cites line {ref.last_line}"]
    return [f"- `{ref.value}`: exists ({count} lines)"]


def check_file(ref):
    """A bare file name -> where files of that name are (tracked or untracked, not ignored)."""
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", f"*/{ref.value}",
                             ref.value], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    found = sorted(set(result.stdout.split()))
    return [f"- `{ref.value}`: " + (listing(found) if found else "**no file of that name**")]


def check_test(ref):
    file_part, names = ref.value.split("::", 1)
    candidates = [p for p in (ROOT / file_part, ROOT / "backend" / file_part, ROOT / "backend/tests" / file_part)
                  if p.is_file()]
    if not candidates:
        return [f"- `{ref.value}`: **no such test file**"]
    text = candidates[0].read_text(encoding="utf-8", errors="replace")
    missing = [n for n in names.split("::") if not re.search(rf"\b{re.escape(n)}\b", text)]
    return [f"- `{ref.value}`: " + (f"**not found: {', '.join(missing)}**" if missing else "exists")]


def test_files_naming(text):
    return sorted({hit.split(":", 1)[0] for hit in grep(text, word=False) if is_test_path(hit.split(":", 1)[0])})


def check_route(ref):
    """Tests often build a route from a constant (f"{EQUIPMENT}/asset-list"), so when the whole
    route is in no test file, its last segment is looked for instead, and the line says so."""
    prefix = re.sub(r"/?<[^>]+>.*$", "", ref.value)
    files, how = test_files_naming(prefix), ""
    last = "/" + prefix.rsplit("/", 1)[-1]
    if not files and last != prefix and last != "/api":
        files, how = test_files_naming(last), f" (by its last segment `{last}`)"
    return [f"- `{ref.value}`: called in {len(files)} test file(s){how}: {listing(files) or '—'}"]


def check_name(ref):
    module, _, short = ref.value.rpartition(".")
    hits = grep(short)
    if module:
        own = [h for h in hits if Path(h.split(":", 1)[0]).stem == module.rsplit(".", 1)[-1]]
        hits = own or hits
    return summarise_hits(ref.value, hits)


CHECKS = {"path": check_path, "file": check_file, "test": check_test, "route": check_route, "name": check_name}
SECTIONS = (("path", "Files"), ("file", "Files named without a folder"), ("test", "Test ids"), ("route", "Routes"), ("name", "Code names"))


def brief_path(arg):
    if re.fullmatch(r"S\d{3}", arg):
        found = sorted(STEPS_DIR.glob(f"{arg}-*/1-brief.md"))
        if not found:
            raise SystemExit(f"No brief for {arg} under docs/steps.")
        return found[0]
    return Path(arg).resolve()


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = brief_path(argv[0])
    refs = extract_refs(path.read_text(encoding="utf-8"))
    out = [f"# Brief facts — {path.relative_to(ROOT).as_posix()}", "",
           "Facts only: \"not found\" is right for a name the brief says is new.", ""]
    for kind, title in SECTIONS:
        group = [r for r in refs if r.kind == kind]
        if group:
            out += [f"## {title}", ""]
            for ref in group:
                out += CHECKS[kind](ref)
            out.append("")
    text = "\n".join(out)
    step = re.match(r"S\d{3}", path.parent.name)
    report = ROOT / "scratch" / f"brief-facts-{step.group(0) if step else 'brief'}.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text(text, encoding="utf-8")
    print(text)
    print(f"(written to {report})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
