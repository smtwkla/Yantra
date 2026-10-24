"""The browser tests in parallel lanes: each lane is one Playwright shard on its own stack
(database vel_yantra_lane<n>_e2e, backend 5010 + n, Vite 5180 + n, files scratch/e2e-data/
lane<n>), so lanes share nothing and cannot race.  Run by tooling/run-e2e-tests.bat after
its checks; extra arguments go to every lane's Playwright (a spec file, --project=…).

    E2E_LANES=<n>   the number of lanes (default 6); 1 runs the single stack as before

Each lane's output goes to scratch/e2e-lanes/lane<n>.log; the runner prints one line per lane,
then merges the lanes' blob reports into scratch/e2e-report/html and prints the failures and
totals once.  Exit 0 when every lane passed and the merge worked, else 1.  Stdlib only.

One run at a time on this machine: every run (lanes or the single stack) uses the same ports,
databases and folders, and each backend drops its database at start, so two runs at once
spoil each other (22-10-2026: two windows' runs, 12 failures).  A run holds an exclusive lock
on scratch/e2e-run.lock; a second run waits for it.  The operating system releases the lock
when the process ends, a crash included, so a stale lock cannot block.

WebKit in Docker (S046): on Windows, Playwright's WebKit multiplies the emulated pixel ratio by
the display scale (125 % gives a 312 px iPhone window, not 390).  So a run that includes
phone-webkit starts one container from Playwright's official image (mcr.microsoft.com/
playwright:v<version>-noble, the version of frontend's @playwright/test) running `run-server`,
published on 127.0.0.1:3999 only, and sets E2E_WEBKIT_WS; playwright.config.js then connects
phone-webkit to it with exposeNetwork "<loopback>", so the lanes' Vite and backend stay on the
host.  The container starts inside the lock, its output goes to scratch/e2e-lanes/webkit.log,
and it is removed after the run, a failed one included.  Its npm cache is the named volume
yantra-e2e-npm (the image has no playwright package, npx fetches it once).  The first run of a
Playwright version pulls the image (about 2.5 GB).

    E2E_WEBKIT=native   run WebKit on Windows as before (S045's guard in e2e/support/test.js
                        skips it when the window is narrower than the device)

A run that names only plain projects other than phone-webkit (matched as Playwright does:
case-insensitive, `*` wildcards) starts no container; a wildcard may match it, so it starts one."""

import contextlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
REPORT_DIR = ROOT / "scratch" / "e2e-report"
BLOBS_DIR = REPORT_DIR / "blobs"
MERGED_DIR = REPORT_DIR / "blobs-merged"
LANE_LOGS = ROOT / "scratch" / "e2e-lanes"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "tooling" / "dev" / "docker-compose.dev.yml")]
DEV_ROOT_PASSWORD = "dev-root-password"   # the dev compose file's; dev only
DB_USER = "vel_yantra_master"
DEFAULT_LANES = 6
MAX_LANES = 20                            # ports 5011–5030 and 5181–5200
PROJECT_COUNT = 3                         # playwright.config.js's projects
LOCK_FILE = ROOT / "scratch" / "e2e-run.lock"
LOCK_POLL_SECONDS = 10
WEBKIT_CONTAINER = "yantra-e2e-webkit"
WEBKIT_PORT = 3999                        # host side, 127.0.0.1 only; outside the e2e and dev ports
WEBKIT_NPM_VOLUME = "yantra-e2e-npm"
NPM_CACHE = "/home/pwuser/.npm"
WEBKIT_START_SECONDS = 60
WEBKIT_LOG = LANE_LOGS / "webkit.log"
WEBKIT_PROJECT = "phone-webkit"
WAYS_OUT = ("Run without the iPhone tests (--project=phone-chromium --project=desktop-chromium), "
            "or run WebKit on Windows (E2E_WEBKIT=native).")
SUMMARY = re.compile(r"^\s*(\d+) (passed|failed|flaky|skipped|did not run)", re.MULTILINE)


def named_projects(args):
    """The project names Playwright 1.64 reads: `--project=a` and `--project a b` (variadic, up
    to the next option).  It has no `-p` and splits nothing at commas."""
    names = []
    reading = False
    for arg in args:
        if arg.startswith("--project="):
            names.append(arg.split("=", 1)[1])
            reading = False
        elif arg == "--project":
            reading = True
        elif arg.startswith("-"):
            reading = False
        elif reading:
            names.append(arg)
    return names


def lane_count(args, wanted):
    """No more lanes than test groups: a shard is a spec file in one project, so a run of two
    spec files on one project needs two lanes, not six."""
    specs = [a for a in args if a.endswith(".spec.js")]
    projects = named_projects(args)
    if not specs and not projects:
        return wanted
    groups = (len(specs) or len(list((FRONTEND / "e2e").glob("*.spec.js")))) * (len(projects) or PROJECT_COUNT)
    return max(1, min(wanted, groups))


