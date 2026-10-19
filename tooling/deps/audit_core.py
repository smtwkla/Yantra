"""Pure core of the dependency audit (S022): plain data in, plain data out.

No network, no file or clock access, no names of any project: `today` is passed
in. The shell (audit.py) fetches the inputs and calls these functions.
"""
import copy
from datetime import date
from urllib.parse import unquote

STALE_AFTER_DAYS = 365
GATING_SEVERITIES = ("critical", "high", "unknown")
# Highest rank wins when advisories of one finding disagree.
SEVERITY_RANK = {"unknown": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}
NPM_DEV_PROPERTY = "cdx:npm:package:development"

UV_LOCK = "uv.lock"
NPM_LOCK = "package-lock.json"


# --- SBOM documents -------------------------------------------------------

def stable_sbom(doc):
    """Same lockfile, same bytes: drop what changes between runs, sort components."""
    out = copy.deepcopy(doc)
    out.pop("serialNumber", None)
    metadata = out.get("metadata", {})
    metadata.pop("timestamp", None)
    metadata.pop("tools", None)
    if "components" in out:
        out["components"] = sorted(out["components"], key=lambda c: c.get("bom-ref", ""))
    return out


def check_spec(doc):
    """None when the document is CycloneDX 1.5, else a message saying what it is."""
    fmt, version = doc.get("bomFormat"), doc.get("specVersion")
    if fmt != "CycloneDX" or version != "1.5":
        return f"expected CycloneDX 1.5, got {fmt} {version}"
    return None


def packages(doc):
    """Sorted, unique purls of the libraries in the document."""
    return sorted({c["purl"] for c in doc.get("components", []) if c.get("purl")})


def _purl_by_ref(doc):
    return {c["bom-ref"]: c["purl"] for c in doc.get("components", []) if c.get("purl") and c.get("bom-ref")}


def direct(doc):
    """Purls the project itself depends on (the root component's dependsOn)."""
    root_ref = doc.get("metadata", {}).get("component", {}).get("bom-ref")
    by_ref = _purl_by_ref(doc)
    for entry in doc.get("dependencies", []):
        if entry.get("ref") == root_ref:
            return sorted({by_ref[r] for r in entry.get("dependsOn", []) if r in by_ref})
    return []


def dev_flags(full_doc, runtime_doc=None):
    """Purls that are development-only.

    With a runtime export (uv: `--no-dev`) they are the purls only in the full
    export, compared by purl because uv renumbers bom-refs between exports.
    Without one (npm) the exporter's own development property decides.
    """
    if runtime_doc is not None:
        return set(packages(full_doc)) - set(packages(runtime_doc))
    return {
        c["purl"]
        for c in full_doc.get("components", [])
        if c.get("purl")
        and any(p.get("name") == NPM_DEV_PROPERTY and p.get("value") == "true" for p in c.get("properties", []))
    }


# --- Lockfile names -------------------------------------------------------

def sbom_name(lock_path, other_locks_in_folder=()):
    """File name of the SBOM of a lockfile, e.g. 'backend/uv.lock' -> 'backend.cdx.json'.

    `other_locks_in_folder`: the other lockfile paths in the same folder; when
    there are any, '-py' / '-npm' tells the two kinds apart.
    """
    parts = lock_path.split("/")
    folder = "-".join(parts[:-1]) or "root"
    if other_locks_in_folder:
        folder += "-py" if parts[-1] == UV_LOCK else "-npm"
    return f"{folder}.cdx.json"


def sbom_names(lock_paths):
    """({lock_path: file name}, [(name, path_a, path_b)] for names given twice)."""
    by_folder = {}
    for path in lock_paths:
        by_folder.setdefault(path.rpartition("/")[0], []).append(path)
    names, owner, collisions = {}, {}, []
    for path in lock_paths:
        others = [p for p in by_folder[path.rpartition("/")[0]] if p != path]
        name = sbom_name(path, others)
        if name in owner:
            collisions.append((name, owner[name], path))
            continue
        owner[name] = path
        names[path] = name
    return names, collisions


# --- Vulnerabilities (OSV) ------------------------------------------------

def purl_base(purl):
    """'pkg:pypi/flask@3.1.2' -> 'pkg:pypi/flask'."""
    return purl.rpartition("@")[0] if "@" in purl else purl


def purl_name_version(purl):
    base, _, version = purl.rpartition("@")
    return unquote(base.split("/", 1)[1]), version


def _cves(record):
    return {a for a in [record["id"], *record.get("aliases", [])] if a.startswith("CVE-")}


def _severity(record):
    value = (record.get("database_specific") or {}).get("severity")
    return value.lower() if value and value.lower() in SEVERITY_RANK else "unknown"


def _fixed_versions(record, base):
    """Every `fixed` event of the affected entries for this package, in order found."""
    entries = record.get("affected", [])
    matching = [a for a in entries if (a.get("package", {}).get("purl") or "").lower() == base.lower()]
    fixed = []
    for entry in matching or entries:
        for rng in entry.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event and event["fixed"] not in fixed:
                    fixed.append(event["fixed"])
    return fixed


