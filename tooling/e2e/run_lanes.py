"""The browser tests at a level (S047), in parallel lanes.  Each lane runs on its own stack
(database vel_yantra_lane<n>_e2e, backend 5010 + n, Vite 5180 + n, files scratch/e2e-data/
lane<n>), so lanes share nothing and cannot race.  Run by tooling/run-e2e-tests.bat after its
checks; the other arguments go to Playwright (spec files, --project=…, -g …).

    --level=basic    the @smoke tests (journeys.spec.js, screens.spec.js) on phone-chromium
    --level=normal   the default: every test on phone-chromium, the @device tests on
                     desktop-chromium (E2E_LEVEL=normal, read by playwright.config.js)
    --level=full     every test on all three projects (the release)
    E2E_LANES=<n>    the number of lanes (default 6); 1 runs the single stack as before

A level adds its --project arguments only when the caller names none; a caller who names
projects gets every matching test on them, with no @device filter.  Basic refuses a --grep.

The lanes are planned, not sharded: one `playwright test --list` run gives the tests of each
group (a spec file in one project; a group runs in one lane, as fullyParallel is off).  Each
group is weighed as its tests now × its measured seconds per test (scratch/e2e-timings.json,
updated after every lane run), and the groups are packed longest first, each into the least
loaded lane (LPT).  A lane gets its groups in E2E_LANE_PLAN, which playwright.config.js turns
into projects and testMatch.  A run that names tests by line (x.spec.js:42), or a positional
argument that is not a plain spec file, falls back to Playwright's --shard.

Each lane's output goes to scratch/e2e-lanes/lane<n>.log; the runner prints the plan and one
line per lane, then merges the lanes' blob reports into scratch/e2e-report/html (and
results.json, read for the timings) and prints the failures and totals once.  Exit 0 when
every lane passed, the merge worked and a test ran, else 1.  Stdlib only.

One run at a time on this machine: every run (lanes or the single stack) uses the same ports,
databases and folders, and each backend drops its database at start, so two runs at once
spoil each other (22-10-2026: two windows' runs, 12 failures).  A run holds an exclusive lock
on scratch/e2e-run.lock of the main working folder (the parent of git's common dir), so a run
from the release's worktree (tooling/release-tests.bat) and a run from the working folder wait
for each other; a second run waits for it.  The operating system releases the lock when the
process ends, a crash included, so a stale lock cannot block.

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
case-insensitive, `*` wildcards) starts no container; a wildcard may match it, so it starts one.
The levels are expanded first, so Basic and Normal (Chromium projects) start none, Full one."""

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
RESULTS_JSON = REPORT_DIR / "results.json"     # playwright.merge.config.js's json reporter
LANE_LOGS = ROOT / "scratch" / "e2e-lanes"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "tooling" / "dev" / "docker-compose.dev.yml")]
DEV_ROOT_PASSWORD = "dev-root-password"   # the dev compose file's; dev only
DB_USER = "vel_yantra_master"
DEFAULT_LANES = 6
MAX_LANES = 20                            # ports 5011–5030 and 5181–5200
LOCK_NAME = "e2e-run.lock"
TIMINGS_NAME = "e2e-timings.json"
LOCK_POLL_SECONDS = 10
LEVELS = ("basic", "normal", "full")
DEFAULT_LEVEL = "normal"
LOGIC_PROJECT = "phone-chromium"          # the shop floor's phone carries the logic tests (S047)
NORMAL_PROJECTS = (LOGIC_PROJECT, "desktop-chromium")
SECONDS_PER_TEST_UNMEASURED = 3           # a group's weight when nothing at all is measured
MEASURED_STATUSES = ("passed", "skipped")  # the results whose time goes into the timings
# Playwright options whose value is the next argument, so the value is not read as a spec file.
# An option missing here makes its value look like a positional argument; the run then falls
# back to --shard, which is slower but right.
VALUE_OPTIONS = {"-g", "--grep", "--grep-invert", "--timeout", "--repeat-each", "--retries", "--reporter",
                 "-j", "--workers", "--max-failures", "--trace", "--global-timeout", "--shard", "--output"}
PLAIN_SPEC = re.compile(r"^[\w./\\-]+\.spec\.js$")
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
LEVEL_UNKNOWN = "Use --level=basic, normal or full."
BASIC_GREP = "Basic runs the smoke tests only. To run chosen tests, use Normal with the spec file and -g."
SHARD_FALLBACK = "This run names tests by line, so the lanes are split by Playwright's --shard."


