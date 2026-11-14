# Doc-Index — Yantra

The documentation files of this repo, read by `/update-docs`. Each row says what the file holds and when it
falls due. Files synced from smtw-common are listed but edited there, never here (a sync overwrites them).
Step files (`docs/steps/S0NN-*/`), roadmap items (`docs/roadmap/R0N-*.md`) and audits (`docs/review/`) are
records of their time and are not kept current.

## Project rules (`.claude/`)

| File | What it holds | Update when |
|---|---|---|
| `.claude/CLAUDE.md` | Yantra's specifics, pre-flight and step settings, docs to keep current, SMTW-Review points | an invariant, dev command, port, secret or audit point is added |
| `.claude/CLAUDE-COMMON.md` | Shared rules of all SMTW repos | **synced from smtw-common, never edited here**; tell KLA |
| `.claude/CLAUDE-INFRA.md` | Infrastructure inventory | synced from smtw-common |
| `.claude/SMTW-WebApp-Base.md` | Reference architecture of SMTW web apps | synced from smtw-common |
| `.claude/agents/*.md` | The step workflow's agents | synced from smtw-common |

## Product and domain (`docs/`)

| File | What it holds | Update when |
|---|---|---|
| `docs/Plan.MD` | Product plan: modules, decisions, open questions | a step builds or changes what a module section describes |
| `docs/Maintenance-Philosophy.md` | The maintenance rules (TPM-based) | a maintenance rule is settled |
| `docs/Plant-Facts.md` | The plants as they are | a fact about the plants is learned |
| `docs/Keycloak.md` | Keycloak realm set-up: roles, clients, claims | roles, clients or token claims change |
| `docs/schema.md` | Database schema conventions | a convention changes |
| `docs/schema/notes.json` | Each table's area and purpose; planned tables (hand-edited) | a migration adds or changes a table |
| `docs/schema/schema.json`, `schema-data.js` | Generated schema (never hand-edited) | `tooling\schema-docs.bat write` after a migration |
| `docs/SMTW-Utils-Gallery.md` | The gallery's app contract | synced from smtw-common |
| `CHANGELOG.md` | Release notes per version | written by the release (`release_changelog.py`) |

## Step and roadmap workflow

| File | What it holds | Update when |
|---|---|---|
| `docs/steps/INDEX.md` | Index and queue of steps | each step's status changes |
| `docs/steps/device-checks.md` | Real-device checks still to do | a step has a real-device check, or one is done |
| `docs/steps/feedback-log.md` | Agents' feedback items, triaged | a feedback review |
| `docs/steps/README.md` | The step workflow's rules | synced from smtw-common |
| `docs/steps/analysis/*.md`, `feedback-advice-*.md` | One-off analyses | records; not kept current |
| `docs/roadmap/INDEX.md` | Index of roadmaps and their items | a roadmap item is taken up or done |
| `docs/roadmap/README.md` | The roadmap rules | synced from smtw-common |

## User help (`help/`, published on gallery.mspv.app)

| File | What it holds | Update when |
|---|---|---|
| `help/README.md` | How Help is built, retaken and published | the guide's slide or picture count, or the retake steps, change |
| `help/guide-outline.md` | Each screenshot: who, where, how-to; slide → shot → alt text | a shot is added, removed or renamed |
| `help/guide/index.html` | The user guide (slides and reading page) | screens change, before a release, on KLA's word (`tooling\help-shots.bat`) |
| `help/home/index.html` | The Help home | the guide's slide count, version or date changes |
| `help/documents/index.html` | Documents and photos guide | the document or photo screens change |
