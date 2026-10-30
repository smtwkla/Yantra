"""Facts behind a brief's claims about the code, in one run (adopted 23-10-2026 from S029's
/step stats: most brief-review findings were facts the orchestrator had not checked — a constant
that already existed, a test the change breaks).  The orchestrator runs it before review round 1
and fixes the brief from it; the brief reviewer gets the output and verifies the brief's
claims from it instead of finding each one again.

    python tooling/steps/brief_facts.py S029                   the step's 1-brief.md
    python tooling/steps/brief_facts.py docs/steps/…/1-brief.md

Reads every `backticked` reference in the brief:
  - a file path (with an optional :line or :from-to): exists, and has that many lines; a path not
    at the root is looked for as the end of a longer path (the brief named its folder in prose);
    one row per file, the highest line cited;
  - a bare file name (`screens.spec.js`): where files of that name are;
  - a test id (file::Class::name): the file exists and names it;
  - an API route (/api/…): the test files that call it;
  - a code name (snake_case, CamelCase, CONSTANT, dotted module.name): where it is defined,
    how many other code files use it, and which test files use it;
  - screen text in double quotes inside the backticks (`"Print asset list"`): the test lines that
    use it, so a step that hides, renames or moves a control sees the tests it breaks.
Plain words in backticks (`down`, `critical`) are skipped: too common to grep usefully.
It judges nothing: "not found" may be right for a name the brief says is new.

Since 30-10-2026 (the agents' feedback, 23 items):
  - *Cited lines*: every path:NN or path:NN-MM in the brief, in backticks or not, with the line's
    text now; when the sentence names a code name that is not on that line, where the file
    defines it now ("moved? now :NN") — anchors move when a brief is planned ahead of its
    dependencies;
  - a route matches a test line only by its whole shape, a placeholder matching one segment; the
    test file's own route constants (EQUIPMENT = "/api/equipment") are put into the line first;
  - a dotted name is looked up only when <module>.py in the code folders defines it at top level;
    else it is listed as a table.column or attribute, not looked up;
  - the names found nowhere go in one line, with "(planned in S0NN)" when their sentence names
    another step; a name in more than 10 test files lists 3 files only;
  - screen text is looked for in the frontend test files only.
Writes the same text to scratch/brief-facts-<step>.md.

The folders searched are the repo's `Code folders` setting (.claude/CLAUDE.md § Step workflow);
without it, the whole repo except docs/."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from step_facts import ROOT, STEPS_DIR, backticked, load_step_settings

STEP_TOOLS_DIR = "tooling/steps"          # the step tools sync to every repo: modules are looked up here too
MAX_LISTED = 8                          # files or lines listed per name; the count says the rest
COMMON_TEST_FILES = 10                  # a name in more test files than this is common: ...
COMMON_LISTED = 3                       # ... its lists show this many files
MAX_LINE_TEXT = 160                     # characters of a cited line shown
FRONTEND_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".vue")   # screen text is tested here

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
UI_TEXT = re.compile(r'^"([^"\n]{2,60})"$')
# path:NN or path:NN-MM anywhere in the text; the extension starts with a letter, so 127.0.0.1:5002 is no path
CITED = re.compile(r"(?<![\w./\-])((?:[\w.\-]+/)*[\w.\-]+\.[A-Za-z]\w*):(\d+)(?:-(\d+))?(?!\d)")
STEP_MENTION = re.compile(r"\bS\d{3}\b")
# EQUIPMENT = "/api/equipment", const BASE = `/api/x`, REGISTER = f"{IMPROVEMENTS}/register"
ROUTE_CONSTANT = re.compile(r"^\s*(?:export\s+)?(?:const\s+)?([A-Z][A-Z0-9_]*)\s*=\s*f?[\"'`]([^\"'`\n]*)[\"'`]", re.M)
# A paragraph ends at a blank line or before a heading, list item or table row
PARAGRAPH_BREAK = re.compile(r"\n\s*\n|\n(?=\s*(?:#|[-*] |\d+\. |\|))")
SENTENCE_END = re.compile(r"(?<=[.!?])(?<!\d\.)\s+")   # not after "1." of a numbered item


@dataclass(frozen=True)
class Ref:
    kind: str           # path | file (a bare file name) | test | route | name | ui (screen text)
    value: str
    first_line: int = 0
    last_line: int = 0


# ---------------------------------------------------------------------------------------------
# Pure parsing
# ---------------------------------------------------------------------------------------------

def classify(token):
    """One backticked text -> a Ref, or None when it is not worth checking."""
    token = token.strip()
    # Opt-in by form (29-10-2026, S064's feedback): a scan of every quoted text in a brief found
    # "No" and "Save" in hundreds of lines.
    match = UI_TEXT.match(token)
    if match:
        return Ref("ui", match.group(1))
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
    if NAME.match(name) and DISTINCT_NAME.search(name) and not name.endswith(".") and greppable(name):
        return Ref("name", name)
    return None


def greppable(name):
    """Whether grepping the name finds its own uses (S062's feedback, 27-10-2026): a lone `_` has
    no letter, and `Thing.open` is grepped by its last part, a plain word in dozens of files."""
    if not re.search(r"[A-Za-z0-9]", name):
        return False
    short = name.rpartition(".")[2]
    return "." not in name or bool(DISTINCT_NAME.search(short)) or (short.isupper() and len(short) >= 4)


def extract_refs(text):
    """Brief text -> its distinct Refs, in order of first mention.  A file cited at several lines
    is one Ref with the highest line, since only that one is checked (S057, S058 feedback)."""
    found = {}
    for token in BACKTICKED.findall(text):
        ref = classify(token)
        if not ref:
            continue
        key = (ref.kind, ref.value)
        if key not in found or ref.last_line > found[key].last_line:
            found[key] = ref
    return list(found.values())


def sentences(text):
    """Brief text -> its sentences.  A brief wraps a sentence over several lines, so each paragraph
    (or list item, or table row) is joined into one line first."""
    found = []
    for paragraph in PARAGRAPH_BREAK.split(text.replace("\r\n", "\n")):
        found += [s for s in SENTENCE_END.split(" ".join(paragraph.split())) if s]
    return found


def citations(text):
    """Brief text -> {(path, first, last): [code names its sentences name]}, in order of first
    mention.  The names are the backticked code names of each sentence that cites the line."""
    found = {}
    for sentence in sentences(text):
        names = names_in(sentence)
        for path, first, last in CITED.findall(sentence):
            key = (path, int(first), int(last or first))
            found.setdefault(key, [])
            found[key] += [n for n in names if n not in found[key]]
    return found


def names_in(sentence):
    """The backticked code names of a sentence, by their last part (`tickets.load` -> load)."""
    refs = [classify(token) for token in BACKTICKED.findall(sentence)]
    return [ref.value.rpartition(".")[2] for ref in refs if ref and ref.kind == "name"]


def planned_in(name, all_sentences, own_step=None):
    """' (planned in S070)' when a sentence that names `name` also names another step, else ''."""
    steps = []
    for sentence in all_sentences:
        if f"`{name}" in sentence:
            steps += [s for s in STEP_MENTION.findall(sentence) if s != own_step and s not in steps]
    return f" (planned in {', '.join(steps)})" if steps else ""


def route_shape(route):
    """A route -> a regex for the test lines that call it: the same segments, and a placeholder
    (<id>) matching any one segment (5, ${id}, {node['id']}).  Nothing may follow the last segment
    but its end.  A line that builds the route on a constant is expanded first (expand_constants)."""
    one = r"(?:\$?\{[^}]*\}|[^/\s\"'`?#{}]+)"
    parts = [one if s.startswith("<") else re.escape(s) for s in route.strip("/").split("/")]
    return re.compile(rf"/{'/'.join(parts)}(?![\w/\-])")


def route_constants(text):
    """A test file's constants that hold a route, {NAME: value}; a value built on another constant
    of the file is expanded (SITES = f"{MASTERS}/sites")."""
    found = dict(ROUTE_CONSTANT.findall(text))
    return {name: expand_constants(value, found) for name, value in found.items()}


def expand_constants(line, constants):
    """{NAME} and ${NAME} of the constants given -> their values; others stay as written."""
    return re.sub(r"\$?\{([A-Z][A-Z0-9_]*)\}", lambda m: constants.get(m.group(1), m.group(0)), line)


def is_test_path(path):
    return bool(TEST_PATH.search(path))


def is_frontend_test(path):
    return is_test_path(path) and path.endswith(FRONTEND_SUFFIXES)


def definition_pattern(name):
    """A regex for the lines that define ``name`` (Python or JavaScript)."""
    word = re.escape(name)
    return re.compile(rf"(def|class|function|const|let|var)\s+{word}\b|^\s*{word}\s*=[^=]|"
                      rf"export\s+(default\s+)?(async\s+)?(function|const|class)\s+{word}\b")


def summarise_hits(name, hits, folders=None):
    """git grep lines ("path:line:text") for ``name`` -> its report lines.  A module ``name.py``
    is looked up in each code folder (``folders``), then in the step tools' folder."""
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
    module = module_file(short, folders)
    where = f"a module ({module})" if module else (listing(definitions) or "none found")
    # A name in many test files is a common one (updated_at, class_id): three files say enough
    limit = COMMON_LISTED if len(test_files) > COMMON_TEST_FILES else MAX_LISTED
    lines = [f"- `{name}`: defined at {where}"]
    lines.append(f"  - used in {len(code_files)} code file(s): {listing(code_files, limit) or '—'}")
    lines.append(f"  - used in {len(test_files)} test file(s): {listing(test_files, limit) or '—'}")
    return lines


def module_file(name, folders=None):
    """`name.py` in a code folder, then in the step tools' folder, or None."""
    return next((f"{d}/{name}.py" for d in (*(folders or ()), STEP_TOOLS_DIR) if (ROOT / d / f"{name}.py").is_file()),
                None)


def listing(items, limit=MAX_LISTED):
    shown = ", ".join(items[:limit])
    return shown + (f", … (+{len(items) - limit} more)" if len(items) > limit else "")


def defines_at_top(text, name):
    """Whether module text defines ``name`` at top level: a def, a class or an assignment."""
    word = re.escape(name)
    return bool(re.search(rf"^(?:async\s+def|def|class)\s+{word}\b|^{word}\s*(?::[^=\n]*)?=(?!=)", text, re.M))


def cited_row(lines, first, last, names):
    """One citation of a file's ``lines`` -> its report text: the line now (for a range, the first
    line and the count), and for each code name of its sentence not on those lines, where the file
    defines it now."""
    spot = f":{first}" if first == last else f":{first}-{last} ({last - first + 1} lines)"
    if not 1 <= first <= len(lines):
        return f"{spot} **past the end**"
    row = f"{spot} {code_span(lines[first - 1])}"
    if last > len(lines):
        row += f" **(the file ends at line {len(lines)})**"
    cited = "\n".join(lines[first - 1:last])
    notes, absent = [], []
    for name in names:
        note = name_note(lines, cited, name)
        if note == NOT_IN_FILE:
            absent.append(f"`{name}`")
        elif note:
            notes.append(note)
    if absent:                           # one note: a sentence often names several files' names
        notes.append(f"{', '.join(absent)} not in file")
    return row + "".join(f"; {note}" for note in notes)


NOT_IN_FILE = "not in file"


def name_note(lines, cited, name):
    """None when ``name`` is on the cited lines; else where the file defines it (or first uses
    it), or NOT_IN_FILE."""
    word = re.compile(rf"\b{re.escape(name)}\b")
    if word.search(cited):
        return None
    defines = definition_pattern(name)
    defined = next((i for i, line in enumerate(lines, 1) if defines.search(line)), None)
    if defined:
        return f"`{name}` moved? now :{defined}"
    used = next((i for i, line in enumerate(lines, 1) if word.search(line)), None)
    return f"`{name}` moved? first used at :{used}" if used else NOT_IN_FILE


def code_span(line):
    text = line.strip()
    if not text:
        return "(blank line)"
    if len(text) > MAX_LINE_TEXT:
        text = text[:MAX_LINE_TEXT - 1] + "…"
    return f"`` {text} ``" if "`" in text else f"`{text}`"


# ---------------------------------------------------------------------------------------------
# Files and git
# ---------------------------------------------------------------------------------------------

def grep(pattern, folders=None, fixed=True, word=True):
    """Tracked and untracked (not ignored) files under the code ``folders`` -> 'path:line:text'
    lines; with no folders, the whole repo except docs/ (the step files name the code names they
    discuss and would count as code)."""
    args = ["git", "grep", "-n", "-I", "--untracked"]
    args += ["-F"] if fixed else ["-E"]
    args += ["-w"] if word else []
    args += ["-e", pattern, "--", *(folders or (".", ":!docs"))]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode > 1:            # 1 = no match
        raise RuntimeError(result.stderr.strip())
    return [line for line in result.stdout.splitlines() if "__pycache__" not in line]


def files_ending(path):
    """Tracked or untracked (not ignored) files whose path is ``path`` or ends in ``/path``."""
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", f"*/{path}",
                             path], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return sorted(set(result.stdout.split()))