class Refused(Exception):
    """A run the runner does not start; the message says why and what to use instead."""


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


# ---------------------------------------------------------------------------------------------
# Levels (S047)
# ---------------------------------------------------------------------------------------------

def read_level(args):
    """args -> (level, the args without --level=…).  No flag is Normal."""
    level, rest = DEFAULT_LEVEL, []
    for arg in args:
        if arg == "--level" or arg.startswith("--level="):
            level = arg.partition("=")[2]
            if level not in LEVELS:
                raise Refused(LEVEL_UNKNOWN)
        else:
            rest.append(arg)
    return level, rest


def _is_grep(arg):
    return arg in ("-g", "--grep", "--grep-invert") or arg.startswith(("--grep=", "--grep-invert=", "-g="))


def expand_level(level, args):
    """A level as Playwright arguments -> (args, extra environment).  The level's projects are
    added only when the caller named none, and only then does Normal filter desktop to @device
    (E2E_LEVEL): a caller's --project=desktop-chromium runs every matching test there."""
    named = bool(named_projects(args))
    if level == "basic":
        if any(_is_grep(arg) for arg in args):
            raise Refused(BASIC_GREP)
        return ([] if named else [f"--project={LOGIC_PROJECT}"]) + list(args) + ["--grep", "@smoke"], {}
    if level == "normal" and not named:
        return [f"--project={project}" for project in NORMAL_PROJECTS] + list(args), {"E2E_LEVEL": "normal"}
    return list(args), {}


# ---------------------------------------------------------------------------------------------
# The lane plan (S047): groups from --list, weights from the timings, LPT packing
# ---------------------------------------------------------------------------------------------

def split_args(args):
    """args -> (positional arguments, the other arguments in their order, without --project and
    its names).  --project is variadic (as named_projects); a VALUE_OPTIONS option keeps its value."""
    positional, others = [], []
    reading_projects = taking_value = False
    for arg in args:
        if taking_value:
            others.append(arg)
            taking_value = False
        elif arg == "--project" or arg.startswith("--project="):
            reading_projects = arg == "--project"
        elif arg.startswith("-"):
            reading_projects = False
            others.append(arg)
            taking_value = arg in VALUE_OPTIONS
        elif not reading_projects:
            positional.append(arg)
    return positional, others


def plannable(positional):
    """Planned lanes need whole spec files: a test named by line, or a filter that is not a spec
    file, cannot become a lane's testMatch."""
    return all(PLAIN_SPEC.match(arg) for arg in positional)


def lane_arguments(others):
    """A planned lane's Playwright arguments: the plan replaces the spec files and the projects,
    and a --shard has no place; every other argument passes through as given."""
    kept, skip_value = [], False
    for arg in others:
        if skip_value:
            skip_value = False
        elif arg == "--shard":
            skip_value = True
        elif not arg.startswith("--shard="):
            kept.append(arg)
    return kept


def _tests_of(report):
    """(project, spec file, test) of every test in a Playwright JSON report, nested suites included."""
    def walk(suite):
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                yield test["projectName"], spec["file"], test
        for inner in suite.get("suites", []):
            yield from walk(inner)

    for suite in report.get("suites", []):
        yield from walk(suite)


def groups_of(report):
    """The --list run's JSON report -> {(project, spec file): tests}."""
    counts = {}
    for project, file, _test in _tests_of(report):
        counts[(project, file)] = counts.get((project, file), 0) + 1
    return counts


def measured_groups(report):
    """A run's merged JSON report -> {(project, spec file): (tests that ran, seconds)}.  A test
    counts when its last result passed or was skipped at run time (the --list count includes it).
    A failed test's time says nothing about the next run (a dead stack fails each test at its
    timeout), so it is left out, and a group with no counted test keeps its earlier timing."""
    measured = {}
    for project, file, test in _tests_of(report):
        results = test.get("results") or []
        if results and results[-1].get("status") in MEASURED_STATUSES:
            tests, seconds = measured.get((project, file), (0, 0.0))
            measured[(project, file)] = (tests + 1, seconds + sum(r.get("duration", 0) for r in results) / 1000)
    return measured


def group_key(project, file):
    return f"{project} {file}"


def updated_timings(timings, measured):
    """The stored timings with this run's groups replaced; the groups it did not run are kept."""
    new = dict(timings)
    for (project, file), (tests, seconds) in measured.items():
        new[group_key(project, file)] = {"tests": tests, "seconds": round(seconds, 1)}
    return new


