"""Run one test suite, keep its whole output in a log, and end with one summary line that an
agent always sees, however much of the output a tool cuts off.

    uv run --no-project python tooling/run_logged.py <label> <log file> -- <command> [args...]

The command's output goes to the console and to the log file as it comes.  At the end:

    == backend: PASSED in 58 s: 2277 passed, 4 skipped (log: C:\\...\\scratch\\backend-tests.log)

When YANTRA_TEST_SUMMARY names a file, the line is also appended to it: run-tests.bat prints
that file's lines again after the last suite.  The exit code is the command's.  Stdlib only.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# pytest: "2277 passed, 4 skipped in 58.1s"; vitest: "Tests  114 passed (114)"
COUNTS = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected|todo)\b")


def counts_of(output):
    """The counts of the last line that has any, e.g. '2277 passed, 4 skipped'."""
    for line in reversed(ANSI.sub("", output).splitlines()):
        found = COUNTS.findall(line)
        if found:
            return ", ".join(f"{n} {kind}" for n, kind in found)
        if "no tests ran" in line:
            return "no tests ran"
    return "no test counts found"


def summary_line(label, exit_code, seconds, output, log_path):
    verdict = "PASSED" if exit_code == 0 else f"FAILED (exit {exit_code})"
    return f"== {label}: {verdict} in {seconds:.0f} s: {counts_of(output)} (log: {log_path})"


def run(label, log_path, command):
    log_path = Path(log_path).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # A .cmd/.bat (npm, npx) runs only by its full name on Windows
    executable = shutil.which(command[0]) or command[0]
    started = time.monotonic()
    captured = []
    with open(log_path, "w", encoding="utf-8") as log:
        # UTF-8 from a Python child (pytest) too, whatever the console's code page
        process = subprocess.Popen([executable, *command[1:]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", bufsize=1,
                                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log.write(line)
            captured.append(line)
        exit_code = process.wait()
    line = summary_line(label, exit_code, time.monotonic() - started, "".join(captured), log_path)
    print(line, flush=True)
    summary_file = os.environ.get("YANTRA_TEST_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as out:
            out.write(line + "\n")
    return exit_code


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    if len(argv) < 4 or argv[2] != "--":
        print("usage: run_logged.py <label> <log file> -- <command> [args...]", file=sys.stderr)
        return 2
    return run(argv[0], argv[1], argv[3:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