def check_path(ref, folders=None):
    """A path not at the root is looked for as the end of a longer one: briefs often give the
    folder in prose ("in `frontend/src/views/`", S048, S059, S061, S064 feedback)."""
    found = [ref.value] if (ROOT / ref.value).is_file() else files_ending(ref.value)
    if not found:
        return [f"- `{ref.value}`: **no such file** (new, or a library's path)"]
    if len(found) > 1:
        return [f"- `{ref.value}`: **{len(found)} files end so**: {listing(found)}"]
    where = "" if found[0] == ref.value else f" (at `{found[0]}`)"
    count = len((ROOT / found[0]).read_text(encoding="utf-8", errors="replace").splitlines())
    if ref.last_line > count:
        return [f"- `{ref.value}`{where}: **has {count} lines**, the brief cites line {ref.last_line}"]
    return [f"- `{ref.value}`{where}: exists ({count} lines)"]


def check_file(ref, folders=None):
    """A bare file name -> where files of that name are (tracked or untracked, not ignored)."""
    found = files_ending(ref.value)
    return [f"- `{ref.value}`: " + (listing(found) if found else "**no file of that name**")]


def check_test(ref, folders=None):
    """A test id's file is looked up at the root, then in each code folder and its tests/ folder."""
    file_part, names = ref.value.split("::", 1)
    places = [ROOT / file_part]
    for folder in folders or ():
        places += [ROOT / folder / file_part, ROOT / folder / "tests" / file_part]
    candidates = [p for p in places if p.is_file()]
    if not candidates:
        return [f"- `{ref.value}`: **no such test file**"]
    text = candidates[0].read_text(encoding="utf-8", errors="replace")
    missing = [n for n in names.split("::") if not re.search(rf"\b{re.escape(n)}\b", text)]
    return [f"- `{ref.value}`: " + (f"**not found: {', '.join(missing)}**" if missing else "exists")]


