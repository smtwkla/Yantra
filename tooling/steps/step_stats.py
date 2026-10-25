"""`/step stats`: how the step workflow performs, from data that already exists — the step
files (review rounds, findings by severity, rejected answers) and Claude Code's stored
transcripts (every subagent run: role, model, step, time, tokens, tool calls, e2e runs).

    python tooling/steps/step_stats.py           every step; writes scratch/step-stats.md
    python tooling/steps/step_stats.py S021      one step's runs in detail as well

Sources:
  - docs/steps/S0NN-*/ : 2-brief-review-rN / -sN and 4-code-review-rN files; a finding is a
    heading "### BR1-02 …" (or CR / BS) of its own round, its severity the first of blocker /
    major / minor / nit in the heading; the brief's Review log for Rejected answers.
  - ~/.claude/projects/<this repo>*/<session>/subagents/agent-*.jsonl and .meta.json: one
    file per subagent run.  The step comes from its description ("S021 code review r1"), the
    role from its agent type.  Tokens are summed once per API message (a message is logged
    once per content block, with the same usage), split into new input, cache writes, cache
    reads and output.
  - the sessions' own transcripts (<session>.jsonl): the orchestrator's tokens per day; they
    cannot be split per step, so they are reported per day only.

E2E time is an estimate from what the runs printed: the repo's total line (setting "Browser-test
total line"), or Playwright's "N passed (1.2m)" for a run of 40 tests or more.  A run that
printed neither counts as a run of unknown time.

E2E runs are counted by level, from the repo's five "Browser-test ..." settings (.claude/CLAUDE.md
§ Step workflow; see E2eConfig).  The header shows each level's first letter, e.g. b/n/t/f =
basic / normal / targeted / full.  A run that names a spec file is targeted, at any level;
otherwise it has the level of its --level flag, or the default level (which can depend on when
the run started).  Without the wrapper setting, no browser runs are counted and the report has
no E2E columns."""

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from step_facts import ROOT, STEPS_DIR, backticked, gather, header_value, load_step_settings, stop

PROJECTS = Path.home() / ".claude" / "projects"
REPORT = ROOT / "scratch" / "step-stats.md"
SEVERITIES = ("blocker", "major", "minor", "nit")
REVIEW_NAME = re.compile(r"^(2-brief-review|4-code-review)-([rs])(\d+)\.md$")
# A finding: a heading "### BR1-02 …", or (since 22-10-2026) a nit bullet "- **BR1-07** (nit) …"
FINDING = re.compile(r"^(?:#{2,4}\s+|-\s+\*\*)((BR|CR|BS)(\d+)-\d+)\b\**(.*)$", re.MULTILINE)
SEVERITY_WORD = re.compile(r"\b(blocker|major|minor|nit)s?\b", re.IGNORECASE)
REJECTED = re.compile(r"\*\*Rejected\*\*|\|\s*Rejected\b")
STEP_IN_TEXT = re.compile(r"\bS0\d\d\b")
PLAYWRIGHT_DONE = re.compile(r"\b(\d+) passed \((\d+(?:\.\d+)?)(m|s)\)")
# A command that starts the e2e wrapper, not one that reads it (cat, grep, sed …): a segment of
# the command (split at && ; | ( ) and new lines) that starts with the wrapper, after an optional
# timeout N, cmd //c, call or quote
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|()\n]")
SEGMENT_LEAD = re.compile(r'^(?:timeout\s+\d+\s+|cmd(?:\.exe)?\s+//?c\s+|call\s+|&\s*|["\'])*', re.IGNORECASE)
E2E_MIN_TESTS = 40                         # a smaller "N passed (…)" is a unit-test run
TARGETED = "targeted"                      # the reserved level name: a run naming a spec file


@dataclass(frozen=True)
class E2eConfig:
    """The repo's five Browser-test settings, read once (e2e_config)."""
    wrapper: re.Pattern                    # a command that starts the wrapper
    levels: tuple                          # the names counted, in the order of the columns
    default_level: str                     # a run with no flag and no spec file
    spec_file: re.Pattern = None           # a run naming such a file is targeted
    history: tuple = ()                    # ((level, time), …): a default run before time has level
    total_line: re.Pattern = None          # one group: the run's seconds

    @property
    def flag(self):
        names = "|".join(re.escape(level) for level in self.levels if level != TARGETED)
        return re.compile(rf"--level=({names})\b")

    @property
    def letters(self):
        return "/".join(level[0] for level in self.levels)