def webkit_mode():
    return os.environ.get("E2E_WEBKIT", "").lower()


def needs_webkit_server(args, mode):
    """True unless WebKit runs natively or every named project is a plain name other than
    phone-webkit.  Playwright matches names case-insensitively with `*` wildcards, so a form
    this parse does not understand errs towards starting the container."""
    if mode == "native":
        return False
    projects = named_projects(args)
    if not projects:
        return True
    return any("*" in name or name.lower() == WEBKIT_PROJECT for name in projects)


def playwright_version(frontend=FRONTEND):
    """The installed @playwright/test version: client and server must match in major.minor."""
    package = frontend / "node_modules" / "@playwright" / "test" / "package.json"
    return json.loads(package.read_text(encoding="utf-8"))["version"]


def webkit_image(version):
    return f"mcr.microsoft.com/playwright:v{version}-noble"


def webkit_run_command(version):
    """`docker run` for the WebKit server, attached (its output is the log), bound to loopback."""
    return ["docker", "run", "--rm", "--init", "--user", "pwuser", "--name", WEBKIT_CONTAINER,
            "-p", f"127.0.0.1:{WEBKIT_PORT}:3000", "-v", f"{WEBKIT_NPM_VOLUME}:{NPM_CACHE}",
            webkit_image(version),
            "npx", "-y", f"playwright@{version}", "run-server", "--port", "3000", "--host", "0.0.0.0"]


def webkit_failure(cause):
    """The message for a WebKit server that cannot start: what happened, then both ways out."""
    reasons = {
        "pull": "The WebKit image could not be downloaded. Check the internet connection, then run again.",
        "port": f"Port {WEBKIT_PORT} is in use, so the WebKit server cannot start. "
                "Close the program that uses it, then run again.",
        "name": f"The old WebKit container could not be removed. Run docker rm -f {WEBKIT_CONTAINER}, "
                "then run again.",
        "cache": "The cache folder of the WebKit server could not be prepared. "
                 "Check that Docker Desktop is running, then run again.",
        "stopped": "The WebKit server stopped before it was ready. See scratch/e2e-lanes/webkit.log.",
        "timeout": f"The WebKit server did not start in {WEBKIT_START_SECONDS} s. See scratch/e2e-lanes/webkit.log.",
    }
    return f"{reasons[cause]}\n{WAYS_OUT}"


class WebkitUnavailable(Exception):
    pass


def _docker(*args, **kwargs):
    return subprocess.run(["docker", *args], capture_output=True, text=True, **kwargs)


def _port_in_use():
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(("127.0.0.1", WEBKIT_PORT)) == 0