def split_hit(hit):
    """A git grep line 'path:line:text' -> (path, line, text)."""
    return tuple((hit.split(":", 2) + ["", ""])[:3])


def check_route(ref, folders=None):
    """The test files with a line that calls the route by its whole shape (route_shape), after the
    file's own route constants are put into the line; the grep looks for the route's last literal
    segment first, then each line is matched."""
    literal = next((s for s in reversed(ref.value.strip("/").split("/")) if not s.startswith("<")), "api")
    shape = route_shape(ref.value)
    files, constants = [], {}
    for path, _, text in map(split_hit, grep(literal, folders, word=False)):
        if not is_test_path(path) or path in files:
            continue
        if path not in constants:
            constants[path] = route_constants((ROOT / path).read_text(encoding="utf-8", errors="replace"))
        if shape.search(expand_constants(text, constants[path])):
            files.append(path)
    return [f"- `{ref.value}`: called in {len(files)} test file(s): {listing(sorted(files)) or '—'}"]


def check_ui(ref, folders=None):
    """Screen text -> the frontend test lines that hold it (a backend line is no screen text)."""
    lines = [f"{path}:{line}" for path, line, _ in map(split_hit, grep(ref.value, folders, word=False))
             if is_frontend_test(path)]
    return [f"- `\"{ref.value}\"`: in {len(lines)} test line(s): {listing(lines) or '—'}"]