def _group(records):
    """Group records that share a CVE; a record without a CVE stands alone."""
    groups = []  # each: {"cves": set, "records": list}
    for record in records:
        cves = _cves(record)
        overlapping = [g for g in groups if cves and g["cves"] & cves]
        merged = {"cves": set(cves), "records": [record]}
        for g in overlapping:
            merged["cves"] |= g["cves"]
            merged["records"] = g["records"] + merged["records"]
            groups.remove(g)
        groups.append(merged)
    return groups


def findings(hits, records, purls):
    """One finding per library and weakness.

    hits: {purl: [advisory ids]} as OSV returned them; records: {id: OSV record};
    purls: the libraries to report (those of one SBOM). Withdrawn records are skipped.
    """
    out = []
    for purl in purls:
        found = [records[i] for i in hits.get(purl, []) if i in records and not records[i].get("withdrawn")]
        name, version = purl_name_version(purl)
        for group in _group(found):
            recs = group["records"]
            severity = max((_severity(r) for r in recs), key=SEVERITY_RANK.get)
            fixed = []
            for r in recs:
                fixed += [v for v in _fixed_versions(r, purl_base(purl)) if v not in fixed]
            out.append({
                "library": name,
                "version": version,
                "purl": purl,
                "cve": sorted(group["cves"])[0] if group["cves"] else None,
                "cves": sorted(group["cves"]),
                "ids": sorted({r["id"] for r in recs}),
                "severity": severity,
                "fixed": fixed,
            })
    return sorted(out, key=lambda f: (-SEVERITY_RANK[f["severity"]], f["library"], f["ids"]))


# --- Maintenance ----------------------------------------------------------

def stale(direct_deps, latest_dates, today):
    """Direct dependencies with no release for over 365 days, or with no known date.

    direct_deps: purls; latest_dates: {purl base: date or None}; today: date.
    """
    out = []
    for purl in direct_deps:
        name, version = purl_name_version(purl)
        latest = latest_dates.get(purl_base(purl))
        if latest is None:
            out.append({"library": name, "version": version, "latest": None, "days": None, "status": "unknown"})
            continue
        days = (today - latest).days
        if days > STALE_AFTER_DAYS:
            out.append({"library": name, "version": version, "latest": latest, "days": days, "status": "stale"})
    return sorted(out, key=lambda s: s["library"])


def parse_iso_date(text):
    """'2026-10-13T07:47:23.649Z' -> date; None for a missing or unreadable value."""
    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


# --- Result ---------------------------------------------------------------

def exit_code(rows, errors):
    """2 when any step failed, 1 when any finding is critical, high or unknown, else 0."""
    if errors:
        return 2
    return 1 if any(r["severity"] in GATING_SEVERITIES for r in rows) else 0


def finding_id(row):
    """The CVE, or the first advisory id when the finding has no CVE."""
    return row["cve"] or row["ids"][0]


def pair_batch_results(owners, results):
    """[(owner, result)] for an OSV batch answer. A different count means the
    answer cannot be matched to the queries, so raise rather than let a library
    pass as clean without having been checked."""
    if len(owners) != len(results):
        raise ValueError(f"OSV answered {len(results)} results for {len(owners)} queries")
    return list(zip(owners, results))


def render_report(today, sboms, rows, stale_rows, errors):
    """Markdown report. sboms: [{name, lockfile, libraries, direct}]; rows: findings
    with 'sbom' and 'scope' added; stale_rows: stale() output; errors: [str]."""
    lines = [f"# Dependency report, {today.isoformat()}", ""]
    code = exit_code(rows, errors)
    lines += [f"Result: exit code {code} "
              f"({'check incomplete' if code == 2 else 'gating vulnerabilities' if code == 1 else 'clean'}).", ""]
    if errors:
        lines += ["## Steps that failed", ""] + [f"- {e}" for e in errors] + [""]
    lines += ["## Libraries checked", "", "| SBOM | Lockfile | Libraries | Direct |", "|---|---|---|---|"]
    lines += [f"| {s['name']} | {s['lockfile']} | {s['libraries']} | {s['direct']} |" for s in sboms]
    lines += ["", "## Known vulnerabilities", ""]
    if rows:
        lines += ["| Severity | Library | Version | CVE | Advisories | Fixed in | SBOM | Scope |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(
                f"| {r['severity']} | {r['library']} | {r['version']} | {finding_id(r)} | "
                f"{', '.join(r['ids'])} | {', '.join(r['fixed']) or '-'} | {r['sbom']} | {r['scope']} |")
    else:
        lines.append("None found.")
    lines += ["", "## Direct dependencies without a release in 12 months (not gating)", ""]
    if stale_rows:
        lines += ["| Library | Version | Latest release | Days |", "|---|---|---|---|"]
        for s in stale_rows:
            if s["status"] == "unknown":
                lines.append(f"| {s['library']} | {s['version']} | release date unknown | |")
            else:
                lines.append(f"| {s['library']} | {s['version']} | {s['latest'].isoformat()} | {s['days']} |")
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