def group_weights(groups, timings):
    """{group: tests now} -> {group: estimated seconds} = tests now × the group's measured seconds
    per test.  An unmeasured group takes the mean over the measured groups (3 s when none is)."""
    measured = {key: entry for key, entry in timings.items() if entry.get("tests")}
    total_tests = sum(entry["tests"] for entry in measured.values())
    mean = (sum(entry["seconds"] for entry in measured.values()) / total_tests
            if total_tests else SECONDS_PER_TEST_UNMEASURED)
    weights = {}
    for (project, file), tests in groups.items():
        stored = measured.get(group_key(project, file))
        per_test = stored["seconds"] / stored["tests"] if stored else mean
        weights[(project, file)] = tests * per_test
    return weights


def plan_lanes(weights, wanted):
    """LPT (longest processing time first): each group, longest first, into the lane with the
    least total so far -> [(total seconds, [groups])], one entry per lane, at most `wanted`."""
    lanes = [[0.0, []] for _ in range(min(wanted, len(weights)))]
    for group, weight in sorted(weights.items(), key=lambda item: (-item[1], item[0])):
        lane = min(lanes, key=lambda entry: entry[0])
        lane[0] += weight
        lane[1].append(group)
    return [(total, groups) for total, groups in lanes]


def plan_line(number, total, groups):
    names = ", ".join(group_key(project, file) for project, file in groups)
    return f"lane {number} plan: {len(groups)} groups, {total:.0f} s ({names})"


def lane_plan_env(groups):
    """E2E_LANE_PLAN of a lane: {project: [spec files]}, as playwright.config.js reads it."""
    plan = {}
    for project, file in groups:
        plan.setdefault(project, []).append(file)
    return json.dumps(plan)


# ---------------------------------------------------------------------------------------------
# The machine's lock and the timings, in the main working folder (S047)
# ---------------------------------------------------------------------------------------------

def main_scratch(root=ROOT):
    """The main working folder's scratch/ (the parent of git's common dir), so the release's
    worktree and the working folder share one lock.  ROOT's own, with one line, when git cannot tell."""
    try:
        found = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                               cwd=root, capture_output=True, text=True)
    except OSError:
        found = None
    if found is not None and found.returncode == 0 and found.stdout.strip():
        return Path(found.stdout.strip()).parent / "scratch"
    fallback = root / "scratch"
    print(f"Git did not find the main working folder, so the e2e lock is in {fallback / LOCK_NAME}.")
    return fallback


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------------------------
# WebKit in Docker (S046)
# ---------------------------------------------------------------------------------------------

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
        docker_error = handed_over.stderr.strip()
        raise WebkitUnavailable((docker_error + "\n" if docker_error else "") + webkit_failure("cache"))
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


# ---------------------------------------------------------------------------------------------
# Running (the shell)
# ---------------------------------------------------------------------------------------------

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


def _playwright(args):
    # shell: npx is npx.cmd on Windows
    return subprocess.list2cmdline(["npx", "playwright", "test", *args])


