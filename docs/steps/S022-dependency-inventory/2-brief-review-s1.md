```
Step: S022 — Software inventory and vulnerability check
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

Reviewed against: 167e178

(Working tree: only `.claude/skills/step/SKILL.md` is modified, which the brief
does not touch; no step's changes are uncommitted.)

# S022 — Staleness review s1

**Verdict: no blocker or major finding. No finding at all; the brief still
holds and the coder can start.**

## What changed since the baseline

The brief's `Baseline:` is `c2c45d2 + uncommitted S013, S014`. Since then:

| Commit | Content | Effect on the brief |
|---|---|---|
| `ae0f183` | S013 committed | Already in the baseline as "uncommitted S013" |
| `dde0d68` | S014 committed | Already in the baseline as "uncommitted S014"; this is where `backend/uv.lock` (+14 lines, `qrcode 8.2` and its Windows-only `colorama` marker) and `backend/pyproject.toml` (+`qrcode>=8.2`) changed |
| `167e178` | docs only (`docs/steps/README.md`, `docs/Plan.MD`, S022 brief) | No code |

So the only code diff between `c2c45d2` and `HEAD` among the files the brief
relies on is S014's `qrcode` line in the backend lockfile, and round 3 already
read that working tree. Nothing the brief says about the code is new to it.

## Findings

None.

## Checked and found consistent

Each statement of the brief about the code, against the tree at `167e178`:

- **Lockfiles found by `git ls-files`** (§ 1, § 5.1): `git ls-files` still
  yields exactly three — `backend/uv.lock`, `frontend/package-lock.json`,
  `uv.lock` — so the manual check "`sbom/` holds three files (`backend`,
  `frontend`, `root`)" and the names in § 1 still hold. `sbom/` does not exist
  yet (the script creates it); `scratch/` exists and is gitignored (§ 4).
- **Root lockfile** (§ 1): the root `uv.lock` still holds only `python-dotenv`
  1.2.4 under the virtual `yantra` project, as the brief says.
- **The uv export command** (§ 5.1): `uv export --format cyclonedx1.5 --frozen
  --preview-features sbom-export` runs on the installed `uv 0.10.10`
  (Open question 2, uv ≥ 0.10, holds), gives `bomFormat CycloneDX`,
  `specVersion 1.5`, and leaves `backend/uv.lock` untouched (`git status`
  clean after the run). Full export: 24 components; `--no-dev`: 19, the
  difference being `pytest`, `pluggy`, `iniconfig`, `packaging`, `pygments` —
  the dev set § 5.2 expects. `qrcode@8.2` and `colorama@0.4.6` appear in
  both, i.e. as runtime, which is right (colorama is a `win32`-marked runtime
  dependency of qrcode).
- **`metadata.component.bom-ref`** (§ 3, `direct()`): the uv export sets it
  (`yantra-backend-1@0.1.0`), so the `dependencies[]` lookup the brief
  describes has something to find. `metadata` carries `timestamp` and `tools`,
  the two fields `stable_sbom` strips.
- **"Runtime" = `--no-dev`** (§ 5.2): `tooling/build/Dockerfile.backend` line 20
  still installs with `uv sync --frozen --no-dev --no-install-project`; the
  backend `pyproject.toml` has only the `dev` group and no `[tool.uv]
  default-groups`, so "none has one today" (BR3-05) still holds.
- **`tooling/run-tests.bat`** (§ 3): still the two `call` lines (backend,
  frontend); "gains a third line" holds.
- **`.gitignore`**: `scratch/` and `.idea/` are listed (§ 3, § 4 unchanged).
- **`.claude/CLAUDE.md`**: no diff since `c2c45d2`; the "npm 10.9 crashes"
  bullet the brief cites for `npx npm@11` is still there, and the Yantra
  Specifics list is where the new section goes.
- **No `tooling/deps/`, `tooling/run-deps-*.bat` or `sbom/` exists yet**, so
  nothing the step creates collides with anything added by S013/S014.
- **`npx`** is on the path as `npx` and `npx.cmd` (§ 3, `shutil.which`).

After this check the planner sets `Baseline: 167e178` (README § Stale brief
check, step 2).
