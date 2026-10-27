"""Step claims: one orchestrator session at a time works on a step (decided 27-10-2026, KLA).

    python tooling/steps/step_claim.py take S062 "coding"         take, or refuse if another session holds it
    python tooling/steps/step_claim.py take S062 "coding" --force take over a live claim (only on the user's word)
    python tooling/steps/step_claim.py agent S062 coder 60        an agent started: role, budget in minutes
    python tooling/steps/step_claim.py agent-done S062            the agent handed back
    python tooling/steps/step_claim.py touch S062                 the orchestrator is still at work on it
    python tooling/steps/step_claim.py release S062               at a gate, or when the user stops the step
    python tooling/steps/step_claim.py watch S062                 wait; exit 3 when the agent passes its budget
    python tooling/steps/step_claim.py show [S062]                every claim (or one), live or dead

Why a claim file and not an OS lock: an OS lock is held by one process and dies with it, while a
step's phase spans many commands and a 25-minute agent run. The claim is a small JSON file in the
main working folder's scratch/step-claims/ (shared by its git worktrees, as the e2e lock is),
written under a short file lock so two sessions cannot both take it.

Who owns it: the Claude Code process that runs the orchestrator, by CLAUDE_PID (and the machine),
which every shell the session starts inherits. A /clear keeps the process, so a cleared session
keeps its own claims and may take them again.

When a claim is dead (another session may then take it without --force):
  - the owner's process is no longer running (checked by its PID and its name), or
  - nothing touched it for IDLE_LIMIT while no agent runs, or
  - an agent runs and its budget plus AGENT_GRACE has passed.
A claim stays live while the orchestrator waits at a gate only if it keeps it: the skill releases
claims at gate A and gate B.

The watchdog (`watch`) is a command the orchestrator starts in the background when it starts an
agent. It returns when the agent is done or the claim is gone (exit 0), or when the agent passes its
budget (exit 3, with a message). Its exit wakes the orchestrator, which checks the agent and tells
the user. It never stops an agent.

stdlib only; the pure core (the claim rules) is unit-tested in tooling/common/tests/test_step_claim.py."""

import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import preflight_stamp  # noqa: E402  (the shared file lock, main_scratch and IST text)

STEP_ID = re.compile(r"^S\d{3}$")
CLAIMS_DIR = "step-claims"
LOCK_NAME = "step-claims.lock"
LOCK_TRIES = 50                       # the lock is held for milliseconds; 50 tries of 0.1 s is plenty
IDLE_LIMIT = timedelta(minutes=30)    # no agent running and no command for this long: dead
AGENT_GRACE = timedelta(minutes=15)   # an agent past its budget by this much: its claim is dead
WATCH_POLL_SECONDS = 30
# Budgets in minutes, about twice each role's usual time (/step stats, 27-10-2026: an Opus coder
# 23-24 min, a review 2-7 min, a fix round 5 min). A fix round passes its own budget (20).
BUDGETS = {"coder": 60, "fix": 20, "code-reviewer": 20, "brief-reviewer": 20, "advisor": 30,
           "roadmapper": 45}

EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_OVER_BUDGET = 3


class ClaimError(Exception):
    """A refusal with a message for the orchestrator."""


# ---------------------------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------------------------

def parse_time(text):
    return datetime.fromisoformat(text) if text else None


def same_owner(claim, me):
    """Whether `me` (an owner dict) holds `claim`: the same process on the same machine; without a
    PID on either side, the same session id."""
    owner = claim.get("owner", {})
    if owner.get("machine") != me.get("machine"):
        return False
    if owner.get("pid") and me.get("pid"):
        return owner["pid"] == me["pid"]
    return bool(owner.get("session")) and owner.get("session") == me.get("session")


def liveness(claim, now, owner_running):
    """(live, reason). `owner_running` is True, False, or None when it cannot be told (another
    machine, no PID): then only the times decide."""
    if owner_running is False:
        return False, "its session has ended (the process is gone)"
    agent = claim.get("agent")
    if agent:
        deadline = parse_time(agent["started"]) + timedelta(minutes=agent["budget"]) + AGENT_GRACE
        if now > deadline:
            return False, f"its {agent['role']} passed its budget of {agent['budget']} min long ago"
        return True, ""
    if now - parse_time(claim["touched"]) > IDLE_LIMIT:
        return False, f"no command for more than {int(IDLE_LIMIT.total_seconds() // 60)} min"
    return True, ""