def list_groups(args):
    """The tests the run's arguments select, per group, from one --list run (no web server, no
    global setup) with the lanes' environment -> ({group: tests}, None) or (None, the error output)."""
    # --pass-with-no-tests: an empty selection is not an error here, run() says "No test matches"
    listed = subprocess.run(_playwright(["--list", "--pass-with-no-tests", "--reporter=json", *args]),
                            cwd=FRONTEND, shell=True,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = listed.stdout
    try:
        report = json.loads(text[text.index("{"):])
    except ValueError:
        return None, (listed.stderr or text).strip()
    # A spec file that cannot load makes Playwright list no test at all, from any file
    errors = [error.get("message", "") for error in report.get("errors") or []]
    if errors or listed.returncode != 0:
        details = "\n".join(errors) or listed.stderr.strip()
        return None, f"{details}\n(playwright --list exit code {listed.returncode})".strip()
    return groups_of(report), None


def run_lanes(lane_runs):
    """lane_runs: [(Playwright arguments, extra environment)], one per lane -> True if a lane failed."""
    shutil.rmtree(BLOBS_DIR, ignore_errors=True)
    running = []
    for lane, (args, extra_env) in enumerate(lane_runs, start=1):
        log = open(LANE_LOGS / f"lane{lane}.log", "w", encoding="utf-8")
        env = {**os.environ, "E2E_LANE": str(lane), **extra_env}
        running.append((lane, log, subprocess.Popen(_playwright(args), cwd=FRONTEND, env=env,
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
    """The lanes' blob zips into one folder, then one HTML report, results.json and one failure list."""
    shutil.rmtree(MERGED_DIR, ignore_errors=True)
    RESULTS_JSON.unlink(missing_ok=True)
    MERGED_DIR.mkdir(parents=True)
    for blob in BLOBS_DIR.glob("*/*.zip"):
        shutil.copy(blob, MERGED_DIR / f"{blob.parent.name}-{blob.name}")
    if not any(MERGED_DIR.iterdir()):
        print("No blob reports to merge: no lane ran a test.")
        return False
    command = ["npx", "playwright", "merge-reports", "--config", "playwright.merge.config.js", str(MERGED_DIR)]
    return subprocess.run(subprocess.list2cmdline(command), cwd=FRONTEND, shell=True).returncode == 0


@contextlib.contextmanager
def one_run_at_a_time(lock_file):
    """Hold the machine's e2e lock for the run; wait while another run holds it."""
    handle = open(lock_file, "a+")
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
    try:
        level, rest = read_level(args)
        args, level_env = expand_level(level, rest)
    except Refused as refused:
        print(refused)
        return 1
    # A caller's E2E_LEVEL must not filter a run whose projects the level did not choose
    os.environ.pop("E2E_LEVEL", None)
    os.environ.update(level_env)             # inherited by the --list run and every lane
    shared = main_scratch()
    # scratch/ is gitignored: a fresh worktree has none, and the backend's log redirect needs it
    for folder in (ROOT / "scratch", shared, LANE_LOGS):
        folder.mkdir(parents=True, exist_ok=True)
    with one_run_at_a_time(shared / LOCK_NAME):
        if not needs_webkit_server(args, webkit_mode()):
            return run(args, wanted, shared / TIMINGS_NAME)
        try:
            with webkit_server(playwright_version()) as endpoint:
                os.environ["E2E_WEBKIT_WS"] = endpoint      # inherited by every lane's Playwright
                return run(args, wanted, shared / TIMINGS_NAME)
        except WebkitUnavailable as stop:
            print(stop)
            return 1


def single_stack(args):
    return subprocess.run(_playwright(args), cwd=FRONTEND, shell=True).returncode


def run(args, wanted, timings_file):
    started = time.monotonic()
    if wanted == 1:
        return single_stack(args)
    groups, error = list_groups(args)
    if groups is None:
        print(f"The tests could not be listed:\n{error}")
        return 1
    if not groups:
        print(f"No test matches these arguments: {subprocess.list2cmdline(args)}.")
        return 1
    lanes = min(wanted, len(groups))
    if lanes == 1:
        return single_stack(args)
    positional, others = split_args(args)
    if plannable(positional):
        plan = plan_lanes(group_weights(groups, read_json(timings_file)), lanes)
        for number, (total, lane_groups) in enumerate(plan, start=1):
            print(plan_line(number, total, lane_groups))
        # A planned lane always has tests, so no --pass-with-no-tests: an empty lane is a fault
        lane_runs = [(lane_arguments(others), {"E2E_LANE_PLAN": lane_plan_env(lane_groups)})
                     for _total, lane_groups in plan]
    else:
        print(SHARD_FALLBACK)
        # Playwright reports "No tests found" only without --shard, so the flag changes nothing here;
        # the check of the merged totals below is the guard against a run of no test
        lane_runs = [([f"--shard={n}/{lanes}", "--pass-with-no-tests", *args], {}) for n in range(1, lanes + 1)]
    print(f"{lanes} lanes; each lane's output in scratch/e2e-lanes/")
    create_databases(lanes)
    failed = run_lanes(lane_runs)
    merged = merge()
    results = read_json(RESULTS_JSON)
    measured = measured_groups(results)
    if measured:
        timings_file.write_text(json.dumps(updated_timings(read_json(timings_file), measured), indent=1,
                                           sort_keys=True), encoding="utf-8")
    ran = any(test.get("results") for _project, _file, test in _tests_of(results))
    if merged and not ran:
        print("No test ran.")
    print(f"All lanes done in {time.monotonic() - started:.0f} s")
    return 1 if failed or not merged or not ran else 0


if __name__ == "__main__":
    # UTF-8 for the Windows console; line-buffered so the lane lines come before the merge's
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main(sys.argv[1:]))