# ---------------------------------------------------------------------------------------------
# Pure parsing (unit-tested)
# ---------------------------------------------------------------------------------------------

def review_findings(name, text):
    """A review file's name and text -> {severity: count} of the findings it raises in its own
    round (a later round's "CR1-01 verified fixed" heading is not counted again)."""
    match = REVIEW_NAME.match(name)
    if not match:
        return {}
    round_number = int(match.group(3))
    counts = defaultdict(int)
    for _id, _prefix, finding_round, rest in FINDING.findall(text):
        if int(finding_round) != round_number:
            continue
        severity = SEVERITY_WORD.search(rest)
        counts[severity.group(1).lower() if severity else "unrated"] += 1
    return dict(counts)


def round_kind(name):
    """'2-brief-review-r2.md' -> 'BR', '-s1' -> 'BS', '4-code-review-r3.md' -> 'CR'; else None."""
    match = REVIEW_NAME.match(name)
    if not match:
        return None
    return "CR" if match.group(1) == "4-code-review" else ("BS" if match.group(2) == "s" else "BR")


def rejected_answers(brief_text):
    log = brief_text.split("## Review log", 1)[1] if "## Review log" in brief_text else ""
    return len(REJECTED.findall(log))


def step_of(description):
    found = STEP_IN_TEXT.search(description or "")
    return found.group(0) if found else None


def message_usage(lines):
    """Transcript lines (JSON) -> {message id: (model, usage)}: the last usage logged for each
    API message, counted once."""
    found = {}
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") or {}
        usage, mid = message.get("usage"), message.get("id")
        if usage and mid:
            found[mid] = (message.get("model"), usage)
    return found


def token_totals(usages):
    total = defaultdict(int)
    for _model, usage in usages.values():
        total["new_input"] += usage.get("input_tokens", 0)
        total["cache_write"] += usage.get("cache_creation_input_tokens", 0)
        total["cache_read"] += usage.get("cache_read_input_tokens", 0)
        total["output"] += usage.get("output_tokens", 0)
    return dict(total)


def e2e_seconds(texts, total_line=None):
    """The tool outputs of one run -> [seconds] of the e2e runs they report (each distinct
    report once: an output read twice is one run).  ``total_line`` is the repo's regular
    expression with one group, the seconds; Playwright's own line counts with or without it."""
    seen, runs = set(), []
    for text in texts:
        if total_line:
            for match in total_line.finditer(text):
                key = ("total", match.group(0))
                if key not in seen:
                    seen.add(key)
                    runs.append(int(match.group(1)))
            if total_line.search(text):
                continue
        for count, amount, unit in PLAYWRIGHT_DONE.findall(text):
            if int(count) < E2E_MIN_TESTS:
                continue
            key = ("pw", count, amount, unit)
            if key not in seen:
                seen.add(key)
                runs.append(round(float(amount) * (60 if unit == "m" else 1)))
    return runs


def default_level(config, started):
    """The level of a run with no flag and no spec file that started at ``started``: the first
    history entry whose time is after it (an unknown start counts as the earliest), else the
    default level."""
    for level, before in config.history:
        if started is None or started < before:
            return level
    return config.default_level


def e2e_invocations(commands, config, started=None):
    """Bash commands of a run that started at ``started`` -> {level: runs} of the wrapper, for
    every level of ``config``.  A spec file makes a run targeted; otherwise the --level flag
    names the level, or the default level of ``started`` does."""
    counts = {level: 0 for level in config.levels}
    unflagged = default_level(config, started)
    for command in commands:
        for segment in SEGMENT_SPLIT.split(command):
            segment = SEGMENT_LEAD.sub("", segment.strip())
            if not config.wrapper.match(segment):
                continue
            level = config.flag.search(segment)
            if config.spec_file and TARGETED in counts and config.spec_file.search(segment):
                counts[TARGETED] += 1
            else:
                counts[level.group(1) if level else unflagged] += 1
    return counts