@contextlib.contextmanager
def webkit_server(version):
    """The WebKit container for the run (inside the lock, so nobody else owns its name or port)."""
    image = webkit_image(version)
    _docker("rm", "-f", WEBKIT_CONTAINER)           # a hard-killed run may have left it
    if _docker("ps", "-aq", "--filter", f"name=^{WEBKIT_CONTAINER}$").stdout.strip():
        raise WebkitUnavailable(webkit_failure("name"))
    if _docker("image", "inspect", image).returncode != 0:
        print(f"Pulling the WebKit image, about 2.5 GB, once per Playwright version: {image}")
        if subprocess.run(["docker", "pull", image]).returncode != 0:
            raise WebkitUnavailable(webkit_failure("pull"))
    if _port_in_use():
        raise WebkitUnavailable(webkit_failure("port"))
    # A new named volume is owned by root, and npx runs as pwuser: hand the cache folder over
    handed_over = _docker("run", "--rm", "--user", "root", "-v", f"{WEBKIT_NPM_VOLUME}:{NPM_CACHE}", image,
                          "chown", "pwuser:pwuser", NPM_CACHE)
    if handed_over.returncode != 0:
        raise WebkitUnavailable(handed_over.stderr.strip() + "\n" + webkit_failure("cache"))
    LANE_LOGS.mkdir(parents=True, exist_ok=True)
    log = open(WEBKIT_LOG, "w", encoding="utf-8")
    process = subprocess.Popen(webkit_run_command(version), stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + WEBKIT_START_SECONDS
        while "Listening on ws://" not in WEBKIT_LOG.read_text(encoding="utf-8", errors="replace"):
            if process.poll() is not None:
                raise WebkitUnavailable(webkit_failure("stopped"))
            if time.monotonic() > deadline:
                raise WebkitUnavailable(webkit_failure("timeout"))
            time.sleep(0.5)
        print(f"WebKit server up in {image} (scratch/e2e-lanes/webkit.log)")
        yield f"ws://127.0.0.1:{WEBKIT_PORT}/"
    finally:
        _docker("rm", "-f", WEBKIT_CONTAINER)
        process.wait()
        log.close()


def lane_database(lane):
    return f"vel_yantra_lane{lane}_e2e"     # as tooling/e2e/e2e_backend.py


def create_databases(lanes):
    """The lanes' databases and grants, in one call to the dev DB container (the backend drops
    and recreates its own at start, so this only makes sure the grant is there)."""
    sql = " ".join(
        f"CREATE DATABASE IF NOT EXISTS `{lane_database(n)}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        f" GRANT ALL PRIVILEGES ON `{lane_database(n)}`.* TO '{DB_USER}'@'%';" for n in range(1, lanes + 1))
    subprocess.run([*COMPOSE, "exec", "-T", "mariadb", "mariadb", "-uroot", f"-p{DEV_ROOT_PASSWORD}",
                    "-e", sql + " FLUSH PRIVILEGES;"], check=True)


def summary_of(log_text):
    found = dict((kind, int(n)) for n, kind in SUMMARY.findall(log_text))
    return ", ".join(f"{n} {kind}" for kind, n in found.items()) or "no summary (see the log)"


def run_lanes(lanes, args):
    shutil.rmtree(BLOBS_DIR, ignore_errors=True)
    LANE_LOGS.mkdir(parents=True, exist_ok=True)
    running = []
    for lane in range(1, lanes + 1):
        log = open(LANE_LOGS / f"lane{lane}.log", "w", encoding="utf-8")
        env = {**os.environ, "E2E_LANE": str(lane)}
        command = ["npx", "playwright", "test", f"--shard={lane}/{lanes}", "--pass-with-no-tests", *args]
        # shell: npx is npx.cmd on Windows
        running.append((lane, log, subprocess.Popen(subprocess.list2cmdline(command), cwd=FRONTEND, env=env,
                                                     stdout=log, stderr=subprocess.STDOUT, shell=True)))
    failed = False
    for lane, log, process in running:
        code = process.wait()
        log.close()
        text = (LANE_LOGS / f"lane{lane}.log").read_text(encoding="utf-8", errors="replace")
        print(f"lane {lane}: exit {code} — {summary_of(text)}  (scratch/e2e-lanes/lane{lane}.log)")
        failed |= code != 0
    return failed


def merge():
    """The lanes' blob zips into one folder, then one HTML report and one failure list."""
    shutil.rmtree(MERGED_DIR, ignore_errors=True)
    MERGED_DIR.mkdir(parents=True)
    for blob in BLOBS_DIR.glob("*/*.zip"):
        shutil.copy(blob, MERGED_DIR / f"{blob.parent.name}-{blob.name}")
    if not any(MERGED_DIR.iterdir()):
        print("No blob reports to merge: no lane ran a test.")
        return False
    command = ["npx", "playwright", "merge-reports", "--config", "playwright.merge.config.js", str(MERGED_DIR)]
    return subprocess.run(subprocess.list2cmdline(command), cwd=FRONTEND, shell=True).returncode == 0


@contextlib.contextmanager
def one_run_at_a_time():
    """Hold the machine's e2e lock for the run; wait while another run holds it."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_FILE, "a+")
    waited = False
    while True:
        try:
            _lock(handle)
            break
        except OSError:
            if not waited:
                print("Another e2e run is in progress on this machine; waiting for it to finish.")
                waited = True
            time.sleep(LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        _unlock(handle)
        handle.close()


def _lock(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def main(args):
    wanted = int(os.environ.get("E2E_LANES", DEFAULT_LANES))
    if not 1 <= wanted <= MAX_LANES:
        sys.exit(f"E2E_LANES must be 1 to {MAX_LANES}, not {wanted}")
    with one_run_at_a_time():
        if not needs_webkit_server(args, webkit_mode()):
            return run(args, wanted)
        try:
            with webkit_server(playwright_version()) as endpoint:
                os.environ["E2E_WEBKIT_WS"] = endpoint      # inherited by every lane's Playwright
                return run(args, wanted)
        except WebkitUnavailable as stop:
            print(stop)
            return 1


def run(args, wanted):
    wanted = int(os.environ.get("E2E_LANES", DEFAULT_LANES))
    if not 1 <= wanted <= MAX_LANES:
        sys.exit(f"E2E_LANES must be 1 to {MAX_LANES}, not {wanted}")
    lanes = lane_count(args, wanted)
    started = time.monotonic()
    if lanes == 1:
        code = subprocess.run(subprocess.list2cmdline(["npx", "playwright", "test", *args]), cwd=FRONTEND,
                              shell=True).returncode
        return code
    print(f"{lanes} lanes; each lane's output in scratch/e2e-lanes/")
    create_databases(lanes)
    failed = run_lanes(lanes, args)
    merged = merge()
    print(f"All lanes done in {time.monotonic() - started:.0f} s")
    return 1 if failed or not merged else 0


if __name__ == "__main__":
    # UTF-8 for the Windows console; line-buffered so the lane lines come before the merge's
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main(sys.argv[1:]))
