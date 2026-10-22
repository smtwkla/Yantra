"""Deploy step for the release pipeline (DEPLOY_SCRIPT for tooling/common/release.py).

Yantra is deployed by Ansible from the Ansible workstation (smtw_erp_devops,
erp_server/yantra/deploy.yaml). Its compose file pins the image tag to
YANTRA_VER, so a release must (1) stamp the new version into the settings yaml
on ansible-ws and (2) run the Ansible deploy there. Both go over a saved PuTTY
session (plink), like VELGeoMaster's stamp step, plus the erp_spanner.py run.
(3) It then waits until the new image reports its schema ready (S025 § 1.1).

Config — environment variables (set in the Release run configs; a
tooling/common/release.env is read too, already-set variables win):
    DEPLOY_WS_SESSION      saved PuTTY session name for ansible-ws    (required)
    DEPLOY_ERP_SERVER_DIR  smtw_erp_devops/erp_server dir on ansible-ws (required)
    DEPLOY_HEALTH_URL      public URL of /api/health                  (required for a deploy)
    PLINK                  plink executable, PATH-resolved            (default: plink)

Usage:
    python tooling/deploy.py               # stamp VERSION, run the Ansible deploy, wait for the schema
    python tooling/deploy.py --stamp-only  # stamp VERSION, leave the deploy to a person
    python tooling/deploy.py --check       # read-only: show host and the stamped line

After the playbook, the deploy polls DEPLOY_HEALTH_URL until it answers 200 with
"schema_ready": true: the new image has run its migrations. Any other answer, a
connection error or an nginx 502 while the backend starts counts as "not yet". On
any failure after the stamp it prints the rollback lines for the user to run on
ansible-ws (S025 § 5.4); production changes are the user's.

plink runs with -batch so it never prompts — the session's host key must already
be cached (connect once interactively first). Exits non-zero on any failure so
release.py aborts the release before its final git push.
"""

import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

load_dotenv(PROJECT_ROOT / "tooling" / "common" / "release.env")

SESSION = os.getenv("DEPLOY_WS_SESSION")
ERP_SERVER_DIR = os.getenv("DEPLOY_ERP_SERVER_DIR")
PLINK = os.getenv("PLINK", "plink")
HEALTH_URL = os.getenv("DEPLOY_HEALTH_URL")

# Deployment this repo releases to — erp_spanner.py <org> <app> <instance>
DEPLOY_TARGET = "vel yantra master"
# Settings yaml (relative to erp_server/) and the key holding the image tag.
# The tag is the bare VERSION (build.bat tags images 0.1.2, not v0.1.2).
VARS_FILE = "yantra/vars/settings_vel_yantra_master.yaml"
VER_KEY = "YANTRA_VER"

# erp_spanner.py reports a failed playbook but still exits 0 — detect it in the output
_FAILED_RECAP = re.compile(r"\b(failed|unreachable)=([1-9]\d*)")
_SPANNER_ERROR = "Error executing Ansible playbook"

# The schema-ready poll: every 10 s for up to 3 minutes.  At first boot the health call may
# wait on the migration lock while a migration runs; the 3 minutes cover it.
HEALTH_POLL_SECONDS = 10
HEALTH_TIMEOUT_SECONDS = 180
HEALTH_REQUEST_TIMEOUT_SECONDS = 10

# The stamped line as grep prints it:  YANTRA_VER: "0.1.3"
_STAMPED_RE = re.compile(r"^" + VER_KEY + r':\s*"?([^"\s]+)"?\s*$', re.MULTILINE)


def _plink(remote_cmd):
    print(f'> {PLINK} -batch {SESSION} "{remote_cmd}"', flush=True)
    return [PLINK, "-batch", SESSION, remote_cmd]