def e2e_runs_text(runs, config):
    """The "b/n/t/f" cell of E2E runs, summed over ``runs``."""
    return "/".join(str(sum(run.e2e.get(level, 0) for run in runs)) for level in config.levels)


def e2e_config(settings):
    """The Step workflow settings -> an E2eConfig, or None when the repo counts no browser runs
    (a missing or ``none`` wrapper or levels entry).  Stops (exit 2) on levels that share a first
    letter, a default or history level that is not a level, a time that is not a date, or a
    total line that is not a regular expression with one group."""
    wrapper = backticked(settings.get("Browser-test wrapper"))
    levels = tuple(backticked(settings.get("Browser-test levels")))
    if not wrapper or not levels:
        return None
    by_letter = defaultdict(list)
    for level in levels:
        by_letter[level[0]].append(level)
    for clash in by_letter.values():
        if len(clash) > 1:
            stop(f"The browser-test levels {' and '.join(clash)} start with the same letter. "
                 "The report's header needs a different first letter for each level.")
    spec_words = backticked(settings.get("Browser-test spec files"))
    total = backticked(settings.get("Browser-test total line"))
    words = backticked(settings.get("Browser-test default level"))
    plain = [level for level in levels if level != TARGETED]
    for level in words[:1] + words[1::2]:
        if level not in levels:
            stop(f"The browser-test default level names {level}, which is not one of the "
                 f"browser-test levels ({', '.join(levels)}).")
    if words and len(words) % 2 == 0:
        stop(f"The browser-test default level ends with {words[-1]}, which has no date and time "
             "after it. Give each later level a time such as 2026-10-25T05:50Z.")
    history = []
    for level, when in zip(words[1::2], words[2::2]):
        try:
            time = _time(when)
        except ValueError:
            stop(f"The browser-test default level has {when}, which is not a date and time "
                 "such as 2026-10-25T05:50Z.")
        history.append((level, time if time.tzinfo else time.replace(tzinfo=timezone.utc)))
    total_line = None
    if total:
        try:
            total_line = re.compile(total[0])
        except re.error:
            stop(f"The browser-test total line {total[0]} is not a valid regular expression.")
        if total_line.groups != 1:
            stop(f"The browser-test total line {total[0]} needs exactly one group, "
                 "the number of seconds.")
    return E2eConfig(
        wrapper=re.compile(r"^[\w./\\:-]*" + re.escape(wrapper[0]) + r"\b", re.IGNORECASE), levels=levels,
        default_level=words[0] if words else (plain[0] if plain else levels[0]),
        spec_file=re.compile(re.escape(spec_words[0]) + r"\b") if spec_words else None,
        history=tuple(history), total_line=total_line)


# ---------------------------------------------------------------------------------------------
# Reading the transcripts
# ---------------------------------------------------------------------------------------------

@dataclass
class Run:
    step: str
    role: str
    description: str
    model: str = ""
    started: datetime = None
    ended: datetime = None
    tokens: dict = field(default_factory=dict)
    tool_calls: int = 0
    e2e: dict = field(default_factory=dict)     # {level: starts of the browser-test wrapper}
    e2e_seconds: list = field(default_factory=list)

    @property
    def minutes(self):
        return (self.ended - self.started).total_seconds() / 60 if self.started and self.ended else 0


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _tool_texts(content):
    for block in content if isinstance(content, list) else []:
        if block.get("type") == "tool_result":
            inner = block.get("content")
            if isinstance(inner, str):
                yield inner
            elif isinstance(inner, list):
                yield from (b.get("text", "") for b in inner if isinstance(b, dict))


