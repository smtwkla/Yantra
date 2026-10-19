# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Software inventory and vulnerability check (thin shell around audit_core).

    uv run tooling/deps/audit.py

Finds every tracked uv.lock and package-lock.json, writes a CycloneDX 1.5 SBOM
for each into sbom/, looks every library up in OSV, checks the latest release of
every direct dependency, and writes scratch/dependency-report.md.

Exit 0: clean. 1: a critical, high or unknown-severity vulnerability. 2: a step
could not be completed (never read that as clean).

Nothing here names a project: the same files work in any repo.
"""
import json
import shutil
import subprocess
import sys
import traceback
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_core as core  # noqa: E402

TIMEOUT_SECONDS = 20
OSV_BATCH_SIZE = 1000
OSV_URL = "https://api.osv.dev/v1"
PYPI_URL = "https://pypi.org/pypi"
NPM_URL = "https://registry.npmjs.org"
NETWORK_ERRORS = (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError)


class StepFailed(Exception):
    """A step did not complete; the message goes into the report."""


# --- helpers: processes and files -----------------------------------------

def run(cmd, cwd):
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    except OSError as e:
        raise StepFailed(f"cannot run {cmd[0]}: {e}") from e
    if done.returncode != 0:
        raise StepFailed(f"{' '.join(cmd)} failed in {cwd}: {done.stderr.strip()[-400:]}")
    return done.stdout


def find_root():
    return Path(run(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd()).strip())


def find_lockfiles(root):
    """Tracked lockfiles as '/'-separated paths from the root, sorted. git lists
    only the current folder's subtree, hence cwd=root."""
    listed = run(["git", "ls-files", "-z"], cwd=root).split("\0")
    return sorted(p for p in listed if p.rpartition("/")[2] in (core.UV_LOCK, core.NPM_LOCK))


def export_sbom(root, lock_path):
    """(full document, runtime document or None) for one lockfile."""
    folder = root / lock_path.rpartition("/")[0]
    if lock_path.endswith(core.UV_LOCK):
        base = ["uv", "export", "--format", "cyclonedx1.5", "--frozen", "--preview-features", "sbom-export"]
        return _parse(run(base, folder), lock_path), _parse(run(base + ["--no-dev"], folder), lock_path)
    npx = shutil.which("npx")
    if not npx:
        raise StepFailed(f"npx not found on the path; needed for {lock_path}")
    cmd = [npx, "--yes", "npm@11", "sbom", "--sbom-format", "cyclonedx", "--package-lock-only"]
    return _parse(run(cmd, folder), lock_path), None


def _parse(text, lock_path):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise StepFailed(f"export of {lock_path} is not JSON: {e}") from e
    problem = core.check_spec(doc)
    if problem:
        raise StepFailed(f"export of {lock_path}: {problem}")
    return doc


def write_if_changed(path, doc):
    """JSON with 2-space indent and a final newline; untouched when equal, so
    git status stays clean."""
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


# --- helpers: network ------------------------------------------------------

def http_json(url, user_agent, body=None):
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def osv_hits(purls, user_agent):
    """{purl: [advisory ids]}, following next_page_token."""
    hits = {}
    for start in range(0, len(purls), OSV_BATCH_SIZE):
        chunk = purls[start:start + OSV_BATCH_SIZE]
        pending = [{"package": {"purl": p}} for p in chunk]
        owners = list(chunk)
        while pending:
            answer = http_json(f"{OSV_URL}/querybatch", user_agent, {"queries": pending})
            next_pending, next_owners = [], []
            try:
                paired = core.pair_batch_results(owners, answer["results"])
            except (KeyError, TypeError, ValueError) as e:
                raise StepFailed(f"OSV answer does not match the query: {e!r}") from e
            for query, (purl, result) in zip(pending, paired):
                hits.setdefault(purl, []).extend(v["id"] for v in result.get("vulns", []))
                token = result.get("next_page_token")
                if token:
                    next_pending.append({**query, "page_token": token})
                    next_owners.append(purl)
            pending, owners = next_pending, next_owners
    return {p: sorted(set(ids)) for p, ids in hits.items() if ids}


def osv_records(ids, user_agent):
    return {i: http_json(f"{OSV_URL}/vulns/{quote(i, safe='')}", user_agent) for i in sorted(ids)}


def latest_release_date(purl, user_agent):
    name, _ = core.purl_name_version(purl)
    if purl.startswith("pkg:pypi/"):
        doc = http_json(f"{PYPI_URL}/{quote(name, safe='')}/json", user_agent)
        urls = doc.get("urls") or []
        return core.parse_iso_date(urls[0].get("upload_time_iso_8601")) if urls else None
    doc = http_json(f"{NPM_URL}/{quote(name, safe='')}", user_agent)
    latest = doc.get("dist-tags", {}).get("latest")
    return core.parse_iso_date(doc.get("time", {}).get(latest))