def run_remote(remote_cmd):
    """Run a short command on ansible-ws; return the CompletedProcess, output echoed."""
    try:
        result = subprocess.run(_plink(remote_cmd), capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        print(f"ABORT: '{PLINK}' not found on PATH. Install PuTTY or set PLINK.")
        sys.exit(127)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result


def run_remote_streaming(remote_cmd):
    """Run a long command on ansible-ws, streaming output; return (returncode, output)."""
    try:
        proc = subprocess.Popen(_plink(remote_cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"ABORT: '{PLINK}' not found on PATH. Install PuTTY or set PLINK.")
        sys.exit(127)
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    return proc.wait(), "".join(lines)


def _stamped_line(version):
    return f'{VER_KEY}: "{version}"'


def stamp_command(version):
    """The remote command that stamps ``version`` — run by stamp(), and printed as a rollback
    line, so the two never differ."""
    return (
        f"set -e; cd {ERP_SERVER_DIR}; "
        f"grep -q '^{VER_KEY}:' {VARS_FILE}; "
        f"sed -i 's|^{VER_KEY}:.*|{_stamped_line(version)}|' {VARS_FILE}; "
        f"grep '^{VER_KEY}:' {VARS_FILE}"
    )


def deploy_command():
    return f"cd {ERP_SERVER_DIR} && ./erp_spanner.py deploy {DEPLOY_TARGET}"


def parse_stamped_version(output):
    """The version in a ``YANTRA_VER: "0.1.3"`` line, or None."""
    match = _STAMPED_RE.search(output or "")
    return match.group(1) if match else None


def read_stamped_version():
    """The version stamped on ansible-ws now, before this deploy changes it, or None."""
    result = run_remote(f"cd {ERP_SERVER_DIR} && grep '^{VER_KEY}:' {VARS_FILE}")
    return parse_stamped_version(result.stdout) if result.returncode == 0 else None


def rollback_lines(previous):
    """What the user runs on ansible-ws to go back to ``previous`` (S025 § 5.4)."""
    return [
        "ROLLBACK - run on ansible-ws (production changes are yours):",
        "  If the new schema was NOT applied (the migration was refused, or the database was down;",
        "  Settings > Database shows the old schema version): stamp the previous version and redeploy:",
        f"    {stamp_command(previous)}",
        f"    {deploy_command()}",
        "  If the new schema WAS applied: the previous image does not run on it. First restore",
        "  db-server's latest dump of the database (ERP-DB-Backup share), then run the two lines above.",
    ]


def stamp(version):
    """Set VER_KEY to the version in the settings yaml. Fails closed if the key is missing."""
    target = _stamped_line(version)
    result = run_remote(stamp_command(version))
    if result.returncode != 0:
        print("ABORT: stamping the version on ansible-ws failed (missing key, file or dir?).")
        return False
    if target not in result.stdout:
        print(f"ABORT: vars file does not show the expected line after edit: {target}")
        return False
    return True


def deploy():
    """Run the Ansible deploy on ansible-ws; True only if the playbook really succeeded."""
    returncode, output = run_remote_streaming(deploy_command())
    if returncode != 0:
        print(f"ABORT: deploy command exited {returncode}.")
        return False
    if _SPANNER_ERROR in output or _FAILED_RECAP.search(output):
        print("ABORT: the Ansible playbook reported failures (see PLAY RECAP above).")
        return False
    if "PLAY RECAP" not in output:
        print("ABORT: no PLAY RECAP in the output — cannot confirm the playbook ran.")
        return False
    return True


def _schema_ready_once(url, opener):
    """One look at /api/health -> True only for a 200 with "schema_ready": true."""
    try:
        with opener(url, timeout=HEALTH_REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                return False
            return json.loads(response.read().decode("utf-8")).get("schema_ready") is True
    except (OSError, http.client.HTTPException, ValueError, AttributeError):
        # URLError and HTTPError (a 502 while the backend starts) are OSErrors; a connection cut
        # mid-answer (BadStatusLine, IncompleteRead, RemoteDisconnected) is an HTTPException or
        # an OSError; a body that is not JSON is a ValueError, and one that is not an object an
        # AttributeError: "not yet"
        return False


def wait_for_schema(url, opener=urllib.request.urlopen, clock=time.monotonic, sleep=time.sleep,
                    timeout=HEALTH_TIMEOUT_SECONDS, interval=HEALTH_POLL_SECONDS):
    """Poll ``url`` until the schema is ready -> True, or False once ``timeout`` has passed.
    ``opener``, ``clock`` and ``sleep`` are parameters for the tests."""
    deadline = clock() + timeout
    while True:
        if _schema_ready_once(url, opener):
            return True
        if clock() >= deadline:
            return False
        print(f"Schema not ready yet at {url}; checking again in {interval} s.", flush=True)
        sleep(interval)


def missing_settings(args):
    """The required variables not set for this run; the health URL only for a real deploy."""
    required = [("DEPLOY_WS_SESSION", SESSION), ("DEPLOY_ERP_SERVER_DIR", ERP_SERVER_DIR)]
    if "--check" not in args and "--stamp-only" not in args:
        required.append(("DEPLOY_HEALTH_URL", HEALTH_URL))
    return [name for name, val in required if not val]


def _fail_after_stamp(message, previous):
    print(message)
    for line in rollback_lines(previous):
        print(line)
    return 1


def main():
    args = sys.argv[1:]
    missing = missing_settings(args)
    if missing:
        print(f"ABORT: not set: {', '.join(missing)} (Release run config env, or tooling/common/release.env)")
        return 1

    if "--check" in args:
        result = run_remote(f"hostname && cd {ERP_SERVER_DIR} && grep '^{VER_KEY}:' {VARS_FILE}")
        if result.returncode != 0:
            print("ABORT: check failed — session, directory, file or key is wrong.")
        return result.returncode

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"ABORT: invalid version {version!r} in {VERSION_FILE}")
        return 1

    # Read before stamping, for the rollback lines; nothing has changed yet if this fails
    previous = read_stamped_version()
    if previous is None:
        print(f"ABORT: cannot read the current {VER_KEY} on ansible-ws; nothing changed.")
        return 1

    if not stamp(version):
        return 1
    print(f"Stamped {VER_KEY} {version} on ansible-ws (was {previous}).")

    if "--stamp-only" in args:
        print(f"Not deployed. Roll out with: erp_spanner.py deploy {DEPLOY_TARGET} (on ansible-ws)")
        return 0

    if not deploy():
        return _fail_after_stamp("ABORT: the deploy failed after the stamp.", previous)
    print(f"Playbook done. Waiting up to {HEALTH_TIMEOUT_SECONDS} s for the schema at {HEALTH_URL} ...")
    if not wait_for_schema(HEALTH_URL):
        return _fail_after_stamp(
            f"ABORT: {HEALTH_URL} did not report schema_ready within {HEALTH_TIMEOUT_SECONDS} s. "
            "Settings > Database shows why (a refused migration names what to do first).", previous)
    print(f"Deployed Yantra {version} ({DEPLOY_TARGET}); schema ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