def read_run(meta_path, config=None):
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    transcript = meta_path.with_name(meta_path.name.replace(".meta.json", ".jsonl"))
    if not transcript.exists():
        return None
    run = Run(step_of(meta.get("description")), meta.get("agentType", "?"), meta.get("description", ""))
    lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    usages = message_usage(lines)
    run.tokens = token_totals(usages)
    models = [m for m, _u in usages.values() if m]
    run.model = max(set(models), key=models.count) if models else ""
    commands, texts, times, seen_calls = [], [], [], set()
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("timestamp"):
            times.append(_time(entry["timestamp"]))
        content = (entry.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            # A tool call is logged more than once (the call, then as rewritten by a hook): once by id
            if block.get("type") == "tool_use" and block.get("id") not in seen_calls:
                seen_calls.add(block.get("id"))
                run.tool_calls += 1
                if block.get("name") in ("Bash", "PowerShell"):
                    commands.append(str((block.get("input") or {}).get("command", "")))
        texts.extend(_tool_texts(content))
    if times:
        run.started, run.ended = min(times), max(times)
    if config:
        run.e2e = e2e_invocations(commands, config, run.started)
        run.e2e_seconds = e2e_seconds(texts, config.total_line)
    return run


def project_dirs():
    prefix = re.sub(r"[:\\/]", "-", str(ROOT))
    return [p for p in PROJECTS.glob(prefix + "*") if p.is_dir()]


def read_runs(config=None):
    runs = []
    for project in project_dirs():
        for meta in project.glob("*/subagents/agent-*.meta.json"):
            run = read_run(meta, config)
            if run:
                runs.append(run)
    return runs


def orchestrator_by_day():
    """The sessions' own (main-thread) tokens per day."""
    days = defaultdict(lambda: defaultdict(int))
    for project in project_dirs():
        for session in project.glob("*.jsonl"):
            usages, day_of = {}, {}
            for line in session.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("isSidechain"):
                    continue
                message = entry.get("message") or {}
                if message.get("usage") and message.get("id"):
                    usages[message["id"]] = (message.get("model"), message["usage"])
                    day_of[message["id"]] = (entry.get("timestamp") or "")[:10]
            for mid, pair in usages.items():
                for key, value in token_totals({mid: pair}).items():
                    days[day_of[mid]][key] += value
    return days


# ---------------------------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------------------------

def mtok(n):
    return f"{n / 1_000_000:.1f}" if n >= 100_000 else f"{n / 1_000_000:.2f}"


def fresh(tokens):
    """New input + cache writes + output: the tokens that cost most (cache reads are cheap)."""
    return tokens.get("new_input", 0) + tokens.get("cache_write", 0) + tokens.get("output", 0)


def counts_text(counts):
    return " / ".join(str(counts.get(s, 0)) for s in SEVERITIES) if counts else "—"


def build_report(only_step=None, config=None):
    """The report; ``config`` is the repo's E2eConfig, or None for no E2E columns."""
    facts = gather()
    runs = read_runs(config)
    by_step = defaultdict(list)
    for run in runs:
        by_step[run.step].append(run)
    e2e_note = ""
    if config:
        names = " / ".join(f"{level} (spec files named)" if level == TARGETED else level for level in config.levels)
        e2e_note = (" E2E minutes count only the runs whose total was printed into the transcript (a lower bound: "
                    "a background run read with grep shows none); E2E runs counts every start of the wrapper, "
                    f"by level: {config.letters} = {names}.")
    out = ["# Step workflow statistics", "",
           f"Built {datetime.now():%d-%m-%Y %H:%M} by `tooling/step-stats.bat` from the step files and "
           f"{len(runs)} stored subagent runs. Findings are blocker / major / minor / nit. Tokens in "
           "millions: *fresh* = new input + cache writes + output (the costly part), *read* = cache "
           f"reads.{e2e_note}", ""]

    out += ["## Per step", "",
            "| Step | Track | BR | BS | CR | Brief findings | Code findings | Rejected | Runs | Agent h | "
            "Fresh Mtok | Read Mtok |" + (f" E2E runs ({config.letters}) | E2E min |" if config else ""),
            "|---|---|---|---|---|---|---|---|---|---|---|---|" + ("---|---|" if config else "")]
    totals = defaultdict(lambda: defaultdict(int))
    late = []
    for step in facts.steps:
        if only_step and step.id != only_step:
            continue
        kinds, brief_counts, code_counts = defaultdict(int), defaultdict(int), defaultdict(int)
        for name in step.names:
            kind = round_kind(name)
            if not kind:
                continue
            kinds[kind] += 1
            found = review_findings(name, step.text(name))
            target = code_counts if kind == "CR" else brief_counts
            for severity, n in found.items():
                target[severity] += n
            number = int(REVIEW_NAME.match(name).group(3))
            serious = found.get("blocker", 0) + found.get("major", 0)
            if serious and (kind == "BS" or number > 1):
                late.append((step.id, name, serious))
        brief_text = step.text("1-brief.md") if step.has_brief else ""
        step_runs = by_step.get(step.id, [])
        tokens = defaultdict(int)
        for run in step_runs:
            for k, v in run.tokens.items():
                tokens[k] += v
        hours = sum(r.minutes for r in step_runs) / 60
        e2e_min = sum(sum(r.e2e_seconds) for r in step_runs) / 60
        track = header_value(step.header, "Track") or "full"
        e2e_cells = f" {e2e_runs_text(step_runs, config)} | {e2e_min:.0f} |" if config else ""
        out.append(f"| {step.id} | {track} | {kinds['BR']} | {kinds['BS']} | {kinds['CR']} | "
                   f"{counts_text(brief_counts)} | {counts_text(code_counts)} | {rejected_answers(brief_text)} | "
                   f"{len(step_runs)} | {hours:.1f} | {mtok(fresh(tokens))} | {mtok(tokens['cache_read'])} |"
                   f"{e2e_cells}")

    out += ["", "## Per role and model", "",
            "| Role | Model | Runs | Mean min | Mean fresh Mtok | Mean read Mtok | Mean tool calls |"
            + (" E2E min (share of its time) |" if config else ""),
            "|---|---|---|---|---|---|---|" + ("---|" if config else "")]
    groups = defaultdict(list)
    for run in runs:
        if only_step and run.step != only_step:
            continue
        groups[(run.role, run.model)].append(run)
    for (role, model), group in sorted(groups.items(), key=lambda kv: -sum(fresh(r.tokens) for r in kv[1])):
        n = len(group)
        minutes = sum(r.minutes for r in group)
        e2e = sum(sum(r.e2e_seconds) for r in group) / 60
        share = f"{100 * e2e / minutes:.0f} %" if minutes else "—"
        e2e_cell = f" {e2e:.0f} ({share}) |" if config else ""
        out.append(f"| {role} | {model or '?'} | {n} | {minutes / n:.0f} | {mtok(sum(fresh(r.tokens) for r in group) / n)} | "
                   f"{mtok(sum(r.tokens.get('cache_read', 0) for r in group) / n)} | "
                   f"{sum(r.tool_calls for r in group) / n:.0f} |{e2e_cell}")

    out += ["", "## Late blockers and majors", "",
            "Found in a staleness round or a review round after the first: what the earlier round missed.", ""]
    out += [f"- {step}: `{name}` — {n}" for step, name, n in late] or ["- none"]

    no_step = [r for r in runs if not r.step]
    out += ["", "## Runs without a step", "",
            f"{len(no_step)} runs name no step in their description (tooling, questions, research): "
            f"{sum(r.minutes for r in no_step) / 60:.1f} h, {mtok(sum(fresh(r.tokens) for r in no_step))} fresh Mtok."]

    if not only_step:
        out += ["", "## The orchestrator (main sessions), per day", "",
                "| Day | Fresh Mtok | Read Mtok |", "|---|---|---|"]
        for day, tok in sorted(orchestrator_by_day().items()):
            if day:
                out.append(f"| {day} | {mtok(fresh(tok))} | {mtok(tok['cache_read'])} |")
    else:
        out += ["", f"## {only_step}: every run", "",
                "| Started | Role | Model | Description | Min | Fresh Mtok | Tool calls |"
                + (f" E2E ({config.letters}, min) |" if config else ""),
                "|---|---|---|---|---|---|---|" + ("---|" if config else "")]
        for run in sorted(by_step.get(only_step, []), key=lambda r: r.started or datetime.min):
            e2e_cell = f" {e2e_runs_text([run], config)}, {sum(run.e2e_seconds) / 60:.0f} |" if config else ""
            out.append(f"| {run.started:%d-%m %H:%M} | {run.role} | {run.model} | {run.description} | {run.minutes:.0f} | "
                       f"{mtok(fresh(run.tokens))} | {run.tool_calls} |{e2e_cell}")
    return "\n".join(out) + "\n"


def main(argv):
    only = next((a for a in argv if STEP_IN_TEXT.fullmatch(a)), None)
    report = build_report(only, e2e_config(load_step_settings()))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    print(f"(written to {REPORT})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