def check_names(group, folders=None, all_sentences=(), own_step=None):
    """The code names: one entry per name found; the names found nowhere in one line; and a dotted
    name whose module is no code file defining it (a table.column, a JS object) in one line."""
    lines, missing, not_looked_up = [], [], []
    for ref in group:
        module, _, short = ref.value.rpartition(".")
        own_file = None
        if module:
            own_file = module_file(module.rsplit(".", 1)[-1], folders)
            text = (ROOT / own_file).read_text(encoding="utf-8", errors="replace") if own_file else ""
            if not defines_at_top(text, short):
                not_looked_up.append(f"`{ref.value}`")
                continue
        hits = grep(short, folders)
        if own_file:
            hits = [h for h in hits if h.startswith(own_file + ":")] or hits
        if not hits:
            missing.append(f"`{ref.value}`{planned_in(ref.value, all_sentences, own_step)}")
            continue
        lines += summarise_hits(ref.value, hits, folders)
    if missing:
        lines.append(f"- not found: {', '.join(missing)}")
    if not_looked_up:
        lines.append(f"- table.column or attribute, not looked up: {', '.join(not_looked_up)}")
    return lines


def check_cited(cites):
    """{(path, first, last): names} -> the Cited lines section, one line per citation, grouped by
    file."""
    by_file = {}
    for (path, first, last), names in cites.items():
        by_file.setdefault(path, []).append((first, last, names))
    out = []
    for path, rows in by_file.items():
        found = [path] if (ROOT / path).is_file() else files_ending(path)
        spots = ", ".join(f":{a}" if a == b else f":{a}-{b}" for a, b, _ in rows)
        if not found:
            out.append(f"- `{path}`: **no such file**, cited at {spots}")
            continue
        if len(found) > 1:
            out.append(f"- `{path}`: **{len(found)} files end so** ({listing(found, COMMON_LISTED)}), cited at {spots}")
            continue
        lines = (ROOT / found[0]).read_text(encoding="utf-8", errors="replace").splitlines()
        where = "" if found[0] == path else f" (at `{found[0]}`)"
        out.append(f"- `{path}`{where} ({len(lines)} lines):")
        out += [f"  - {cited_row(lines, first, last, names)}" for first, last, names in rows]
    return out


