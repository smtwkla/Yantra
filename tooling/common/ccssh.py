#!/usr/bin/env python3
"""ccssh.py — restricted SSH wrapper for Claude Code production-VM diagnostics.

Claude Code must use this tool (never ssh/plink directly) to reach production
VMs. It enforces, in code, what would otherwise be convention:

  - always connects as the restricted read-only user (claude_ro) with its
    dedicated key — there is no argument that selects another identity
  - host keys are pinned in a dedicated known_hosts file; unknown or changed
    host keys fail loudly (BatchMode, StrictHostKeyChecking)
  - every command is echoed before execution and appended to a per-machine
    log on the dev machine

Machine list, known_hosts and key live OUTSIDE all repos (nothing sensitive
is ever committed):

  ~/.claude/prod-vm/vms.tsv      tab-separated: alias  host  [port]  [notes]
  ~/.claude/prod-vm/known_hosts  pinned host keys (append after verifying!)
  ~/.ssh/claude_ro_ed25519       private key (generate: ssh-keygen -t ed25519)
  ~/.claude/logs/prod-vm/        per-machine command logs

Usage:
  ccssh.py list                                 show known machines
  ccssh.py scan <alias>                         fetch host keys for pinning
  ccssh.py run [-m REASON] <alias> <command...> run a command on the machine

This script is synced across repos from smtw-common (see sync_common.py).
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SSH_USER = "claude_ro"
KEY_FILE = Path.home() / ".ssh" / "claude_ro_ed25519"
CONFIG_DIR = Path.home() / ".claude" / "prod-vm"
VMS_FILE = CONFIG_DIR / "vms.tsv"
KNOWN_HOSTS = CONFIG_DIR / "known_hosts"
LOG_DIR = Path.home() / ".claude" / "logs" / "prod-vm"

# Aliases and hostnames must be plain names — this also guarantees a value
# from vms.tsv can never be mistaken for an ssh option.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Preference order matters: the Windows built-in OpenSSH (9.5p1) fails
# against Ubuntu 24.04 sshd offering sntrup761x25519 KEX ("choose_kex:
# unsupported KEX method"); Git for Windows bundles a newer OpenSSH that
# handles it. PATH is the last resort.
OPENSSH_DIRS = (
    Path(r"C:\Program Files\Git\usr\bin"),
    Path(r"C:\Windows\System32\OpenSSH"),
)


def die(msg: str) -> "NoReturn":
    print(f"ccssh: error: {msg}", file=sys.stderr)
    sys.exit(2)


def find_exe(name: str) -> str:
    for d in OPENSSH_DIRS:
        candidate = d / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if not found:
        die(f"{name} not found - install Git for Windows or the Windows OpenSSH client")
    return found


def fwd(p: Path) -> str:
    """Forward-slash path form - accepted by both Windows and MSYS OpenSSH."""
    return str(p).replace("\\", "/")


def load_vms() -> dict:
    """Parse vms.tsv into {alias: {host, port, notes}}."""
    if not VMS_FILE.exists():
        die(f"machine list not found: {VMS_FILE}\n"
            "Create it (tab-separated: alias<TAB>host<TAB>[port]<TAB>[notes]) - "
            "see tooling/common/example_vms.tsv in the smtw-common repo")
    vms = {}
    for lineno, line in enumerate(VMS_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split("\t") if c.strip()]
        if len(cols) < 2:
            die(f"{VMS_FILE}:{lineno}: need at least alias<TAB>host")
        alias, host = cols[0], cols[1]
        port = cols[2] if len(cols) > 2 and cols[2].isdigit() else "22"
        notes = "\t".join(cols[3:]) if len(cols) > 3 else (
            cols[2] if len(cols) > 2 and not cols[2].isdigit() else "")
        if not NAME_RE.match(alias) or not NAME_RE.match(host):
            die(f"{VMS_FILE}:{lineno}: invalid alias or host '{alias}'/'{host}'")
        if not 1 <= int(port) <= 65535:
            die(f"{VMS_FILE}:{lineno}: invalid port '{port}'")
        if alias in vms:
            die(f"{VMS_FILE}:{lineno}: duplicate alias '{alias}'")
        vms[alias] = {"host": host, "port": port, "notes": notes}
    return vms


def get_vm(vms: dict, alias: str) -> dict:
    if alias not in vms:
        known = ", ".join(sorted(vms)) or "(none)"
        die(f"unknown machine '{alias}' - known: {known}")
    return vms[alias]


def cmd_list(_args) -> int:
    vms = load_vms()
    for alias, vm in sorted(vms.items()):
        port = f":{vm['port']}" if vm["port"] != "22" else ""
        notes = f"  # {vm['notes']}" if vm["notes"] else ""
        print(f"{alias}\t{vm['host']}{port}{notes}")
    return 0


def cmd_scan(args) -> int:
    """Print host keys so the USER can verify and pin them.

    Deliberately does NOT write known_hosts — comparing the fingerprint
    against the VM console and appending the line is the user's act.
    With no alias, scans every machine in the list (failures reported,
    scan continues).
    """
    vms = load_vms()
    aliases = [args.alias] if args.alias else sorted(vms)
    keyscan = find_exe("ssh-keyscan")
    keys, failed = [], []
    for alias in aliases:
        vm = get_vm(vms, alias)
        result = subprocess.run(
            [keyscan, "-p", vm["port"], "-t", "ed25519", vm["host"]],
            capture_output=True, text=True)
        out = result.stdout.strip()
        if result.returncode != 0 or not out:
            err = result.stderr.strip().splitlines()
            failed.append(f"{alias} ({vm['host']}): {err[-1] if err else 'no key returned'}")
        else:
            keys.append(out)
    for line in keys:
        print(line)
    if failed:
        print("\nFailed to scan:", file=sys.stderr)
        for f in failed:
            print(f"  {f}", file=sys.stderr)
    if keys:
        print("\nVerify each fingerprint on the VM console first:", file=sys.stderr)
        print("  ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub", file=sys.stderr)
        print(f"then append the verified line(s) to: {KNOWN_HOSTS}", file=sys.stderr)
    return 1 if failed else 0


def log_run(alias: str, host: str, command: str, reason: str, rc: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp}  exit={rc}  reason={reason or '-'}  $ {command}\n"
    with (LOG_DIR / f"{alias}.cc.log").open("a", encoding="utf-8") as f:
        f.write(line)


def cmd_run(args) -> int:
    if not args.command:
        die("no remote command given (interactive shells are not supported)")
    vm = get_vm(load_vms(), args.alias)
    if not KEY_FILE.exists():
        die(f"private key not found: {KEY_FILE}\n"
            f"Generate: ssh-keygen -t ed25519 -f {KEY_FILE} -C claude_ro")
    if not KNOWN_HOSTS.exists():
        die(f"pinned host keys not found: {KNOWN_HOSTS}\n"
            f"Run: ccssh.py scan {args.alias}  and follow the instructions")

    remote_cmd = " ".join(args.command)
    ssh_cmd = [
        find_exe("ssh"),
        "-l", SSH_USER,
        "-i", fwd(KEY_FILE),
        "-p", vm["port"],
        "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={fwd(KNOWN_HOSTS)}",
        "-o", "ConnectTimeout=10",
        "-T",
        "--", vm["host"], remote_cmd,
    ]
    print(f"[ccssh] {args.alias} ({vm['host']}) $ {remote_cmd}", file=sys.stderr)
    result = subprocess.run(ssh_cmd)
    log_run(args.alias, vm["host"], remote_cmd, args.reason, result.returncode)
    if result.returncode == 255:
        print("[ccssh] exit 255 - ssh connection/auth/hostkey failure "
              "(not the remote command's exit code)", file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ccssh.py",
        description="Restricted SSH wrapper for Claude Code prod-VM diagnostics "
                    f"(always connects as {SSH_USER}).")
    sub = parser.add_subparsers(dest="verb", required=True)

    sub.add_parser("list", help="show known machines").set_defaults(func=cmd_list)

    p_scan = sub.add_parser("scan", help="fetch host key(s) for manual pinning")
    p_scan.add_argument("alias", nargs="?",
                        help="machine alias; omit to scan ALL machines")
    p_scan.set_defaults(func=cmd_scan)

    p_run = sub.add_parser("run", help="run a command on a machine")
    p_run.add_argument("-m", "--reason", default="",
                       help="why this command is being run (logged)")
    p_run.add_argument("alias")
    p_run.add_argument("command", nargs=argparse.REMAINDER,
                       help="remote command (everything after the alias)")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