def describe(claim, now, live, reason):
    """One line about a claim, for a refusal and for `show`."""
    owner = claim.get("owner", {})
    who = f"session {owner.get('session') or '?'} (process {owner.get('pid') or '?'} on {owner.get('machine')})"
    line = (f"{claim['step']}: {claim['phase']} — {who}, since {preflight_stamp.ist_text(parse_time(claim['taken']))}"
            f", last command {minutes(now - parse_time(claim['touched']))} ago")
    agent = claim.get("agent")
    if agent:
        line += (f"; {agent['role']} running {minutes(now - parse_time(agent['started']))}"
                 f" (budget {agent['budget']} min)")
    return line + ("" if live else f" — DEAD: {reason}")


def minutes(delta):
    return f"{max(0, int(delta.total_seconds() // 60))} min"


def decide_take(existing, me, now, owner_running, force):
    """None when `me` may take the step, else the refusal message."""
    if existing is None or same_owner(existing, me) or force:
        return None
    live, reason = liveness(existing, now, owner_running)
    if not live:
        return None
    return ("refused: another session is working on this step.\n  " + describe(existing, now, live, reason)
            + "\n  Wait for it, or take it over with --force only if the user says so.")


def new_claim(step_id, phase, me, now, existing=None):
    """The claim `me` writes on take. The same owner taking again keeps the start time and any
    agent; a take-over starts fresh and records whom it took the step from."""
    claim = {"step": step_id, "phase": phase, "owner": me, "taken": now.isoformat(),
             "touched": now.isoformat(), "agent": None}
    if existing and same_owner(existing, me):
        claim["taken"], claim["agent"] = existing["taken"], existing.get("agent")
    elif existing:
        claim["taken_over_from"] = existing.get("owner")
    return claim


def start_agent(claim, role, budget, now):
    if budget is None:
        if role not in BUDGETS:
            raise ClaimError(f"no budget for role {role!r}; give one in minutes")
        budget = BUDGETS[role]
    if budget < 1:
        raise ClaimError("a budget is a whole number of minutes, 1 or more")
    return {**claim, "touched": now.isoformat(),
            "agent": {"role": role, "budget": budget, "started": now.isoformat()}}


def watch_state(claim, me, now):
    """What `watch` does on one poll: ("done", msg), ("over", msg) or ("wait", seconds to sleep)."""
    if claim is None or not same_owner(claim, me):
        return "done", "the claim was released or taken over"
    agent = claim.get("agent")
    if not agent:
        return "done", "the agent handed back"
    over_at = parse_time(agent["started"]) + timedelta(minutes=agent["budget"])
    if now >= over_at:
        return "over", (f"{claim['step']}: the {agent['role']} has run {minutes(now - parse_time(agent['started']))}"
                        f", past its budget of {agent['budget']} min. Check on it and tell the user; "
                        "do not stop it without the user's word.")
    return "wait", min(WATCH_POLL_SECONDS, max(1, (over_at - now).total_seconds()))


# ---------------------------------------------------------------------------------------------
# Shell: the environment, the process table and the claim files
# ---------------------------------------------------------------------------------------------

def me_from_env(environ=os.environ):
    pid = environ.get("CLAUDE_PID", "")
    return {"pid": int(pid) if pid.isdigit() else None,
            "session": environ.get("CLAUDE_CODE_SESSION_ID") or None,
            "machine": platform.node()}


def process_name(pid):
    """The image name of a running process, or "" when no process has this PID."""
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True).stdout.strip()
        return out.split('","')[0].strip('"') if out.startswith('"') else ""
    out = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True).stdout
    return out.strip()


def owner_running(claim, me):
    """True / False for a claim made on this machine with a PID; None when it cannot be told.
    The name check guards against the PID being reused by another program."""
    owner = claim.get("owner", {})
    if owner.get("machine") != me.get("machine") or not owner.get("pid"):
        return None
    return "claude" in process_name(owner["pid"]).lower()


def claims_dir():
    return preflight_stamp.main_scratch() / CLAIMS_DIR


def read_claim(step_id):
    path = claims_dir() / f"{step_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_claim(claim):
    path = claims_dir() / f"{claim['step']}.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(claim, indent=2), encoding="utf-8")
    os.replace(temp, path)  # a reader never sees half a file


def remove_claim(step_id):
    (claims_dir() / f"{step_id}.json").unlink(missing_ok=True)


def all_claims():
    folder = claims_dir()
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("S*.json"))] if folder.is_dir() else []


