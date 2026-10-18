```
Step: S022 — Software inventory and vulnerability check
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

Reviewed against: c2c45d2 + uncommitted S013, S014

# S022 — Brief review, round 3 (full track; round 3 of 3, U1)

**Verdict: no `blocker` or `major` finding is open.** The U1 mechanics all work
as the brief describes, each tested on this machine in a scratchpad replica or
read-only in the two repos: `tooling/deps/pytest.ini` is the config pytest
picks when it is given `tooling/deps/tests` from the repo root (rootdir
`tooling/deps`, `pythonpath = .` makes `audit_core` importable, no project
file touched); `uv run tooling/deps/audit.py` with a PEP 723 header runs in an
isolated environment that ignores the root project, finds the sibling
`audit_core.py` through `sys.path[0]`, and passes its exit code through
`uv run` and the `.bat`; `uv export --frozen` works in each lockfile's folder in
aibots too, including its `package = false` root project; `git ls-files`
finds exactly the three Yantra lockfiles and the two aibots ones. Every earlier
`Accepted` finding is still in the text after U1, with two bookkeeping slips
(BR3-03). Two `minor` findings: `git ls-files` prints paths relative to the
**current directory**, so the script must run git at the root or the "any
directory" promise of § 1 fails; and the test wrapper now reaches for the
network on a cold or forced-refresh uv cache, which the brief's own decision
text ("tests must not depend on the network") should acknowledge. Three nits.

Reviewed against: the brief (as revised for U1); `2-brief-review-r1.md`,
`-r2.md`; `docs/steps/README.md` (full track, index row, Stale brief check);
`CLAUDE-COMMON.md` (Dependency health, Pure core, Testing, Wrapper scripts,
Release workflow); `CLAUDE.md`; `SMTW-WebApp-Base.md` § Shared Tooling Sync,
§ Testing Pattern; `docs/Plan.MD` (no mention of SBOMs or aibots, nothing to
contradict). Yantra: root `pyproject.toml` + `uv.lock`, `backend/pyproject.toml`
(dev group `pytest>=8.0`, no pytest table), `.gitignore`, `tooling/run-tests.bat`,
`run-backend-tests.bat`, `run-frontend-tests.bat`, `tooling/common/release.py`
(`subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)` for `TEST_CMD`),
`tooling/common/sync_common.py` (`FILES`). aibots (read-only, `76440f8`):
`pyproject.toml` (`package = false`, dev group `pytest`, `httpx`),
`tooling/pyproject.toml`, `pytest.ini`, `.gitignore`, `tooling/.gitignore`,
`.python-version` (3.14), `tooling/release.bat`, both `uv.lock` heads. Tools: uv
0.10.10, local npm 10.9.2, Pythons 3.11–3.14 installed. Ran, in the scratchpad or
read-only: a replica repo shaped like aibots (root `pytest.ini` with
`testpaths = tests`, `tooling/pyproject.toml`, root `.venv` via `uv sync`) with
the brief's `tooling/deps/pytest.ini`, `audit_core.py`, a PEP 723 `audit.py` and
the three `.bat` files exactly as § 3 writes them, run from the root, from a
subdirectory and through `cmd.exe`; `uv run --no-project --with pytest` with a
dead proxy, with `--offline` and with `--refresh`; `uv export --format
cyclonedx1.5 --frozen --preview-features sbom-export [--no-dev]` in aibots's root
and `tooling/` (`git status` unchanged afterwards); `git ls-files` from
`Yantra/backend/` with and without `--full-name`.

---

## Earlier `Accepted` findings, verified in the text after U1

| Finding | In the brief? | Note |
|---|---|---|
| BR1-01 strip, sort, write on change | § 1.1, § 5.1, § 7 | Unchanged by U1 |
| BR1-02 `--no-dev` set difference; dev gates | § 5.2, § 7 | Now "every uv lockfile" (BR2-03) |
| BR1-03 OSV rules | § 5.3 | Unchanged |
| BR1-04 tests wired into `run-tests.bat`; audit stays out | § 3 | Mechanism changed by U1 (`run-deps-tests.bat`, `uv run --with pytest`); works, see Checked. Review-log row still describes the old mechanism — BR3-03 |
| BR1-05 exit 2 for any incomplete step; unknown gates | § 5.5, § 2 | Unchanged |
| BR1-06 endpoints, `today` in, 20 s timeout | § 5.4, § 3 | Unchanged |
| BR1-07 `--frozen`, preview flag, spec 1.5 | § 5.1, § 2, § 3 | Unchanged |
| BR1-08 no committed run config; `.bat` shape; `scratch/` | § 3, § 4 | `.bat` now `uv run tooling\deps\audit.py` (no `python`, no `%*`): correct for a PEP 723 script, tested |
| BR1-09 inline deps of `tooling/common` as a gap | § 1 Out of scope | Unchanged |
| BR2-01 backend's own pytest table | — | **Superseded** by U1: no project file gains a pytest table, so the problem BR2-01 described cannot arise. The log row still says the table is added — BR3-03 |
| BR2-02 `metadata.tools` stripped | § 1.1, § 3 | Unchanged |
| BR2-03 every uv lockfile; compare by purl | § 5.2, § 8 | Verified on aibots too (Checked) |
| BR2-04 stdout capture, `shutil.which("npx")`, `--yes`, `sbom/` created | § 3 | Unchanged |
| BR2-05 `bomFormat`; User-Agent; 365 days; empty `urls` | § 3, § 5.4 | User-Agent now `<repo folder name>-deps-audit` (portable, fine). Empty `urls` → "reported, not gating" rather than r2's "exit 2": a better rule (staleness never gates), but the log says plain `Accepted` — BR3-03 |

---

## Findings

### BR3-01 — `minor` — `git ls-files` prints paths relative to the current directory, not the repo root

**Problem.** § 5.1 takes the root from `git rev-parse --show-toplevel` and the
lockfiles from `git ls-files`, and § 1 promises `uv run tooling/deps/audit.py`
works "any OS" (the `.bat` does `cd /d "%~dp0.."`, but the plain command is
the portable one and the brief does not say it must run from the root).
Verified: from `Yantra/backend/`, `git ls-files | grep uv.lock` prints
`uv.lock` (meaning `backend/uv.lock`) and does not list `frontend/package-lock.json`
or the root lock at all — `git ls-files` lists only the paths **under the
current directory**, relative to it. With `--full-name` it prints
`backend/uv.lock` but still only the subtree; `git -C <root> ls-files` (or
`cwd=root` in `subprocess.run`) prints all three, root-relative. `sbom_name`,
`sbom/` and `scratch/` all depend on root-relative paths.

**Why it matters.** Run from a subdirectory (a PyCharm terminal opened in
`backend/`, or a scheduler later), the script would see one lockfile, name its
SBOM `root.cdx.json`, and under the "lockfile removed" rule of § 5.1 **delete**
the other two committed SBOMs. The `.bat` hides this on Windows; the aibots bot
and any Linux run would not have it.

**Options.**
1. **Run git at the root and say so.** § 5.1: "`git ls-files -z` run with
   `cwd=root` (the `--show-toplevel` result); paths are root-relative". `-z`
   also avoids git quoting non-ASCII paths (`core.quotepath`). Every other path
   the script writes (`sbom/`, `scratch/`) is then `root / …`, never relative
   to the process's cwd. One sentence, one unit test is not possible (shell),
   so make it a rule the code reviewer checks.
2. `os.chdir(root)` first. Works, but a hidden side effect in a script that
   also spawns `uv` and `npx` in other folders.

**Recommendation.** Option 1.

---

### BR3-02 — `minor` — The test wrapper now needs the network on a cold or refreshed uv cache; the brief's decision text says the opposite

**Problem.** `tooling/run-deps-tests.bat` runs `uv run --no-project --with
pytest pytest …`, and `run-tests.bat` is `release.py`'s `TEST_CMD`. § 7
("Not in the test run") gives the reason "Tests must not depend on the
network", and Open question 4 accepts that pytest is "fetched at its newest
version … and not locked", but neither says that the fetch itself is a network
step inside the test run. Measured: a warm cache resolves and installs the
ephemeral environment in ~0.3 s and worked with a dead proxy a few minutes
later; `--offline` works; but `--refresh` with no network fails before pytest
starts (`client error (Connect)`), which is what a cold cache (fresh clone, new
machine, `uv cache clean`) does too. The backend suite does not have this: `cd
backend && uv run pytest` uses the locked `.venv`. r1 rejected this very option
(BR1-04 option 2) for this reason; U1 chose it for portability, which is a fair
trade, but the trade should be written down.

**Why it matters.** A release on a machine with a cold uv cache and no PyPI
access would fail at step 2 with a uv error, not a test failure — confusing
but safe (the release machine pushes images and git anyway, so in practice it
has the network). The second effect is the unpinned `pytest`: a new pytest major
could change behaviour on the day it is published, on whichever machine runs
next. Small, but it is the "same input, different result" class of surprise
this brief has been removing elsewhere (BR1-01, BR2-02).

**Options.**
1. **Keep U1, state it honestly.** § 7 reason → "the *tests* do not touch the
   network; `uv run --with pytest` fetches pytest once into uv's cache (network
   on a cold cache)"; Open question 4 adds "a new pytest major may need a
   look"; the CLAUDE.md section says the same in one line. No code change.
2. As 1, plus a floor and ceiling: `--with "pytest>=8,<10"`. Rules out a
   surprise major; one number to raise occasionally. Still network on a cold
   cache.
3. Make `tooling/deps/` a tiny uv project (`pyproject.toml` with pytest in a
   dev group, `uv.lock`). Locked and offline-capable, and `git ls-files` would
   then inventory the audit tool itself (`sbom/tooling-deps.cdx.json`), which
   is honest. But it adds two files to carry into `smtw-common`, and `uv run`
   from `tooling/deps/` would then find a project — more to explain than U1
   wanted.

**Recommendation.** Option 2 (1 plus the version range). Option 3 is the
"proper" answer if the tooling tests ever grow; not now.

---

### BR3-03 — `nit` — Review-log rows that no longer match the text after U1

Three rows read as current but are not:
1. **BR1-04** "root dev group, pytest config, third line in `run-tests.bat`" —
   the root dev group and the root pytest table are gone; only the third line
   remains (now `call run-deps-tests.bat`).
2. **BR2-01** "`backend/pyproject.toml` gets its own table (§ 3)" — no longer
   done, and no longer needed (nothing above `backend/` has a pytest table).
3. **BR2-05** item 4 was accepted as "no `urls` → exit 2 with the package
   named"; the text (§ 3, § 5.4) says "release date unknown, reported, not
   gating". That is the better rule (§ 7: staleness is a judgement, not an
   emergency), so mark it `Accepted (alternative)` like BR2-02.

The U1 paragraph does say "the BR1-04 and BR2-01 answers change accordingly",
but a reader of the tables will not see it. Strike or annotate the three rows
(`~~…~~ superseded by U1: …`).

---

### BR3-04 — `nit` — `sbom_name` collisions and an index entry with no file

1. Two folders can map to one name: `a-b/uv.lock` and `a/b/uv.lock` both give
   `a-b.cdx.json`; a folder literally named `root/` collides with the repo
   root. Unlikely in our repos, but the "lockfile removed → delete the SBOM"
   rule makes a silent overwrite worse than a loud stop. Rule: duplicate names
   → exit 2 naming both lockfiles. One test case for `sbom_name` callers.
2. `git ls-files` lists the **index**: a lockfile deleted in the working tree
   but not yet `git rm`-ed is still listed, and `uv export` in that folder
   would fail with uv's message rather than the script's. Rule: a listed path
   that does not exist → exit 2 naming it (the § 5.5 "which step" message).

---

### BR3-05 — `nit` — Two portability details the aibots check surfaced

1. **`npx` only when needed.** aibots tracks no `package-lock.json` (its
   `admin-ui/frontend/package-lock.json` is gitignored on purpose), so a
   machine without Node must still run the audit there. § 3 says `npx` is
   resolved with `shutil.which`; add "only when an npm lockfile was found;
   `None` then is exit 2". Same for `uv` — trivially present, since `uv run`
   started the script.
2. **`--no-dev` removes the `dev` group only.** A project with another default
   group (`[tool.uv] default-groups = ["dev", "docs"]`) would count `docs` as
   runtime. `--no-dev` matches what Yantra's `Dockerfile.backend` installs
   (`uv sync --frozen --no-dev`) and aibots has only `dev`, so keep it, but say
   in § 5.2 that "runtime" means "what `--no-dev` leaves", the same definition
   the Docker build uses; `--no-default-groups` is the general form if a repo
   ever needs it.

---

## Checked and found consistent

- **pytest config selection (U1), tested.** In a replica with an aibots-style
  root `pytest.ini` (`testpaths = tests`, a multi-dir `pythonpath`), a
  `tooling/pyproject.toml` above the new folder, and `tooling/deps/pytest.ini`
  (`testpaths = tests`, `pythonpath = .`): `uv run --no-project --with pytest
  pytest tooling/deps/tests` from the root gives `rootdir: …\tooling\deps`,
  `configfile: pytest.ini`, `import audit_core` resolves, 2 passed; the same
  from a subdirectory with a relative path; the same through `cmd.exe` with
  the `.bat`'s backslash path. pytest starts its walk at the common ancestor
  of the **arguments** and takes the first `pytest.ini` it meets, so the root
  file and `tooling/pyproject.toml` are never reached — the brief's sentence
  is right as long as the wrapper passes the tests path, which it does. A
  plain `pytest` at the aibots root still collects only `tests/` (its
  `testpaths` exists), so the new tests do not leak into aibots's own run.
  `.pytest_cache` lands in `tooling/deps/` (the rootdir) and ignores itself
  (`.pytest_cache/.gitignore`); `__pycache__/` is ignored in both repos.
- **PEP 723 script (U1), tested.** `uv run tooling/deps/audit.py` with
  `requires-python = ">=3.12"`, `dependencies = []`: runs in
  `uv\cache\environments-v2\audit-…` on Python 3.14.3 (newest satisfying
  interpreter), **not** in the root `.venv` (the root project's `python-dotenv`
  is not importable from it, so the project is ignored as the brief says);
  `sys.path[0]` is `tooling/deps`, so `import audit_core` works; `sys.exit(2)`
  comes back as `rc=2` from `uv run`, from the `.bat`, and from a subdirectory
  cwd. Works with a dead proxy (no dependencies to fetch).
- **The three `.bat` files as § 3 writes them**, under `cmd.exe`:
  `run-deps-audit.bat` from another directory `cd`s to the root and returns the
  script's code (2); `run-tests.bat`'s `call "%~dp0run-deps-tests.bat" || exit
  /b 1` returns 0 on a green run and 1 on a failing test (`1 failed, 2
  passed`). `release.py` runs `TEST_CMD` with `shell=True, cwd=PROJECT_ROOT`,
  so the chain works there too.
- **`uv export` per lockfile folder on aibots (U1), read-only.** Root
  (`package = false`, requires-python 3.14, 47 components) and `tooling/`
  (1 component) both export with `--frozen --preview-features sbom-export`,
  no stderr, `git status` unchanged. `metadata.component.bom-ref` is present
  in both (`aibots-1@0.0.0`, `tooling-1@0.1.0`), is listed in
  `dependencies[]`, and `direct()` gives 16 / 1 — so `direct()` as specified
  works on a virtual project. Every component has a purl. `--no-dev` set
  difference by purl: exactly `pytest`, `iniconfig`, `pluggy`, `pygments`;
  `httpx` (in aibots's dev group) is correctly **not** dev-only because
  `anthropic` needs it — the by-purl rule (BR2-03) does the right thing.
- **Lockfile discovery and names (U1).** Yantra `git ls-files` (from the
  root): `backend/uv.lock`, `frontend/package-lock.json`, `uv.lock` →
  `backend`, `frontend`, `root`, as § 1 lists. aibots: `tooling/uv.lock`,
  `uv.lock` → `tooling`, `root`; no npm lockfile (see BR3-05.1); its six
  `requirements.txt` are not lockfiles and are rightly left to the queued note.
  Neither repo ignores `sbom/`; both ignore `scratch/`.
- **Nothing Yantra-specific in `tooling/deps/` (U1).** § 3 names no Yantra
  folder, project or port; the User-Agent derives from the repo folder; the
  Yantra-specific wiring (`run-tests.bat` third line, CLAUDE.md section, the
  three expected SBOM names in the manual check) is in Yantra's own files.
  `tooling/deps/` is outside `sync_common.py`'s `FILES`, so a later move to
  `smtw-common` is a sync-inventory change, not a code change.
- **uv 0.10.10** installed (`uv --version`), as Open question 2 assumes; `git`
  on PATH (Open question 3).
- **Full-track sections** all present; header `Track: full`, `Status: In
  review`, no `Baseline` yet (correct before approval); index row agrees.
- **Standards** unchanged since r2 and still right: ISO 27001:2022 A.8.8
  (know the software in use, learn of its vulnerabilities, act in time) and
  A.5.9 (asset inventory); CycloneDX 1.5 (1.6 = ECMA-424), purl (ECMA-427),
  SPDX (ISO/IEC 5962); GHSA severity scale; CVE grouping. Maintenance
  standards (ISO 14224, EN 13306, ISO 55000, SMRP, TPM) do not bear on a
  tooling step and are rightly absent. For the user: NTIA's "minimum elements"
  for an SBOM also ask for the SBOM author and timestamp — the git commit
  supplies both for a file kept in the repo, which is why stripping them
  (BR1-01, BR2-02) is sound.
- **Manual checks**: both important, both need a person; the first names the
  three Yantra SBOMs correctly after the `tooling` → `root` rename.
- **Out of scope and queue** consistent: the image SBOM and the aibots bot are
  in `README.md` § Queued with the right notes (aibots installs from
  `requirements.txt`, so its lockfile is not what runs).
- **Scope**: U1 added no new module or dependency; the pure core / thin shell
  split (`audit_core.py` / `audit.py`, `today` passed in) is unchanged.
