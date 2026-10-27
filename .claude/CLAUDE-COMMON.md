# CLAUDE-COMMON.md

Shared development rules across all repos, in two kinds:

- **Invariants** — hold in every repo. A repo's `CLAUDE.md` must not override them.
- **Defaults** — starting choices for new projects. A repo's `CLAUDE.md` wins on conflict.

## Invariants

### Principles

- **Simplicity first**: Minimal, straightforward code. No over-engineering.
- **Right-sized for internal apps**: These are internal apps with ~50 users. Prioritize correctness, security, and maintainability over performance tuning or scale; avoid obvious waste (N+1 queries, needless full-table scans) but don't build for load that won't come.
- **Explicit over implicit and clever**: No magic numbers, obscure one-liners, or hidden side effects. If someone has to puzzle over what it does, rewrite it.
- **Explain decisions**: Explain your choices and how things work — in replies and in docs. Code comments say *why*, not *what*; don't add comments that restate the code.
- **Pure core, thin shell**: Business computation (scheduling, projections, simulations, derivations) lives in pure functions — plain data in, plain data out; no DB access, no `datetime.now()`, no framework imports. Route handlers and DB code form a thin shell that fetches inputs, calls the core, and stores results. Write and green the core's unit tests before building the API or UI on top.
- **Backend heavy, frontend light**: Business logic and critical code in the backend. Frontend stays thin and presentational; simple helpers for input validation/formatting are fine.
- **Separation of concerns**: Clear module boundaries. Functionality lives where it belongs.

### Engineering rules

- **DRY**: Extract shared logic into reusable functions; never copy-paste code blocks.
- **Testing**: Write tests for new functionality — happy path plus key failure modes.
- **Known faults are marked strict**: a test that fails because of a fault you accept for now carries a
  strict expected-failure mark that names the step and the fault, so the run turns red when the fault
  is fixed and the mark has to come off. A test that also passes now and then is no known fault: fix
  the test. The mark's syntax for each test tool is the repo's `## Pre-flight` setting *Known fault*
  (`SMTW-WebApp-Base.md` § Pre-flight Before Every Release); this rule does not repeat it.
  (Yantra, S049, 25-10-2026.)
- **Edge cases**: Consider nulls, empty inputs, boundary values, concurrent access. Clarify ambiguous requirements.
- **Error handling**: Handle errors at the right level with meaningful messages. Never silently swallow exceptions.
- **Deprecation**: Never use deprecated APIs/functions/modules. If found in existing code, rewrite to avoid them after consulting me.
- **Dependency health**: Prefer actively maintained libraries. Flag dependencies that are unmaintained (no release in 12+ months, archived repo), end-of-life, or abandoned, and suggest a maintained alternative.
- **Software inventory**: keep a CycloneDX software bill of materials (SBOM) for every lockfile
  (`uv.lock`, `package-lock.json`) in `sbom/`, one file per lockfile named after its folder
  (`backend.cdx.json`). Generate it with the audit script, never edit it by hand, and commit `sbom/`
  with every dependency change. The audit (`tooling/deps/audit.py`, wrapper `tooling/run-deps-audit.bat`)
  looks every library up in OSV and flags direct dependencies with no release in 12 months, as *Dependency
  health* asks. Exit codes: **0** clean, **1** a critical, high or unknown-severity vulnerability, **2** the
  check could not be completed. Run it before a release; keep it out of the normal test run (it needs the
  network). Its report goes to `scratch/dependency-report.md`. (Yantra, S022, 18-10-2026.)
- **Idle connections**: Pooled DB/HTTP connections die after long idle periods (overnight). Detect a dead connection on first use (`OperationalError`/`InterfaceError` or equivalent) and reconnect, rather than returning a 500 after a quiet night.

### Migrations & dev databases

- **Migrations are append-only**: Never edit an applied migration; always add a new version.
- **Dev/test DBs are disposable**: On any schema drift or stale-schema symptom, drop the schema and let migrations rebuild it — don't debug a stale test DB.

### Conventions

