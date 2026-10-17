# CLAUDE.md — Yantra

@CLAUDE-COMMON.md

The shared conventions imported above apply to all repos. This file contains repo-specific instructions: anything here overrides the Defaults section of CLAUDE-COMMON.md; its Invariants always apply.

## Yantra Specifics

- **Stack**: Flask backend + Vue.js frontend (see [SMTW-WebApp-Base.md](SMTW-WebApp-Base.md)); MariaDB (PyMySQL + DBUtils pool); Keycloak realm `Office.smtw.in`. Product plan: `docs/Plan.MD`. Domain knowledge: `docs/Maintenance-Philosophy.md` (rules, TPM-based) and `docs/Plant-Facts.md` (the factories as they are) — read both before designing any maintenance module.
- **Standards and best practice**: Yantra must help the plant adopt industry maintenance standards and best practices (TPM, ISO 14224, EN 13306, ISO 55000, SMRP KPIs). At every design step, name the relevant standard or practice, explain in plain terms what it says and why, show how the proposal follows it — or state where and why it deliberately departs — and prefer standard terms over inventing local ones. The project owner is learning maintenance practice as the project goes.
- **Step workflow**: work is done in numbered steps (`S001`, …) whose brief, reviews and implementation report live in `docs/steps/` — read `docs/steps/README.md` for the file naming, finding IDs and gates before planning, reviewing or coding a step. Never code a step whose brief is not `Approved` by the user. `/step` (skill) orchestrates the cycle from one terminal with the `brief-reviewer`, `coder` and `code-reviewer` subagents (`.claude/agents/`).
- **RBAC deviation (S011)**: roles do not all come from the token. Keycloak gives only `maintenance_team` (may log in, grants nothing), `it_admin` and admin (`mspv-apps-admin`). The maintenance roles (`config_rbac.SITE_ROLES`) are held in Yantra per person and site (`memberships`, `person_units`; Team in Masters) and are read lazily per request. Keys in `config_rbac.SITE_SCOPED` are checked at the record's site (`has_perm_at`, `accessible_unit_ids(cur, key)`); others use the union. `config_rbac.py` stays the single source of roles and keys; fail-closed and the admin bypass are unchanged. New site-scoped keys must be added to `SITE_SCOPED`. Keycloak setup: `docs/Keycloak.md`.
- **Ports (dev)**: backend 5001, Vite 5176, MariaDB 3307 (3306 is SaralWeb's dev DB). Container backend listens on 5000.
- **Dev commands** (also PyCharm run configs):
  - DB: `tooling/dev/dev-db-up.bat` / `dev-db-down.bat` / `dev-db-reset.bat` — compose project `yantra-dev`, DBs `vel_yantra_master` + `vel_yantra_test`
  - Backend: PyCharm "Backend" (`FLASK_DEBUG=1`, `DEV_AUTH_BYPASS=1`, interpreter `uv (Yantra-backend)`); frontend: "Frontend" (`npm run dev`)
  - Tests: `tooling/run-tests.bat` (both), `run-backend-tests.bat` (needs the dev DB), `run-frontend-tests.bat`
- **Secrets**: `backend/secrets_app.py`; in prod rendered by Ansible (`smtw_erp_devops/erp_server/yantra/secrets_app.py.j2`) — keep `example_secrets_app.py` field names in step with that template. Missing file falls back to the example only in dev/test.
- **Files (S006)**: uploads live under `DATA_DIR` (default `<repo>/data/`, gitignored); in prod `DATA_DIR=/app/data`, the App-FS NFS share bind-mounted by the devops compose. Served only through permission-checked routes, never as static files.
- **DB may not exist**: the app must start and serve while the DB is unreachable or not created (fresh deploy). `local_db.ensure_schema()` retries migrations every 30 s; `get_db()` raises `DBUnavailable` → 503.
- **Release**: Release (patch/minor/major) run configs → `tooling/common/release.py`, with `TEST_CMD` / `BUILD_SCRIPT` / `DEPLOY_SCRIPT` and the deploy settings set as run-config env vars (a hook blocks writing `release.env`).
- **Deploy**: `tooling/deploy.py` over plink to PuTTY session `ansible-ws` (`/home/kla/smtw/erp_server`): stamps `YANTRA_VER` (bare version, e.g. `"0.1.2"`) in `yantra/vars/settings_vel_yantra_master.yaml` (relative to `erp_server/`), then runs `./erp_spanner.py deploy vel yantra master`. The compose pins the tag, so a VelKilnMaster-style `compose pull` would not update. `erp_spanner.py` exits 0 even when the playbook fails, so `deploy.py` checks the PLAY RECAP itself. `--check` is read-only; `--stamp-only` skips the Ansible run. "Deploy" run config = redeploy current `VERSION`.
- **npm**: npm 10.9 crashes (`edgesOut`) resolving vitest's optional peers — use `npx npm@11 install` to change dependencies; `npm ci` (Docker) is fine.
- **Not yet built** (Plan.MD phase 1, deliberate gaps for now): network gate + access log, task_queue (worker.py idles), PWA shell.