CHECKS = {"path": check_path, "file": check_file, "test": check_test, "route": check_route, "ui": check_ui}
SECTIONS = (("path", "Files"), ("file", "Files named without a folder"), ("test", "Test ids"), ("route", "Routes"),
            ("name", "Code names"), ("ui", "Screen text in the tests"))


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
    folders = backticked(load_step_settings().get("Code folders")) or None
    path = brief_path(argv[0])
    brief = path.read_text(encoding="utf-8")
    refs = extract_refs(brief)
    step = re.match(r"S\d{3}", path.parent.name)
    all_sentences = sentences(brief)
    out = [f"# Brief facts — {path.relative_to(ROOT).as_posix()}", "",
           "Facts only: \"not found\" is right for a name the brief says is new.", ""]
    for kind, title in SECTIONS:
        group = [r for r in refs if r.kind == kind]
        if group:
            out += [f"## {title}", ""]
            if kind == "name":
                out += check_names(group, folders, all_sentences, step.group(0) if step else None)
            else:
                for ref in group:
                    out += CHECKS[kind](ref, folders)
            out.append("")
        if kind == "path":
            cites = citations(brief)
            if cites:
                out += ["## Cited lines", ""] + check_cited(cites) + [""]
    text = "\n".join(out)
    report = ROOT / "scratch" / f"brief-facts-{step.group(0) if step else 'brief'}.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text(text, encoding="utf-8")
    print(text)
    print(f"(written to {report})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
