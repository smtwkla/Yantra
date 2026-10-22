"""The browser tests in parallel lanes: each lane is one Playwright shard on its own stack
(database vel_yantra_lane<n>_e2e, backend 5010 + n, Vite 5180 + n, files scratch/e2e-data/
lane<n>), so lanes share nothing and cannot race.  Run by tooling/run-e2e-tests.bat after
its checks; extra arguments go to every lane's Playwright (a spec file, --project=…).

    E2E_LANES=<n>   the number of lanes (default 6); 1 runs the single stack as before

Each lane's output goes to scratch/e2e-lanes/lane<n>.log; the runner prints one line per lane,
then merges the lanes' blob reports into scratch/e2e-report/html and prints the failures and
totals once.  Exit 0 when every lane passed and the merge worked, else 1.  Stdlib only."""

import os
import re
import shutil
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
SUMMARY = re.compile(r"^\s*(\d+) (passed|failed|flaky|skipped|did not run)", re.MULTILINE)


def lane_count(args, wanted):
    """No more lanes than test groups: a shard is a spec file in one project, so a run of two
    spec files on one project needs two lanes, not six."""
    specs = [a for a in args if a.endswith(".spec.js")]
    projects = [a for a in args if a.startswith("--project")]
    if not specs and not projects:
        return wanted
    groups = (len(specs) or len(list((FRONTEND / "e2e").glob("*.spec.js")))) * (len(projects) or PROJECT_COUNT)
    return max(1, min(wanted, groups))


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


def main(args):
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