- **Timezone**: Servers run UTC; business logic uses IST (Asia/Kolkata, UTC+5:30).
- **Date formats**: Indian format `DD-MM-YYYY` (preferred) or ISO 8601 `YYYY-MM-DD` for entry, display, and storage. Never US `MM/DD/YYYY`.
- **Raw SQL over ORM** with the appropriate driver, unless the framework requires an ORM.
- **Secrets**: Credentials in gitignored `secrets_*.py` files, with `example_secrets_*.py` templates. (Canonical description — repo `CLAUDE.md` links here, doesn't restate.)
- **Mail relay values and personal addresses never go into a repo**: the host, port and credentials of a
  mail relay, and any person's email address, appear nowhere in the repo — no code default, example,
  test value or doc. They come from the deployment's variables (Ansible), through the secrets file.
  Tests and examples use reserved names (`example.test`). A person's address comes from the login
  token, is never typed in, and is shown only to its owner and the administrator. A background-task
  payload carries the person's id, never the address, so the queue and the logs hold no address.
  (Yantra, S032, 24-10-2026.) This covers the mail relay and people's addresses only; other service
  URLs, realm names and deployment paths may be in a repo.
- **Data directories**: App-owned data in a gitignored `data/` folder, organized by tenant/company if multi-tenant. Support env-var overrides for default paths.
- **Git commit messages**: One line, feature-focused — what changed, brief context after a dash or semicolon. No multi-line bodies or bullet lists.
  Example: `Auto-generated project index: Index.md - triggered on project save and daily materialisation run;`

### Writing style (ASD-STE100, light)

Write in the spirit of ASD-STE100 Simplified Technical English, without its full dictionary and verb-form limits. Two scopes:

**A. Reports to me** — briefs, plans, bug reports, issue lists, questions, summaries. Not code, code comments, or quoted tool output.

1. **Lead with the point.** First line: the result, the decision needed, or the main finding. Details after.
2. **One idea per sentence.** Aim for 20 words or fewer. Split long sentences unless a split loses the logic.
3. **Active voice, plain verbs.** "The job fails because X", not "Failure is caused by X". Use "use", "start", "check", "fix" — not "utilize", "initiate", "ascertain", "remediate".
4. **One term for one thing.** Do not alternate synonyms (task / job / run) for the same object. Keep exact names for files, functions, flags, and errors.
5. **Imperative for actions.** One action per step: "Run X.", "Set Y to Z." Number steps that must run in order.
6. **No noun stacks or hedges.** Avoid 3+ nouns in a row ("user session token refresh failure"). Cut "might possibly", "it seems that", "in order to".
7. **Use structure for scanning.** Lists for parallel items, tables for comparisons. Label each item as fact, assumption, or recommendation.
8. **Questions to me:** state the question first, then the options with the consequence of each. Mark the recommended option.

Keep full sentences with articles — no telegraphic text. Keep technical depth: plain wording must not remove detail, reasons, or caveats.

**B. Text inside the apps you build** — UI labels, buttons, headings, tooltips, help text, empty states, validation messages, error messages, toasts, confirmation dialogs, and CLI output for users. Rules 2–6 above apply, plus:

- **Error messages answer three things:** what happened, why (if known), what the user can do next. Example: "The file was not saved. The name already exists. Use a different name." Never show stack traces, SQL, or internal codes to users; log those server-side.
- **Buttons and menu items start with a verb** that names the result: "Save order", "Delete item". Not "OK" or "Submit".
- **Same word for the same thing in the whole app** (and across SMTW apps). Do not switch between "Delete / Remove", "Customer / Client", "Save / Update" for one action.
- **Say what the user sees,** not what the system does: "Enter a date in DD-MM-YYYY format", not "Invalid input".
- **Short, direct, no blame:** "Enter a quantity", not "You forgot to enter a quantity". No jargon the shop-floor or office user would not know. No exclamation marks.
- **Confirmations state the consequence:** "Delete order 123? You cannot undo this."
- Developer-facing text (logs, code comments, exception messages not shown to users) stays technical and exact.

### Shell preference (Windows)

Prefer the Bash tool over PowerShell — PowerShell mangles special characters, wasting turns. Use PowerShell only when the task genuinely requires it (Windows cmdlets, `Invoke-Command`, remote Windows VM management).

### Wrapper scripts

Wrap recurring test/build/query commands in `tooling/*.bat` (or `.sh`) scripts so Claude Code permissions can whitelist them once. Prefer running the wrapper over retyping the raw command.

A test wrapper writes the suite's whole output to `scratch/<suite>-tests.log` (with the run name,
`scratch/<suite>-tests-<run>.log`, when one is set) and prints one last line:
PASSED or FAILED, the counts, the time and the log path (`tooling/common/run_test_suite.py` does this for
any command). Read that line and the log; never run the suite again just to see its summary. A
wrapper that runs several suites sets `TEST_SUMMARY_FILE` to a file, so each suite appends its line and
the wrapper prints all lines again at the end.

