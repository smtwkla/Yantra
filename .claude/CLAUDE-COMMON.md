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
- **Edge cases**: Consider nulls, empty inputs, boundary values, concurrent access. Clarify ambiguous requirements.
- **Error handling**: Handle errors at the right level with meaningful messages. Never silently swallow exceptions.
- **Deprecation**: Never use deprecated APIs/functions/modules. If found in existing code, rewrite to avoid them after consulting me.
- **Dependency health**: Prefer actively maintained libraries. Flag dependencies that are unmaintained (no release in 12+ months, archived repo), end-of-life, or abandoned, and suggest a maintained alternative.
- **Idle connections**: Pooled DB/HTTP connections die after long idle periods (overnight). Detect a dead connection on first use (`OperationalError`/`InterfaceError` or equivalent) and reconnect, rather than returning a 500 after a quiet night.

### Migrations & dev databases

- **Migrations are append-only**: Never edit an applied migration; always add a new version.
- **Dev/test DBs are disposable**: On any schema drift or stale-schema symptom, drop the schema and let migrations rebuild it — don't debug a stale test DB.

### Conventions

- **Timezone**: Servers run UTC; business logic uses IST (Asia/Kolkata, UTC+5:30).
- **Date formats**: Indian format `DD-MM-YYYY` (preferred) or ISO 8601 `YYYY-MM-DD` for entry, display, and storage. Never US `MM/DD/YYYY`.
- **Raw SQL over ORM** with the appropriate driver, unless the framework requires an ORM.
- **Secrets**: Credentials in gitignored `secrets_*.py` files, with `example_secrets_*.py` templates. (Canonical description — repo `CLAUDE.md` links here, doesn't restate.)
- **Data directories**: App-owned data in a gitignored `data/` folder, organized by tenant/company if multi-tenant. Support env-var overrides for default paths.
- **Git commit messages**: One line, feature-focused — what changed, brief context after a dash or semicolon. No multi-line bodies or bullet lists.
  Example: `Auto-generated project index: Index.md - triggered on project save and daily materialisation run;`

### Shell preference (Windows)

Prefer the Bash tool over PowerShell — PowerShell mangles special characters, wasting turns. Use PowerShell only when the task genuinely requires it (Windows cmdlets, `Invoke-Command`, remote Windows VM management).

### Wrapper scripts

Wrap recurring test/build/query commands in `tooling/*.bat` (or `.sh`) scripts so Claude Code permissions can whitelist them once. Prefer running the wrapper over retyping the raw command.

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
2. Run `TEST_CMD` — the full suite must be 100% green. The frontend build must also complete with no new errors (pre-existing chunk-size warnings are acceptable).
3. Bump `VERSION`, commit `release vX.Y.Z` (body = bullet summary of commits since the last release) and create the annotated tag. Skipped when there are no changes.
4. Run `BUILD_SCRIPT` if set (typically builds and pushes container images to the registry).
5. Run `DEPLOY_SCRIPT` if set (deploys the release; which script varies per repo).
6. `git push --follow-tags` — publishes the release commit and tag. Last step, so a failed build/deploy never leaves a published release. Opt out with `GIT_PUSH=skip` in `release.env`.

Rules for Claude Code:

- **Never run a release unless explicitly asked** in the current request — see "Release & deployment authorization" above.
- Whether a release deploys depends on `DEPLOY_SCRIPT` in that repo's `release.env` — check it before answering deploy questions or running a release.
- The pipeline itself commits and pushes the release (steps 3 and 6) — the only automated git operations, and they run only as part of a release the user asked for.

### Stale bundle detection (web apps)

Every SPA must tell an open tab when a newer build is deployed and prompt the user to reload. Pattern: `SMTW-WebApp-Base.md` § Stale bundle detection.

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