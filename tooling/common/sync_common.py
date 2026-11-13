# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv", "truststore"]
# ///
"""Sync shared files from the private smtw-common repo into the current project."""

import json
import os
import ssl
import sys
import base64
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv

# truststore checks certificates with the operating system's own verifier.
# Python's default check on Windows loads the Root and the intermediate (CA)
# stores into OpenSSL, and a stale cross-signed intermediate there can make the
# check fail now and then ("unable to get issuer certificate"). truststore is
# optional: a repo whose Python lacks it keeps the default check, so the
# self-update below never breaks a sync.
try:
    import truststore
except ImportError:
    truststore = None

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
    ("tooling/common/preflight_stamp.py", "tooling/common/preflight_stamp.py"),
    ("tooling/common/preflight.py", "tooling/common/preflight.py"),
    ("tooling/common/ccssh.py", "tooling/common/ccssh.py"),
    ("tooling/common/ccloki.py", "tooling/common/ccloki.py"),
    ("tooling/common/material_icon.py", "tooling/common/material_icon.py"),
    ("tooling/common/run_test_suite.py", "tooling/common/run_test_suite.py"),
    # Software inventory audit: the scripts only (its tests live in tooling/common/tests)
    ("tooling/deps/audit.py", "tooling/deps/audit.py"),
    ("tooling/deps/audit_core.py", "tooling/deps/audit_core.py"),
    ("tooling/run-deps-audit.bat", "tooling/run-deps-audit.bat"),
    # Step workflow (/step): wrappers and the two READMEs
    ("tooling/step-brief-facts.bat", "tooling/step-brief-facts.bat"),
    ("tooling/step-check.bat", "tooling/step-check.bat"),
    ("tooling/step-claim.bat", "tooling/step-claim.bat"),
    ("tooling/step-clean.bat", "tooling/step-clean.bat"),
    ("tooling/step-feedback.bat", "tooling/step-feedback.bat"),
    ("tooling/step-ls.bat", "tooling/step-ls.bat"),
    ("tooling/step-snapshot.bat", "tooling/step-snapshot.bat"),
    ("tooling/step-stats.bat", "tooling/step-stats.bat"),
    ("tooling/render-mockups.bat", "tooling/render-mockups.bat"),
    ("tooling/check-diagrams.bat", "tooling/check-diagrams.bat"),
    ("docs/steps/README.md", "docs/steps/README.md"),
    ("docs/roadmap/README.md", "docs/roadmap/README.md"),
    # The gallery app contract: any repo with a gallery/ folder follows it
    ("docs/SMTW-Utils-Gallery.md", "docs/SMTW-Utils-Gallery.md"),
]

# Source directories in smtw-common repo to recursively sync into the project
# (source dir in repo, destination dir relative to project root)
DIRS = [
    (".claude/skills", ".claude/skills"),
    (".claude/hooks", ".claude/hooks"),
    (".claude/agents", ".claude/agents"),
    ("tooling/steps", "tooling/steps"),
    ("tooling/roadmap", "tooling/roadmap"),
    ("tooling/architecture", "tooling/architecture"),
]

# Files this repo once synced and has since renamed or dropped:
# (path relative to project root, {SHA-256 of each version this repo shipped}).
# The sync deletes such a file only if its content matches one of the hashes, so
# a copy the target repo has edited is kept, with a warning. Hash with
# file_hash() below, i.e. with CRLF turned into LF, e.g.:
#   git show <commit>:<path> | tr -d '\r' | sha256sum
REMOVED = [
    # Renamed to tooling/common/run_test_suite.py
    ("tooling/common/run_logged.py", {
        "1429b45df726b460ed34e82c2a4aeb2e22e1ba824ab8a302f8ffd6aaceb6d52b",  # a2147bd
    }),
    # Renamed to .claude/agents/planner.md
    (".claude/agents/roadmapper.md", {
        "351b65792313801640f7fb4534778925f64a5c057991b0f808dc91948b60dddf",  # a2147bd
        "b495ddd31ee76e45f8609ea1746fcda76cf77c736fa1f7586eb16383085f0ffd",  # 17272f6
    }),
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


def _ssl_context() -> ssl.SSLContext:
    if truststore is not None:
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()


def report_cert_error(e: ssl.SSLCertVerificationError):
    """Stop on a certificate failure: every other fetch would fail the same way."""
    print(f"Error: the certificate of api.github.com could not be verified "
          f"({e.verify_message}).")
    if truststore is None:
        print("Python's own check is in use, and a stale certificate in the Windows "
              "certificate stores can cause this. Install truststore into this Python, "
              "so the check uses the operating system's verifier:\n"
              f"  uv pip install --python \"{sys.executable}\" truststore\n"
              f"  (or: \"{sys.executable}\" -m pip install truststore)")
    else:
        print("The operating system's verifier (truststore) refused it too. Check for "
              "a proxy or antivirus that inspects HTTPS, and the system clock.")
    raise SystemExit(1)


def _gh_request(token: str, path: str):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read())
    except HTTPError:
        raise  # a subclass of URLError; the callers report it per file
    except URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            report_cert_error(e.reason)
        raise


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


def file_hash(path: Path) -> str:
    """SHA-256 of a file's content, with CRLF read as LF: write_text() saves CRLF on
    Windows, so the same synced file has different bytes on different machines."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# The last lines of a sync name each old file it kept, so the warning is not lost in the output;
# sync_all.py reads them by this prefix.
KEPT_PREFIX = "KEPT, delete by hand if not needed: "


def kept_report(kept: list[str]) -> list[str]:
    """The closing lines that repeat the old files a sync kept because this repo changed them."""
    return [f"{KEPT_PREFIX}{rel}" for rel in kept]


def remove_old_files(root: Path, removed=None) -> list[str]:
    """Delete the files in REMOVED that are unchanged copies of what this repo
    shipped. Return the paths kept because the target repo changed them."""
    kept = []
    for rel, hashes in (REMOVED if removed is None else removed):
        path = root / rel
        if not path.is_file():
            continue
        if file_hash(path) in hashes:
            path.unlink()
            print(f"Removed {rel} (no longer in smtw-common)")
        else:
            kept.append(rel)
            print(f"Warning: {rel} is no longer in smtw-common, but it was changed "
                  f"in this repo, so it is kept. Delete it by hand if not needed.")
    return kept


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

    kept = remove_old_files(PROJECT_ROOT)

    check_claude_md_banner()

    if kept:
        print()
        for line in kept_report(kept):
            print(line)

    if failures:
        print(f"\n{failures} of {attempts} fetches failed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()