### Show the plan before building

**No silent architecture.** Design and architectural decisions are mine to approve, not yours to take in the background. Before writing code for anything beyond a trivial, obvious edit, present a short implementation brief and wait for the go-ahead:

1. **What will be built** — the behaviour/features, in plain terms.
2. **Where** — files created or changed, and any new module/table/endpoint/dependency.
3. **Design decisions** — the choices you are making, why, and the main alternative you rejected. Anything that is a judgement call, not a forced move, belongs here.
4. **Open questions / assumptions** — what you had to assume because the request didn't say.

Keep it proportionate: a few lines for a small change, a structured list for a feature. A handful of clarifying questions is not a substitute for the brief — I want to see the shape of the thing before it exists.

**Settled is not approved.** When a conversation is discussing, designing, or clarifying an approach, resolving the open points does not authorize building. Don't jump from "that settles all the open points" straight into implementation — ask "shall I implement this?" and wait. Only start building when the current request explicitly asks for implementation.

**Nothing beyond the agreed scope.** Build what was agreed, not what you think would also be nice. Extra helpers, abstractions, config flags, fallbacks, endpoints, or "while I was in there" refactors are surprises — propose them, don't ship them. If the plan turns out to be wrong or incomplete mid-implementation, stop and say so rather than silently choosing a different design.

**Decisions taken mid-flight get surfaced.** If something not covered by the brief comes up while coding, call it out as you go — either ask, or state the choice explicitly in your running commentary. Never let a decision reach me for the first time as a fait accompli in the code.

### Report after implementation

Every implementation ends with a written summary — this is mandatory, even when the plan was pre-approved and the work went exactly as planned. Cover:

- **What was built** — features/behaviour now present or changed.
- **How it works** — what the new or changed code actually does, walked through at a level I can follow without reading the diff.
- **Files touched** — path plus one line on what changed in each.
- **Decisions taken** — design/architecture choices made during implementation, with reasons; explicitly flag any that differ from the plan.
- **Not done / deferred / assumed** — anything skipped, stubbed, worked around, or assumed, and anything I should verify.

I should never discover a feature, abstraction, or design choice by reading the code afterwards. If it isn't in the report, it shouldn't be in the codebase.

### Agents change nothing outside the repo

