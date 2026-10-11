# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv"]
# ///
"""Pre-release pipeline: check clean tree, test, bump version, commit+tag, build, deploy, push.

Usage:
    uv run tooling/common/release.py            # patch bump (default)
    uv run tooling/common/release.py -m         # minor bump
    uv run tooling/common/release.py -M         # major bump
    uv run tooling/common/release.py -B         # allow release from non-main branch

Configuration via tooling/common/release.env (all optional):
    TEST_CMD=pytest                        # default if unset; "skip" opts out with a warning
    POST_BUMP_SCRIPT=tooling/hook.py       # run after version bump, before release commit;
                                           # must git-add any files it modifies; skipped if unset
    BUILD_SCRIPT=tooling/build.py          # skipped if unset
    DEPLOY_SCRIPT=tooling/deploy.py        # skipped if unset
    GIT_PUSH=skip                          # opt out of the final `git push --follow-tags`
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import os

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


def run(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    print(f"\n> {cmd}")
    kwargs.setdefault("encoding", "utf-8")
    return subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT, **kwargs)


def git_commit(message: str) -> subprocess.CompletedProcess:
    """Create a git commit using a temp file to avoid shell-quoting issues on Windows."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(message)
        msg_file = f.name
    try:
        return run(f"git commit -F {msg_file}")
    finally:
        os.unlink(msg_file)


def git_tag(name: str, message: str) -> subprocess.CompletedProcess:
    """Create an annotated git tag using a temp file for the message."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(message)
        msg_file = f.name
    try:
        return run(f"git tag -a {name} -F {msg_file}")
    finally:
        os.unlink(msg_file)


def abort(msg: str):
    print(f"ABORT: {msg}")
    sys.exit(1)


def main():
    load_dotenv(SCRIPT_DIR / "release.env")

    parser = argparse.ArgumentParser(description="Run pre-release pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-M", "--major", action="store_true", help="Major bump")
    group.add_argument("-m", "--minor", action="store_true", help="Minor bump")
    group.add_argument("-p", "--patch", action="store_true", help="Patch bump (default)")
    parser.add_argument("-B", "--any-branch", action="store_true",
                        help="Allow release from a non-main branch")
    args = parser.parse_args()

    # --- 0. Check branch ---
    if not args.any_branch:
        result = run("git rev-parse --abbrev-ref HEAD", capture_output=True, text=True)
        if result.returncode != 0:
            abort("Could not determine current branch.")
        branch = result.stdout.strip()
        if branch != "main":
            abort(f"Release is only allowed on 'main' (current: '{branch}'). Use -B to override.")

    # --- 1. Check for uncommitted changes ---
    result = run("git status --porcelain", capture_output=True, text=True)
    if result.returncode != 0:
        abort("git status failed")
    if result.stdout.strip():
        abort("Uncommitted changes detected. Commit or stash before releasing.")

    # --- 2. Run tests ---
    test_cmd = os.getenv("TEST_CMD", "pytest")
    if test_cmd == "skip":
        print("\nWARNING: tests skipped (TEST_CMD=skip)")
    else:
        result = run(test_cmd)
        if result.returncode != 0:
            abort("Tests failed.")

    # --- 3. Bump version (skip if no code changes since last release) ---
    # Find commits since the last "release v..." commit using NUL-separated
    # full messages. Each entry is: subject\x01body
    log_result = run(
        'git log --pretty=format:%s%x01%B%x00',
        capture_output=True, text=True,
    )
    change_lines: list[str] = []
    if log_result.returncode == 0 and log_result.stdout.strip():
        entries = [e.strip() for e in log_result.stdout.split("\x00") if e.strip()]
        for entry in entries:
            subject, _, body = entry.partition("\x01")
            if subject.startswith("release v"):
                break  # stop at the last release commit
            for line in body.splitlines():
                line = line.strip()
                if line:
                    change_lines.append(line)
        # Deduplicate preserving order
        seen: set[str] = set()
        change_lines = [ln for ln in change_lines if not (ln in seen or seen.add(ln))]

    if not change_lines:
        new_ver = VERSION_FILE.read_text().strip()
        print(f"\nNo code changes since last release. Reusing version v{new_ver}.")
    else:
        bump_flag = "-M" if args.major else ("-m" if args.minor else "-p")
        result = run(f"{sys.executable} {SCRIPT_DIR / 'bump_ver.py'} {bump_flag}")
        if result.returncode != 0:
            abort("Version bump failed.")

        new_ver = VERSION_FILE.read_text().strip()

        # Post-bump hook: propagate the new version into project files. The
        # hook must git-add anything it modifies so it rides in the release
        # commit below (release.py itself only adds VERSION).
        post_bump_script = os.getenv("POST_BUMP_SCRIPT")
        if post_bump_script:
            result = run(f"{sys.executable} {PROJECT_ROOT / post_bump_script}")
            if result.returncode != 0:
                abort("Post-bump script failed.")

        # --- 4. Commit and tag ---
        summary = "\n".join(f"- {line}" for line in change_lines)
        commit_msg = f"release v{new_ver}\n\n{summary}"

        run(f"git add {VERSION_FILE}")
        result = git_commit(commit_msg)
        if result.returncode != 0:
            abort("Git commit failed.")

        result = git_tag(f"v{new_ver}", summary)
        if result.returncode != 0:
            abort(f"Git tag v{new_ver} failed (already exists?).")

        print(f"\nTagged v{new_ver}")

    # --- 5. Build ---
    build_script = os.getenv("BUILD_SCRIPT")
    if build_script:
        result = run(f"{PROJECT_ROOT / build_script}")
        if result.returncode != 0:
            abort("Build failed.")
    else:
        print("\nBUILD_SCRIPT not set, skipping build.")

    # --- 6. Deploy ---
    deploy_script = os.getenv("DEPLOY_SCRIPT")
    if deploy_script:
        result = run(f"{sys.executable} {PROJECT_ROOT / deploy_script}")
        if result.returncode != 0:
            abort("Deploy failed.")
    else:
        print("\nDEPLOY_SCRIPT not set, skipping deploy.")

    # --- 7. Push ---
    # Last step so a failed build/deploy never leaves a published release commit;
    # everything before this is local and can be amended or re-run.
    if os.getenv("GIT_PUSH") == "skip":
        print("\nWARNING: git push skipped (GIT_PUSH=skip) — publish the release commit and tag manually.")
    else:
        result = run("git push --follow-tags origin HEAD")
        if result.returncode != 0:
            abort(f"git push failed — v{new_ver} is built/deployed but NOT published; push manually.")

    print(f"\nRelease v{new_ver} complete.")


if __name__ == "__main__":
    main()