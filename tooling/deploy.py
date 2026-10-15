"""Deploy step for the release pipeline (DEPLOY_SCRIPT for tooling/common/release.py).

Yantra is deployed by Ansible from the Ansible workstation (smtw_erp_devops,
erp_server/yantra/deploy.yaml). Its compose file pins the image tag to
YANTRA_VER, so a release must (1) stamp the new version into the settings yaml
on ansible-ws and (2) run the Ansible deploy there. Both go over a saved PuTTY
session (plink), like VELGeoMaster's stamp step, plus the erp_spanner.py run.

Config — environment variables (set in the Release run configs; a
tooling/common/release.env is read too, already-set variables win):
    DEPLOY_WS_SESSION      saved PuTTY session name for ansible-ws    (required)
    DEPLOY_ERP_SERVER_DIR  smtw_erp_devops/erp_server dir on ansible-ws (required)
    PLINK                  plink executable, PATH-resolved            (default: plink)

Usage:
    python tooling/deploy.py               # stamp VERSION, then run the Ansible deploy
    python tooling/deploy.py --stamp-only  # stamp VERSION, leave the deploy to a person
    python tooling/deploy.py --check       # read-only: show host and the stamped line

plink runs with -batch so it never prompts — the session's host key must already
be cached (connect once interactively first). Exits non-zero on any failure so
release.py aborts the release before its final git push.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

load_dotenv(PROJECT_ROOT / "tooling" / "common" / "release.env")

SESSION = os.getenv("DEPLOY_WS_SESSION")
ERP_SERVER_DIR = os.getenv("DEPLOY_ERP_SERVER_DIR")
PLINK = os.getenv("PLINK", "plink")

# Deployment this repo releases to — erp_spanner.py <org> <app> <instance>
DEPLOY_TARGET = "vel yantra master"
# Settings yaml (relative to erp_server/) and the key holding the image tag.
# The tag is the bare VERSION (build.bat tags images 0.1.2, not v0.1.2).
VARS_FILE = "yantra/vars/settings_vel_yantra_master.yaml"
VER_KEY = "YANTRA_VER"

# erp_spanner.py reports a failed playbook but still exits 0 — detect it in the output
_FAILED_RECAP = re.compile(r"\b(failed|unreachable)=([1-9]\d*)")
_SPANNER_ERROR = "Error executing Ansible playbook"


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


def stamp(version):
    """Set VER_KEY to the version in the settings yaml. Fails closed if the key is missing."""
    target = f'{VER_KEY}: "{version}"'
    remote_cmd = (
        f"set -e; cd {ERP_SERVER_DIR}; "
        f"grep -q '^{VER_KEY}:' {VARS_FILE}; "
        f"sed -i 's|^{VER_KEY}:.*|{target}|' {VARS_FILE}; "
        f"grep '^{VER_KEY}:' {VARS_FILE}"
    )
    result = run_remote(remote_cmd)
    if result.returncode != 0:
        print("ABORT: stamping the version on ansible-ws failed (missing key, file or dir?).")
        return False
    if target not in result.stdout:
        print(f"ABORT: vars file does not show the expected line after edit: {target}")
        return False
    return True


def deploy():
    """Run the Ansible deploy on ansible-ws; True only if the playbook really succeeded."""
    returncode, output = run_remote_streaming(f"cd {ERP_SERVER_DIR} && ./erp_spanner.py deploy {DEPLOY_TARGET}")
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


def main():
    missing = [name for name, val in (("DEPLOY_WS_SESSION", SESSION),
                                      ("DEPLOY_ERP_SERVER_DIR", ERP_SERVER_DIR)) if not val]
    if missing:
        print(f"ABORT: not set: {', '.join(missing)} (Release run config env, or tooling/common/release.env)")
        return 1

    args = sys.argv[1:]
    if "--check" in args:
        result = run_remote(f"hostname && cd {ERP_SERVER_DIR} && grep '^{VER_KEY}:' {VARS_FILE}")
        if result.returncode != 0:
            print("ABORT: check failed — session, directory, file or key is wrong.")
        return result.returncode

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"ABORT: invalid version {version!r} in {VERSION_FILE}")
        return 1

    if not stamp(version):
        return 1
    print(f"Stamped {VER_KEY} {version} on ansible-ws.")

    if "--stamp-only" in args:
        print(f"Not deployed. Roll out with: erp_spanner.py deploy {DEPLOY_TARGET} (on ansible-ws)")
        return 0

    if not deploy():
        return 1
    print(f"Deployed Yantra {version} ({DEPLOY_TARGET}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