- **Agents change nothing outside the repo** (standing rule, 25-10-2026, by KLA). Every
  agent — orchestrator, advisor, reviewers, coder — changes only the repo's working tree and
  Claude's memory:
  - no installing software, packages, browsers, drivers or scripts on the machine; no global
    npm / pip / uv installs;
  - no changes to the operating system's settings, the registry, services, scheduled tasks,
    environment variables, or other repos;
  - experiments are read-only: read a value, run a small check; any script stays in the
    session scratchpad or `scratch/`;
  - allowed, because the repo's own tooling does it as written: what the repo's `tooling/`
    scripts do when run (e.g. installing Playwright's browsers, starting the e2e containers,
    the release tests' temporary worktree), installing the repo's own lockfiles when a step
    changes dependencies, and temporary git worktrees the agent removes itself;
  - anything else outside the repo: ask the user first.
  Put this limit in every spawn prompt that runs experiments.

### Release & deployment authorization

**Never run a release or deployment action without explicit instruction for that specific action in the current request.** This applies to:

- Building container images and pushing to any registry (`docker build`/`docker push`, or build scripts that push)
- Publishing packages or artifacts anywhere external
- Version stamping / release selection (e.g. `stamp_version.py`, editing deploy vars on the ansible workstation)
- Git `commit`, `push`, and tagging — the user reviews changes and commits himself
- Running Ansible playbooks or deploy scripts against any server
- Restarting/stopping services, containers, or VMs

Rules:

1. **Prepare, then stop.** Editing files in the local working tree to prepare a fix or release is fine. Once ready, stop and report: "Fix ready — shall I build / push / stamp / deploy?" Then wait for the go-ahead.
2. **Authorization is per-action and per-request.** Being told to build or stamp earlier in a session does NOT authorize doing it again for a later change. "Fix X" does not mean "release X".
3. **One step at a time.** "Build it" authorizes the build+push only — not stamping, not deploying. Each subsequent step needs its own explicit go-ahead.
4. **When in doubt, ask.** If an action changes anything outside the local working tree (registries, remote machines, remote repos, running services), it needs explicit confirmation first.

### Release workflow

Releases run via `tooling/common/release.py` (PyCharm run configs "Release (patch/minor/major)" → `-p`/`-m`/`-M`). Per-repo behaviour is configured in `tooling/common/release.env`: `TEST_CMD` (default `pytest`), `BUILD_SCRIPT`, `DEPLOY_SCRIPT` — an unset step is skipped.

The pipeline, in order:

1. Abort unless on `main` (override with `-B`) with a clean working tree.
2. Run `TEST_CMD`, unless HEAD carries a valid pre-flight stamp (`/pre-flight`, `tooling/common/preflight_stamp.py`): the tests passed on this exact commit, on this machine, with this `TEST_CMD`, within 7 days. The full suite must be 100% green. The frontend build must also complete with no new errors (pre-existing chunk-size warnings are acceptable).
3. Bump `VERSION`, commit `release vX.Y.Z` (body = bullet summary of commits since the last release) and create the annotated tag. Skipped when there are no changes.
4. Run `BUILD_SCRIPT` if set (typically builds and pushes container images to the registry).
5. Run `DEPLOY_SCRIPT` if set (deploys the release; which script varies per repo).
6. `git push --follow-tags` — publishes the release commit and tag. Last step, so a failed build/deploy never leaves a published release. Opt out with `GIT_PUSH=skip` in `release.env`.

Rules for Claude Code:

- **Never run a release unless explicitly asked** in the current request — see "Release & deployment authorization" above.
- Whether a release deploys depends on `DEPLOY_SCRIPT` in that repo's `release.env` — check it before answering deploy questions or running a release.
- The pipeline itself commits and pushes the release (steps 3 and 6) — the only automated git operations, and they run only as part of a release the user asked for.
- Run `/pre-flight` before the maintenance window, so a failing test is found before the users stop work. The skill needs a `## Pre-flight` section in the repo's `CLAUDE.md`; the release's gate is on everywhere and does nothing where no stamp exists.

### Stale bundle detection (web apps)

Every SPA must tell an open tab when a newer build is deployed and prompt the user to reload. Pattern: `SMTW-WebApp-Base.md` § Stale bundle detection.

### Working in numbered steps (optional)

A repo may work in numbered steps with `/step`: a brief, a brief review, the code with an impl report,
and a code review, each in `docs/steps/S0NN-<slug>/`. The skill (`.claude/skills/step/`), the agents
(`.claude/agents/`), the tools (`tooling/steps/`, `tooling/roadmap/` and the `tooling/step-*.bat` and
`tooling/render-mockups.bat` wrappers) and the two READMEs (`docs/steps/README.md`,
`docs/roadmap/README.md`) come from `smtw-common` and are edited there, never in the repo. A repo opts
in with two things of its own: a `## Step workflow` section in its `.claude/CLAUDE.md` (the entries
are listed in `docs/steps/README.md` § The repo's settings and index; one line each, in the form of
`## Pre-flight`) and its `docs/steps/INDEX.md`. The tools' tests live and run in `smtw-common` only
(`tooling/common/tests`, `tooling/run-common-tests.bat`). One orchestrator session at a time works on a
step: the skill takes a claim on it (`tooling/step-claim.bat`) and refuses a second session, and its
watchdog tells the user when an agent runs past its budget (27-10-2026, by KLA; no hook enforces it).

### RBAC Pattern

Canonical description — repo `CLAUDE.md` links here, doesn't restate. When a project self-implements role-based access control:

- **`config_rbac.py`** — single source of truth: `PERMISSIONS` dict maps `'module:action'` → tuple of granted roles. Route code references only permission key strings, never role names directly.
- **`auth_utils.py`** — `require_perm(key)` decorator, `has_perm(key)` for inline masking, `compute_permissions(role)` for building the user's permission list.
- **Wildcard `('*',)`** — any authenticated role passes. Never mix `*` with other roles in the same tuple.
- **`admin` bypasses unconditionally in code** — never put `admin` in permission tuples.
- **Fail-closed** — unknown permission keys grant nobody (not even senior roles).
- **Three-level read hierarchy** — `module:read_basic` (list/identity), `module:read` (all safe fields), `module:read_senior` (sensitive fields + analytics).
- **Frontend** — backend sends permission list via `/api/auth/me`; frontend stores it in a reactive ref; sidebar filters nav items by permission, using the minimum permission per nav item.

### Production access

To connect to, run commands on, or diagnose production servers (VMs, switches, OS), use the provided tooling scripts and skills — the `prod-vm` skill may apply; verify before connecting.

**Claude Code is read-only on production.** Connections go through `tooling/common/ccssh.py` (restricted `claude_ro` account) for diagnostics only. Any change on a prod machine — config edit, service restart, deploy, cleanup — is executed by the user: prepare the exact ready-to-paste commands with a one-line reason and expected outcome each, state risks, then wait for the user to run them and report back. Never attempt a change via another credential, session, or workaround.

### Reference architecture — `SMTW-WebApp-Base.md`

`.claude/SMTW-WebApp-Base.md` (synced) is the current reference architecture for SMTW Flask + Vue web apps: stack, layout, and proven patterns (RBAC implementation, DB access, migrations, job queues, uploads, versioning, …). Older repos may predate parts of it. It doesn't apply to non-web repos.

- It is not loaded automatically. When designing or adding a feature in a web app, read the relevant section first and follow the current pattern.
- When the area you're working in differs from the base pattern, point out the gap — don't fix it unasked. Raise gaps only for the area being worked on; a whole-repo gap analysis is `/smtw-review`'s job.
- Precedence: rules in this file win over `SMTW-WebApp-Base.md`. A repo's `CLAUDE.md` may record deliberate deviations from `SMTW-WebApp-Base.md`; those aren't gaps.

### Code review

Use `/code-review` to review a change or diff. Use `/smtw-review` for a full audit of the codebase against its docs (business rules, RBAC matrix, API contract, hindsight review).

## Defaults for New Projects

Repo `CLAUDE.md` overrides anything in this section.

### Stack

- **Languages**: Python (latest stable), JavaScript/TypeScript
- **Backend**: Flask (FastAPI for new services where it fits)
- **Frontend**: Vue.js (keep it simple — I'm learning it), Bootstrap
- **Database**: relational default → MariaDB; time-series → TimescaleDB (PostgreSQL); local/app data → SQLite
- **Python packaging**: `pyproject.toml` + uv (`uv sync`, `uv run`). Some legacy repos are still on pip + venv + `requirements.txt` — follow whatever the repo actually uses.
- **Configuration**: YAML or TOML for settings/config files
- **Deployment**: Docker Compose; Gunicorn behind Nginx; Ubuntu LTS

### Workflow

- Run Python via `uv run` (no venv activation needed). In legacy pip+venv repos, activate the venv first.
- Frontend dev servers via `npm run dev` (or framework equivalent).

### Wider infrastructure

The full infrastructure/tooling inventory (Proxmox, Ansible, ERPNext, MS SQL sources, etc.) rarely affects a coding session — see `.claude/CLAUDE-INFRA.md` and read it only when the task touches infrastructure.