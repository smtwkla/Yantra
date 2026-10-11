# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv"]
# ///
"""Sync shared files from the private smtw-common repo into the current project."""

import json
import os
import sys
import base64
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv

REPO = "smtwkla/smtw-common"
BRANCH = "main"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# (source path in smtw-common repo, destination path relative to project root)
SELF_SRC = "tooling/common/sync_common.py"

# (source path in smtw-common repo, destination path relative to project root)
FILES = [
    (".claude/CLAUDE-COMMON.md", ".claude/CLAUDE-COMMON.md"),
    (".claude/CLAUDE-INFRA.md", ".claude/CLAUDE-INFRA.md"),
    (".claude/SMTW-WebApp-Base.md", ".claude/SMTW-WebApp-Base.md"),
    ("tooling/common/bump_ver.py", "tooling/common/bump_ver.py"),
    ("tooling/common/release.py", "tooling/common/release.py"),
    ("tooling/common/ccssh.py", "tooling/common/ccssh.py"),
    ("tooling/common/ccloki.py", "tooling/common/ccloki.py"),
]

# Source directories in smtw-common repo to recursively sync into the project
# (source dir in repo, destination dir relative to project root)
DIRS = [
    (".claude/skills", ".claude/skills"),
    (".claude/hooks", ".claude/hooks"),
]

# Target project's CLAUDE.md must start with this banner. The `@CLAUDE-COMMON.md`
# line is a Claude Code import: the file is loaded into context automatically at
# session start, rather than relying on Claude to choose to read it. Import paths
# resolve relative to the importing file, and CLAUDE.md lives alongside
# CLAUDE-COMMON.md in .claude/, so the path is same-directory. The import must be
# plain text — imports inside code spans or code blocks are not evaluated.
CLAUDE_MD_REL = ".claude/CLAUDE.md"
CLAUDE_MD_MARKER = "@CLAUDE-COMMON.md"
CLAUDE_MD_BANNER = (
    "@CLAUDE-COMMON.md\n\n"
    "The shared conventions imported above apply to all repos. This file contains "
    "repo-specific instructions: anything here overrides the Defaults section of "
    "CLAUDE-COMMON.md; its Invariants always apply."
)


def _gh_request(token: str, path: str):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_file(token: str, file_path: str) -> str:
    data = _gh_request(token, file_path)
    return base64.b64decode(data["content"]).decode("utf-8")


def sync_dir(token: str, src_dir: str, dest_dir: Path):
    entries = _gh_request(token, src_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        name = entry["name"]
        entry_type = entry["type"]
        src_path = f"{src_dir}/{name}"
        dest_path = dest_dir / name
        if entry_type == "dir":
            sync_dir(token, src_path, dest_path)
        elif entry_type == "file":
            content = fetch_file(token, src_path)
            dest_path.write_text(content, encoding="utf-8")
            print(f"Synced {src_path} -> {dest_path}")


def report_fetch_error(path: str, e: HTTPError):
    """Print a failed fetch. A 401 means the token itself is bad, so every other
    fetch would fail the same way -- stop right away with a clear message."""
    if e.code == 401:
        print(f"Error: GITHUB_PAT rejected ({e.code} {e.reason}) fetching {path} -- the token is "
              f"expired or revoked; update tooling/common/.env-common.")
        raise SystemExit(1)
    print(f"Error fetching {path}: {e.code} {e.reason}")


def ensure_gitignore():
    gitignore = Path(__file__).resolve().parent / ".gitignore"
    entry = ".env-common"
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        if entry not in lines:
            with gitignore.open("a", encoding="utf-8") as f:
                if lines and lines[-1] != "":
                    f.write("\n")
                f.write(entry + "\n")
    else:
        gitignore.write_text(entry + "\n", encoding="utf-8")


def check_claude_md_banner():
    """Warn (don't modify) if the project's CLAUDE.md is missing the CLAUDE-COMMON.md import."""
    claude_md = PROJECT_ROOT / CLAUDE_MD_REL
    if claude_md.exists() and CLAUDE_MD_MARKER in claude_md.read_text(encoding="utf-8"):
        return

    if claude_md.exists():
        reason = f"{CLAUDE_MD_REL} does not import CLAUDE-COMMON.md ({CLAUDE_MD_MARKER})."
    else:
        reason = f"{CLAUDE_MD_REL} does not exist."

    print("\n" + "!" * 70)
    print(f"ACTION NEEDED: {reason}")
    print("Without this banner at the TOP of CLAUDE.md, the shared conventions")
    print("are not loaded. Please copy/paste the following into place, replacing")
    print("any older 'Read CLAUDE-COMMON.md first' banner:\n")
    print(CLAUDE_MD_BANNER)
    print("!" * 70)


def main():
    ensure_gitignore()
    load_dotenv(Path(__file__).resolve().parent / ".env-common")
    token = os.getenv("GITHUB_PAT")
    if not token:
        print("Error: GITHUB_PAT not set in tooling/common/.env-common")
        raise SystemExit(1)

    # Every fetch counts towards the exit status: a sync that fetched nothing
    # must not look like a success to the caller (e.g. sync_all.py).
    attempts = 1 + len(FILES) + len(DIRS)
    failures = 0

    # Self-update first
    self_path = Path(__file__).resolve()
    try:
        new_self = fetch_file(token, SELF_SRC)
    except HTTPError as e:
        report_fetch_error(SELF_SRC, e)
        failures += 1
    else:
        if new_self != self_path.read_text(encoding="utf-8"):
            self_path.write_text(new_self, encoding="utf-8")
            print(f"sync_common.py updated itself — re-running...\n")
            os.execv(sys.executable, [sys.executable, str(self_path)] + sys.argv[1:])
        else:
            print("sync_common.py is up to date.")

    for src, dest_rel in FILES:
        dest = PROJECT_ROOT / dest_rel
        try:
            content = fetch_file(token, src)
        except HTTPError as e:
            report_fetch_error(src, e)
            failures += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        print(f"Synced {src} -> {dest}")

    for src_dir, dest_rel in DIRS:
        dest_dir = PROJECT_ROOT / dest_rel
        try:
            sync_dir(token, src_dir, dest_dir)
        except HTTPError as e:
            report_fetch_error(src_dir, e)
            failures += 1

    check_claude_md_banner()

    if failures:
        print(f"\n{failures} of {attempts} fetches failed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()