class locked:
    """The claims folder's file lock, for one read-change-write."""

    def __enter__(self):
        claims_dir().mkdir(parents=True, exist_ok=True)
        for _ in range(LOCK_TRIES):
            self._held = preflight_stamp.held_lock(claims_dir() / LOCK_NAME)
            if self._held.__enter__():
                return self
            self._held.__exit__(None, None, None)
            time.sleep(0.1)
        raise ClaimError("the claims lock stays busy; try again")

    def __exit__(self, *exc):
        return self._held.__exit__(*exc)


def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------

def owned_claim(step_id, me):
    claim = read_claim(step_id)
    if claim is None:
        raise ClaimError(f"{step_id} has no claim; take it first")
    if not same_owner(claim, me):
        raise ClaimError(f"{step_id} is held by another session; take it first")
    return claim


def cmd_take(step_id, phase, me, force):
    with locked():
        existing, now = read_claim(step_id), now_utc()
        refusal = decide_take(existing, me, now, existing and owner_running(existing, me), force)
        if refusal:
            raise ClaimError(refusal)
        claim = new_claim(step_id, phase, me, now, existing)
        write_claim(claim)
    note = ""
    if existing and not same_owner(existing, me):
        live, reason = liveness(existing, now, owner_running(existing, me))
        note = f"\n  taken over from: {describe(existing, now, live, reason)}"
    return f"claimed {step_id}: {phase}{note}"


def cmd_agent(step_id, role, budget, me):
    with locked():
        claim = start_agent(owned_claim(step_id, me), role, budget, now_utc())
        write_claim(claim)
    return f"{step_id}: {role} started, budget {claim['agent']['budget']} min"


def cmd_agent_done(step_id, me):
    with locked():
        claim = {**owned_claim(step_id, me), "agent": None, "touched": now_utc().isoformat()}
        write_claim(claim)
    return f"{step_id}: agent done"


def cmd_touch(step_id, me):
    with locked():
        write_claim({**owned_claim(step_id, me), "touched": now_utc().isoformat()})
    return f"{step_id}: touched"


def cmd_release(step_id, me, force):
    with locked():
        claim = read_claim(step_id)
        if claim is None:
            return f"{step_id}: no claim"
        if not same_owner(claim, me) and not force:
            raise ClaimError(f"{step_id} is held by another session; release it with --force only if the user says so")
        remove_claim(step_id)
    return f"released {step_id}"


def cmd_watch(step_id, me):
    while True:
        state, value = watch_state(read_claim(step_id), me, now_utc())
        if state != "wait":
            return state, value
        time.sleep(value)


def cmd_show(step_id, me):
    claims = [c for c in all_claims() if step_id in (None, c["step"])]
    if not claims:
        return "no claims" if step_id is None else f"{step_id}: no claim"
    now = now_utc()
    lines = []
    for claim in claims:
        live, reason = liveness(claim, now, owner_running(claim, me))
        mine = " (this session)" if same_owner(claim, me) else ""
        lines.append(describe(claim, now, live, reason) + mine)
    return "\n".join(lines)


def main(argv, me=None):
    me = me or me_from_env()
    force = "--force" in argv
    args = [a for a in argv if a != "--force"]
    try:
        if len(args) >= 2 and not STEP_ID.match(args[1]):
            raise ClaimError(f"step id must look like S062, got {args[1]!r}")
        if args[:1] == ["take"] and len(args) == 3:
            print(cmd_take(args[1], args[2], me, force))
        elif args[:1] == ["agent"] and len(args) in (3, 4):
            budget = int(args[3]) if len(args) == 4 and args[3].isdigit() else None
            if len(args) == 4 and budget is None:
                raise ClaimError("the budget is a whole number of minutes")
            print(cmd_agent(args[1], args[2], budget, me))
        elif args[:1] == ["agent-done"] and len(args) == 2:
            print(cmd_agent_done(args[1], me))
        elif args[:1] == ["touch"] and len(args) == 2:
            print(cmd_touch(args[1], me))
        elif args[:1] == ["release"] and len(args) == 2:
            print(cmd_release(args[1], me, force))
        elif args[:1] == ["watch"] and len(args) == 2:
            state, message = cmd_watch(args[1], me)
            print(message)
            return EXIT_OVER_BUDGET if state == "over" else 0
        elif args[:1] == ["show"] and len(args) in (1, 2):
            print(cmd_show(args[1] if len(args) == 2 else None, me))
        else:
            print(__doc__)
            return EXIT_USAGE
        return 0
    except ClaimError as error:
        print(error if str(error).startswith("refused") else f"refused: {error}")
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
