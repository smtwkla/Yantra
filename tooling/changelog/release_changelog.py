"""Release hook: writes the new version's section into CHANGELOG.md (S048 § 1.2).

Run by tooling/common/release.py as POST_BUMP_SCRIPT, after the bump and before the release
commit; it `git add`s CHANGELOG.md so the file rides in that commit.  Standard library only: it
runs under release.py's interpreter.

The items come from, in order: scratch/release-notes.md (written by the pre-flight, valid only
for HEAD), the Claude CLI running the pre-flight skill's notes mode on the commit list, or
nothing (an empty section).  Claude being missing, slow or wrong never stops a release; only an
unreadable or unwritable CHANGELOG.md does (exit 1).
"""

import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
NOTES_FILE = REPO_ROOT / "scratch" / "release-notes.md"
CLAUDE_TIMEOUT_S = 300
# The rules for the notes are the pre-flight skill's (.claude/skills/pre-flight/SKILL.md § 3c).
CLAUDE_PROMPT = "/pre-flight notes unattended"
IST = timezone(timedelta(hours=5, minutes=30))
SHA_LINE_PREFIX = "<!-- commit "
SHA_LINE_SUFFIX = " -->"


# ---------------------------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------------------------

def clean_items(output):
    """The lines of `output` that start with "- ", stripped; everything else is dropped."""
    return [line.strip() for line in output.splitlines() if line.strip().startswith("- ")]


def notes_file_sha(file_text):
    """The sha a notes file names on its first line, or None."""
    lines = file_text.splitlines()
    first = lines[0].strip() if lines else ""
    if first.startswith(SHA_LINE_PREFIX) and first.endswith(SHA_LINE_SUFFIX):
        return first[len(SHA_LINE_PREFIX):-len(SHA_LINE_SUFFIX)].strip()
    return None


def notes_for_head(file_text, head_sha):
    """The items of a notes file, or None when its first line does not name `head_sha`."""
    if notes_file_sha(file_text) != head_sha:
        return None
    return clean_items("\n".join(file_text.splitlines()[1:]))


def insert_section(text, version, date, items):
    """`text` with the section `## <version> — <date>` and its items after the `# ` title line.

    With no title line the section goes at the top.  A blank line separates it from what follows."""
    section = [f"## {version} — {date}", *items, ""]
    lines = text.splitlines()
    at = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
    before = lines[:at]
    after = lines[at:]
    while after and not after[0].strip():
        after = after[1:]
    if before:
        before.append("")
    return "\n".join(before + section + after).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------------------------
# Shell: git, the Claude CLI, the files
# ---------------------------------------------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          encoding="utf-8", errors="replace")


def head_sha():
    result = _git("rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def commit_list():
    """Subjects and bodies since the last release tag, release commits skipped."""
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    rev = f"{tag.stdout.strip()}..HEAD" if tag.returncode == 0 else "HEAD"
    result = _git("log", rev, "--no-merges", "--invert-grep", "--grep=^release v",
                  "--format=commit %h%n%s%n%b%n")
    return result.stdout if result.returncode == 0 else ""


def ask_claude(commits):
    """(items, why_none): Claude's `- ` lines, or [] with the reason for none."""
    claude = shutil.which("claude")
    if not claude:
        return [], "Claude CLI not found"
    if not commits.strip():
        return [], "no commits since the last release"
    try:
        result = subprocess.run(
            [claude, "-p", CLAUDE_PROMPT, "--model", "sonnet", "--tools", "Read",
             "--strict-mcp-config", "--no-session-persistence"],
            input=commits, cwd=REPO_ROOT, capture_output=True, encoding="utf-8",
            errors="replace", timeout=CLAUDE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return [], f"Claude timed out after {CLAUDE_TIMEOUT_S} s"
    except OSError as err:
        return [], f"Claude could not start ({err})"
    if result.returncode != 0:
        return [], f"Claude failed (exit {result.returncode})"
    items = clean_items(result.stdout)
    return items, "" if items else "Claude gave no items"


def choose_items():
    """(items, source text) for the new section."""
    head = head_sha()
    if NOTES_FILE.exists() and head:
        try:
            file_text = NOTES_FILE.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            print(f"Release notes: scratch/release-notes.md cannot be read ({err}); not used.")
        else:
            items = notes_for_head(file_text, head)
            if items is not None:
                return items, "from pre-flight"
            named = notes_file_sha(file_text)
            print(f"Release notes: scratch/release-notes.md is for commit "
                  f"{named[:7] if named else 'no commit'}, not HEAD; not used.")
    items, why = ask_claude(commit_list())
    if items:
        return items, "from Claude"
    return [], f"empty section: {why}"


def say(text):
    """Print `text` even where the console cannot show every character (a PyCharm console)."""
    encoding = sys.stdout.encoding or "ascii"
    print(text.encode(encoding, errors="replace").decode(encoding))


def main():
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    date = datetime.now(IST).strftime("%d-%m-%Y")
    items, source = choose_items()
    try:
        text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
        CHANGELOG.write_text(insert_section(text, version, date, items), encoding="utf-8")
    except OSError as err:
        print(f"Release notes: CHANGELOG.md cannot be read or written: {err}")
        return 1
    added = _git("add", "CHANGELOG.md")
    if added.returncode != 0:
        print(f"Release notes: git add CHANGELOG.md failed: {added.stderr.strip()}")
        return 1
    say(f"Release notes for v{version}: {source} ({len(items)} {'item' if len(items) == 1 else 'items'})")
    for item in items:
        say(f"  {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