# --- main ------------------------------------------------------------------

def build_sboms(root, errors):
    """Export every lockfile; write sbom/. Returns the exported ones."""
    locks = find_lockfiles(root)
    if not locks:
        errors.append("no uv.lock or package-lock.json found; nothing was checked")
        return []
    missing = [p for p in locks if not (root / p).exists()]
    if missing:
        errors.append(f"tracked lockfile missing on disk (deleted but not git rm-ed?): {', '.join(missing)}")
        return []
    names, collisions = core.sbom_names(locks)
    if collisions:
        errors += [f"{a} and {b} would both be written to sbom/{name}" for name, a, b in collisions]
        return []

    sbom_dir = root / "sbom"
    sbom_dir.mkdir(exist_ok=True)
    for old in sbom_dir.glob("*.cdx.json"):
        if old.name not in names.values():
            old.unlink()

    built = []
    for lock_path in locks:
        try:
            full, runtime = export_sbom(root, lock_path)
        except StepFailed as e:
            errors.append(str(e))
            continue
        write_if_changed(sbom_dir / names[lock_path], core.stable_sbom(full))
        built.append({
            "name": names[lock_path], "lockfile": lock_path, "packages": core.packages(full),
            "direct": core.direct(full), "dev": core.dev_flags(full, runtime),
        })
    return built


def lookup_vulnerabilities(purls, user_agent, errors):
    try:
        hits = osv_hits(purls, user_agent)
        return hits, osv_records({i for ids in hits.values() for i in ids}, user_agent)
    except (*NETWORK_ERRORS, StepFailed) as e:
        errors.append(f"OSV lookup failed: {e}")
        return {}, {}


def lookup_release_dates(purls, user_agent, errors):
    dates = {}
    for purl in purls:
        try:
            dates[core.purl_base(purl)] = latest_release_date(purl, user_agent)
        except NETWORK_ERRORS as e:
            errors.append(f"latest release of {purl} could not be read: {e}")
    return dates


def main():
    """Any unexpected exception becomes a failed step: traceback on stderr, the
    report still written, exit 2 (never the interpreter's exit 1, which means
    a gating vulnerability)."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    errors = []
    try:
        root = find_root()
    except StepFailed as e:
        print(f"deps audit: {e}", file=sys.stderr)
        return 2
    user_agent = f"{root.name}-deps-audit"
    today = date.today()

    built, rows, stale_rows, all_purls = [], [], [], []
    try:
        built = build_sboms(root, errors)
        all_purls = sorted({p for s in built for p in s["packages"]})
        all_direct = sorted({p for s in built for p in s["direct"]})

        hits, records = lookup_vulnerabilities(all_purls, user_agent, errors) if all_purls else ({}, {})
        for s in built:
            for f in core.findings(hits, records, s["packages"]):
                rows.append({**f, "sbom": s["name"], "scope": "dev" if f["purl"] in s["dev"] else "runtime"})

        dates = lookup_release_dates(all_direct, user_agent, errors) if all_direct else {}
        stale_rows = core.stale([p for p in all_direct if core.purl_base(p) in dates], dates, today)
    except Exception as e:  # noqa: BLE001 - deliberate catch-all, see docstring
        traceback.print_exc()
        errors.append(f"unexpected {type(e).__name__} in the audit, results are incomplete: {e}")

    sboms = [{"name": s["name"], "lockfile": s["lockfile"], "libraries": len(s["packages"]),
              "direct": len(s["direct"])} for s in built]
    scratch = root / "scratch"
    code = core.exit_code(rows, errors)
    try:
        report = core.render_report(today, sboms, rows, stale_rows, errors)
        scratch.mkdir(exist_ok=True)
        (scratch / "dependency-report.md").write_text(report, encoding="utf-8")
    except Exception as e:  # noqa: BLE001 - disk full, file locked, or a render bug: exit 2, not 1
        print(f"deps audit: writing the report failed ({type(e).__name__}: {e})", file=sys.stderr)
        errors.append(f"the report could not be written: {e}")
        code = 2
    print(f"deps audit: {len(built)} SBOM(s), {len(all_purls)} libraries, {len(rows)} vulnerabilities, "
          f"{len(stale_rows)} stale/unknown direct dependencies, {len(errors)} failed step(s)")
    for e in errors:
        print(f"  FAILED: {e}")
    for r in rows:
        print(f"  {r['severity'].upper():8} {r['library']} {r['version']} {core.finding_id(r)} "
              f"fixed in {', '.join(r['fixed']) or '-'} [{r['sbom']}, {r['scope']}]")
    print(f"  report: {scratch / 'dependency-report.md'}; exit code {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())
