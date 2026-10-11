---
name: prod-vm
description: Rules and protocol for Claude Code when connecting to and operating on production VMs, and when reading the fleet's centralised logs to investigate what happened on them.
---

When the user asks Claude Code to connect to a production VM and perform actions, the following rules apply.

## Connection — ccssh only

All production VM access goes through the restricted wrapper (synced to every repo):

```
python tooling/common/ccssh.py list                                  # show known machines
python tooling/common/ccssh.py run [-m "<reason>"] <alias> <command> # run a remote command
python tooling/common/ccssh.py scan <alias>                          # fetch host key for pinning
```

- **Never invoke `ssh`, `plink`, `pscp`, or `scp` directly against a production machine.** The wrapper is the only permitted path.
- The wrapper always connects as `claude_ro`, a restricted read-only account (groups `adm` + `systemd-journal` for logs/journal; sudo limited to a whitelist of read-only docker commands: `docker ps`, `docker logs`, `docker inspect`, `docker compose ls|ps|logs`). It cannot escalate — do not try.
- **Never try to guess** an alias or hostname/ip. Use `ccssh.py list`; if the machine is not in the list, ask the user.
- The machine list lives at `~/.claude/prod-vm/vms.tsv` on the dev machine and must never be created inside a repo.
- Always pass `-m "<reason>"` so the reason is logged with the command.
- **Project the fields you need — never dump whole objects.** `docker inspect`
  and friends are read-only but their output is full of secrets. See
  [Secrets in Command Output](#secrets-in-command-output) below.

## Reading logs — ccloki only

Centralised logs (Loki) are read through the restricted wrapper (synced to every repo):

```
python tooling/common/ccloki.py show                       # configured store (no secrets)
python tooling/common/ccloki.py stats [-m R] <selector>    # how big is this fetch?
python tooling/common/ccloki.py logs  [-m R] <logql>       # fetch log lines
python tooling/common/ccloki.py labels|values|series|query # explore what is shipped
```

- **Never invoke `curl`, `wget`, or any other HTTP client against the log store.** The wrapper is the only permitted path, exactly as `ccssh.py` is for SSH.
- The wrapper is GET-only and reaches only Loki's query endpoints, so **everything it can do is Tier 1** — no separate authorization is needed to run a query. It cannot push, delete or flush; do not look for a tool that can.
- It authenticates with the **read** basic-auth pair, which is rejected by the push endpoint. Never ask for, or use, the write pair — that belongs to the Alloy shippers.
- Config and credential live at `~/.claude/prod-vm/loki.conf` on the dev machine and must never be created inside a repo. If it is missing or a query returns 401, show the error to the user and stop — **writing that file is the user's act.**
- Always pass `-m "<reason>"`.
- **Run `stats` before a wide fetch.** It reports how many lines a selector matches without transferring them. Fetching blind can pull thousands of lines into the conversation and strain the log store — narrow the window or add a filter first.
- **Absence of log lines is not proof that nothing happened.** Some hosts ship no logs at all, some services are silent by design, and some only log during working hours. Establish what is actually shipping before drawing a conclusion from silence — `values host`, `values unit`, `series` — and never report "nothing ran" on the strength of an empty result alone. Which hosts and services those are is fleet-specific and is not recorded in any repo; if you cannot establish it from the store, ask the user.

## Proxmox Hosts (PVE hypervisors / PBS)

Hypervisors and backup servers are infra territory — how to work with them
(restrictions, read-only API wrapper) is documented in the smtw_erp_devops
repo's `.claude/CLAUDE.md`. All rules in this skill apply in full when
contacting them.

## Host Keys

If a connection fails because the host key is unknown or changed, run `scan <alias>`, show the output to the user, and stop. **Verifying the fingerprint and appending it to `~/.claude/prod-vm/known_hosts` is the user's act — never edit that file yourself.**

## Machine Identity Verification
- After every successful connection to a production VM, immediately perform identity verification using only existing system state.
- Never proceed with other commands until verification is complete and acceptable.
- Acceptable: The combination of hostname + /etc/machine-id + running containers/services clearly matches the expected machine for that session.

## Announcement

**Make it clear that you are connecting to a production VM, announce the machine name and intent.**

## Command Authorization
- **Rules**:
  - **Every command must be printed before execution**, along with the reason it is being run.
  - **Stick to Authorized Actions only** - Do only the actions that are authorized by the user. Do not try to execute commands that are not explicitly authorized.
  - If a command’s impact is unclear, treat it as Tier 4
- **Tiers**:
All commands must be classified into one of the categories below **before** execution. The agent must state the category and reasoning.
  - **Tier 1 - Diagnostic / read-only commands**: viewing logs, checking processes, disk usage, service status, diagnostic etc. are permitted without explicit authorization. `sudo` only works for the whitelisted read-only docker commands.
  - **Tier 2 - Config Change**: Any command that alters machine configuration or files. User-executed (see Read-Only Policy below).
  - **Tier 3 - Service Control**: Restarting/stopping services, containers, VMs. User-executed (see Read-Only Policy below).
  - **Tier 4 - Destructive / High-risk commands**: (e.g., `rm`, `mv` on important paths, database drops/migrations, mass file operations, `fdisk`, `mkfs`). User-executed; spell out impact and recovery path before handing these over.

## Read-Only Policy — Changes Are the User's Act

Claude Code sessions are **read-only on production**. Claude Code executes Tier 1 only; Tier 2-4 commands are executed by the user, never by Claude Code.

When a change is needed (config edit, service restart, deploy, cleanup):

1. **Stop.** Do not attempt the change, do not look for another credential, session, or workaround. The restriction is intentional.
2. **Prepare the exact commands** for the user to run on the prod machine: ready to paste, in order, one purpose per command, each with a one-line reason and the expected outcome.
3. **State the risk** for anything destructive or hard to reverse, and provide the read-only verification command(s) to run afterwards.
4. **Wait.** The user executes on prod and reports back; continue diagnosis over the read-only channel.

## CRITICAL 
- **Never run commands that could potentially cause credentials to be exfiliated to including the cloud.**

## Secrets in Command Output

**Read-only does not mean safe to print.** A Tier 1 command changes nothing on
the VM, but everything it prints enters the conversation and leaves the dev
machine. A password read by an "innocent" diagnostic command is exfiltrated
just as surely as one that was copied out deliberately. Classify the *output*,
not only the command.

Before running any command, ask: **could this output contain a credential?**
If yes, narrow the command first — this is part of the print-before-execute
rule, not an afterthought.

Known traps, all reachable with the whitelisted read-only verbs:

| Command | What leaks |
|---|---|
| `docker inspect` | `.Config.Env` — DB root passwords, API tokens, licence keys. Also `.Config.Cmd` / `.Args` (secrets passed as flags) and `.Config.Labels` on some images |
| `docker logs`, `docker compose logs` | apps that print connection strings, tokens or full config at startup; stack traces echoing arguments |
| `journalctl` on a unit | `ExecStart=` lines carrying passwords; the same application startup banners |
| `systemctl show`, `systemctl cat` | `Environment=` / `EnvironmentFile=` contents in unit and drop-in files |
| `ccloki` queries | any of the above, already shipped into the log store |

Rules:

- **Never dump a whole `docker inspect`.** Always `--format` down to the exact
  fields needed, and never include `.Config.Env`, `.Config.Cmd` or `.Args`.
  For an image version use the label, not the environment:
  `sudo docker inspect <c> --format '{{index .Config.Labels "org.opencontainers.image.version"}}'`
- To confirm a variable is *set* without revealing it, print key names only —
  never `key=value` pairs.
- Prefer the narrowest source: an image label over a container env, a single
  unit's status over a full journal dump, a filtered LogQL selector over a
  broad one.
- Redaction after the fact is not a fix. Once a secret is in the transcript it
  is out; the only remedy is rotation.

**If a secret does reach the conversation anyway:** stop, tell the user
immediately and plainly — name which credential, which command produced it,
and that it now needs rotating. Do not bury it in a summary, and do not carry
on as though the command had succeeded cleanly.

## Logging

The wrappers automatically append every command or request, reason (`-m`), and outcome to `~/.claude/logs/prod-vm/<alias>.cc.log` on the dev machine (never on the prod VM). Both `ccssh.py` and `ccloki.py` write to the same per-machine file, so SSH and log-query access to one host read as a single timeline. Credentials never appear there. Additionally summarize notable output/findings in the conversation.

## Data / File Downloads

Any files or data downloaded from the session must be listed at the end of the session for proper handling and securing.

## Sub-commands

If the user specifies `clean-logs`, delete all log files under `~/.claude/logs/prod-vm/`.

If the user specifies `help`, display the available sub-commands and a summary of the rules above.
