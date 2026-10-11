#!/usr/bin/env python3
"""guard-common.py — single PreToolUse policy hook for all SMTW repos.

Synced from smtw-common (.claude/hooks). Registered ONCE per dev machine in
~/.claude/settings.json under hooks.PreToolUse
(matcher "Bash|PowerShell|Read|Write|Edit|Grep") as:

    py -3 .claude/hooks/guard-common.py 2>/dev/null || true

The registration never changes; policy updates ship as edits to this file
via smtw-common push + sync_common.py. Replaces the former
block-secrets-common.sh (jq-dependent, silently broken without jq) and
block-direct-ssh-common.sh.

Denies:
  1. Secrets-file access — secrets_*.py, settings_*.yml/.yaml, .env* / *.env —
     whether via file tools (file_path/path) or mentioned in a shell command
     line. example_* templates are always allowed.
  2. Direct SSH-client invocations (ssh/scp/sftp/plink/pscp/putty) anywhere in
     a shell command line — production access must go through
     tooling/common/ccssh.py (see the prod-vm skill).

RULES for editing this file:
  - stdlib only. The interpreter may be any Python (system, venv, uv) —
    third-party imports would break it silently.
  - fail open: an internal error must never block the tool call
    (empty output + exit 0 means "allow").
  - a deny is JSON on stdout with permissionDecision "deny".
"""
import json
import os
import re
import sys

SSH_CLIENT_RE = re.compile(
    r'(^|[;&|(`\s"\x27/\\])(ssh|scp|sftp|plink|pscp|putty)(\.exe)?(\s|"|\x27|$)',
    re.IGNORECASE)

# Secrets filenames, matched against a basename. example_* is exempted in code.
SECRET_BASENAME_RE = re.compile(
    r'^(secrets_[\w.-]*\.py'
    r'|settings_[\w.-]*\.ya?ml'
    r'|\.env([._-][\w.-]+)?'   # .env, .env-common, .env.production ...
    r'|[\w.-]+\.env'           # aws.env ... (but not aws.env.j2 templates)
    r')$',
    re.IGNORECASE)

# The same filenames appearing as a token anywhere in a shell command line.
SECRET_IN_COMMAND_RE = re.compile(
    r'(^|[\s"\x27=/\\(;&|])(?!example_)'
    r'(secrets_[\w.-]*\.py'
    r'|settings_[\w.-]*\.ya?ml'
    r'|\.env([._-][\w.-]+)?'
    r'|[\w.-]+\.env'
    r')($|[\s"\x27);&|])',
    re.IGNORECASE)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return

    # File tools: Read/Write/Edit carry file_path, Grep carries path.
    for field in ("file_path", "path"):
        target = tool_input.get(field) or ""
        basename = os.path.basename(str(target).replace("\\", "/"))
        if basename and not basename.lower().startswith("example_") \
                and SECRET_BASENAME_RE.match(basename):
            deny(f"Access to secrets file '{basename}' is blocked for "
                 "security (example_* templates are allowed)")

    # Shell tools: Bash/PowerShell carry command.
    command = str(tool_input.get("command") or "")
    if command:
        if SSH_CLIENT_RE.search(command):
            deny("Direct SSH clients are blocked - use: "
                 "python tooling/common/ccssh.py run -m <reason> <alias> "
                 "<command> (see prod-vm skill)")
        if SECRET_IN_COMMAND_RE.search(command):
            deny("Command references a secrets file (secrets_*/settings_*/"
                 ".env*) - blocked for security (example_* templates are "
                 "allowed)")


if __name__ == "__main__":
    main()
    sys.exit(0)
