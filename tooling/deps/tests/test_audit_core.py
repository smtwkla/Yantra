"""Tests of the pure core. Fixtures in tests/fixtures are real responses:

- osv-*.json, osv-querybatch-flask.json: api.osv.dev, recorded 18-10-2026;
- uv-backend*.cdx.json: `uv export` of Yantra's backend lockfile (full and --no-dev);
- npm-frontend.cdx.json: `npm sbom` of the frontend lockfile, cut down to its
  direct dependencies plus a few others;
- pypi-flask.json, npm-vue-shared.json: the registry answers, cut down to the
  fields the audit reads.
"""
import copy
import json
from datetime import date
from pathlib import Path

import pytest

import audit_core as core

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 18)
FLASK_OLD = "pkg:pypi/flask@0.12"
FLASK_NEW = "pkg:pypi/flask@3.1.2"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def osv(*ids):
    return {i: load(f"osv-{i}.json") for i in ids}


def has(purls, prefix):
    return any(p.startswith(prefix) for p in purls)


@pytest.fixture
def uv_full():
    return load("uv-backend.cdx.json")


@pytest.fixture
def uv_runtime():
    return load("uv-backend-nodev.cdx.json")


@pytest.fixture
def npm_doc():
    return load("npm-frontend.cdx.json")


# --- stable_sbom / check_spec ---

def test_stable_sbom_removes_volatile_fields(uv_full, npm_doc):
    for doc in (uv_full, npm_doc):
        out = core.stable_sbom(doc)
        assert "serialNumber" not in out
        assert "timestamp" not in out["metadata"]
        assert "tools" not in out["metadata"]
        assert out["metadata"]["component"] == doc["metadata"]["component"]


def test_stable_sbom_same_bytes_whatever_the_run(uv_full):
    other = copy.deepcopy(uv_full)
    other["serialNumber"] = "urn:uuid:00000000-0000-0000-0000-000000000000"
    other["metadata"]["timestamp"] = "2030-01-01T00:00:00Z"
    other["metadata"]["tools"][0]["version"] = "9.9.9"
    other["components"].reverse()

    def dump(d):
        return json.dumps(core.stable_sbom(d), indent=2)

    assert dump(uv_full) == dump(other)


def test_stable_sbom_sorts_components_and_leaves_input_alone(npm_doc):
    npm_doc["components"].reverse()
    before = copy.deepcopy(npm_doc)
    refs = [c["bom-ref"] for c in core.stable_sbom(npm_doc)["components"]]
    assert refs == sorted(refs)
    assert npm_doc == before


def test_check_spec(uv_full):
    assert core.check_spec(uv_full) is None
    assert "1.6" in core.check_spec({**uv_full, "specVersion": "1.6"})
    assert core.check_spec({**uv_full, "bomFormat": "SPDX"})


# --- packages / direct / dev ---

def test_packages_uv_and_npm(uv_full, npm_doc):
    assert "pkg:pypi/blinker@1.9.0" in core.packages(uv_full)
    assert has(core.packages(npm_doc), "pkg:npm/%40vue/shared@")
    assert core.packages(uv_full) == sorted(set(core.packages(uv_full)))


def test_direct_uv_and_npm(uv_full, npm_doc):
    d = core.direct(uv_full)
    assert has(d, "pkg:pypi/flask@")
    assert not has(d, "pkg:pypi/blinker@")  # indirect, via flask
    n = core.direct(npm_doc)
    assert has(n, "pkg:npm/vue@")
    assert not has(n, "pkg:npm/%40vue/shared@")


def test_direct_without_root_dependency_entry():
    assert core.direct({"components": []}) == []


def test_dev_flags_uv_by_purl_although_bom_refs_differ(uv_full, uv_runtime):
    refs_full = {c["bom-ref"] for c in uv_full["components"]}
    refs_runtime = {c["bom-ref"] for c in uv_runtime["components"]}
    assert refs_runtime - refs_full  # uv renumbered at least one ref
    dev = core.dev_flags(uv_full, uv_runtime)
    assert has(dev, "pkg:pypi/pytest@")
    assert not has(dev, "pkg:pypi/flask@")
    assert dev == set(core.packages(uv_full)) - set(core.packages(uv_runtime))


def test_dev_flags_npm_uses_the_property(npm_doc):
    dev = core.dev_flags(npm_doc)
    assert has(dev, "pkg:npm/vitest@")
    assert not has(dev, "pkg:npm/vue@")


# --- sbom_name / sbom_names ---

@pytest.mark.parametrize("path,others,expected", [
    ("uv.lock", [], "root.cdx.json"),
    ("backend/uv.lock", [], "backend.cdx.json"),
    ("frontend/package-lock.json", [], "frontend.cdx.json"),
    ("tools/x/uv.lock", [], "tools-x.cdx.json"),
    ("web/uv.lock", ["web/package-lock.json"], "web-py.cdx.json"),
    ("web/package-lock.json", ["web/uv.lock"], "web-npm.cdx.json"),
    ("uv.lock", ["package-lock.json"], "root-py.cdx.json"),
])
def test_sbom_name(path, others, expected):
    assert core.sbom_name(path, others) == expected


def test_sbom_names_yantra_layout():
    names, collisions = core.sbom_names(["backend/uv.lock", "frontend/package-lock.json", "uv.lock"])
    assert names == {"backend/uv.lock": "backend.cdx.json",
                     "frontend/package-lock.json": "frontend.cdx.json",
                     "uv.lock": "root.cdx.json"}
    assert collisions == []


def test_sbom_names_both_kinds_in_one_folder():
    names, collisions = core.sbom_names(["a/uv.lock", "a/package-lock.json"])
    assert names == {"a/uv.lock": "a-py.cdx.json", "a/package-lock.json": "a-npm.cdx.json"}
    assert collisions == []


def test_sbom_names_collisions_are_reported_not_overwritten():
    names, collisions = core.sbom_names(["a-b/uv.lock", "a/b/uv.lock"])
    assert collisions == [("a-b.cdx.json", "a-b/uv.lock", "a/b/uv.lock")]
    assert list(names) == ["a-b/uv.lock"]
    _, collisions = core.sbom_names(["root/uv.lock", "uv.lock"])
    assert collisions == [("root.cdx.json", "root/uv.lock", "uv.lock")]


# --- findings ---

def test_ghsa_and_pysec_with_one_cve_are_one_finding_with_the_ghsa_severity():
    records = osv("GHSA-68rp-wp8r-4726", "PYSEC-2026-2151")
    out = core.findings({FLASK_NEW: ["GHSA-68rp-wp8r-4726", "PYSEC-2026-2151"]}, records, [FLASK_NEW])
    assert len(out) == 1
    f = out[0]
    assert (f["library"], f["version"], f["cve"]) == ("flask", "3.1.2", "CVE-2026-27205")
    assert f["ids"] == ["GHSA-68rp-wp8r-4726", "PYSEC-2026-2151"]
    assert f["severity"] == "low"  # PYSEC carries none; the GHSA rating is used
    assert f["fixed"] == ["3.1.3"]


def test_severity_is_the_highest_in_the_group():
    records = osv("GHSA-562c-5r94-xh97", "PYSEC-2018-66")
    out = core.findings({FLASK_OLD: ["PYSEC-2018-66", "GHSA-562c-5r94-xh97"]}, records, [FLASK_OLD])
    assert [f["severity"] for f in out] == ["high"]


def test_pysec_alone_has_unknown_severity():
    out = core.findings({FLASK_OLD: ["PYSEC-2018-66"]}, osv("PYSEC-2018-66"), [FLASK_OLD])
    assert out[0]["severity"] == "unknown"
    assert out[0]["cve"] == "CVE-2018-1000656"


def test_advisory_without_cve_stands_alone():
    purl = "pkg:pypi/pillow@2.0.0"
    out = core.findings({purl: ["GHSA-4fx9-vc88-q2xc"]}, osv("GHSA-4fx9-vc88-q2xc"), [purl])
    assert len(out) == 1
    assert out[0]["cve"] is None
    assert out[0]["ids"] == ["GHSA-4fx9-vc88-q2xc"]


def test_withdrawn_records_are_skipped():
    purl = "pkg:pypi/pillow@2.0.0"
    records = osv("GHSA-4fx9-vc88-q2xc")
    records["GHSA-4fx9-vc88-q2xc"]["withdrawn"] = "2026-01-01T00:00:00Z"
    assert core.findings({purl: ["GHSA-4fx9-vc88-q2xc"]}, records, [purl]) == []


def test_fix_versions_over_several_ranges():
    purl = "pkg:pypi/django@1.8"
    out = core.findings({purl: ["PYSEC-2016-3"]}, osv("PYSEC-2016-3"), [purl])
    expected = [e["fixed"] for r in load("osv-PYSEC-2016-3.json")["affected"][0]["ranges"]
                for e in r["events"] if "fixed" in e]
    assert len(expected) == 2
    assert out[0]["fixed"] == expected


def test_fix_versions_come_from_the_entries_of_that_package_only():
    record = {"id": "GHSA-x", "affected": [
        {"package": {"purl": "pkg:npm/other"}, "ranges": [{"events": [{"fixed": "9.9.9"}]}]},
        {"package": {"purl": "pkg:npm/%40vue/shared"},
         "ranges": [{"events": [{"introduced": "0"}, {"fixed": "3.5.14"}]}]},
    ]}
    purl = "pkg:npm/%40vue/shared@3.5.13"
    out = core.findings({purl: ["GHSA-x"]}, {"GHSA-x": record}, [purl])
    assert out[0]["fixed"] == ["3.5.14"]
    assert out[0]["library"] == "@vue/shared"


def test_clean_package_and_package_outside_the_sbom_give_nothing():
    hits = {FLASK_NEW: ["GHSA-68rp-wp8r-4726"]}
    records = osv("GHSA-68rp-wp8r-4726")
    assert core.findings(hits, records, ["pkg:pypi/blinker@1.9.0"]) == []
    assert core.findings({}, {}, [FLASK_NEW]) == []


def test_findings_sorted_worst_first():
    hits = {FLASK_OLD: ["PYSEC-2018-66", "GHSA-562c-5r94-xh97"], FLASK_NEW: ["GHSA-68rp-wp8r-4726"]}
    records = osv("PYSEC-2018-66", "GHSA-562c-5r94-xh97", "GHSA-68rp-wp8r-4726")
    out = core.findings(hits, records, [FLASK_NEW, FLASK_OLD])
    assert [f["severity"] for f in out] == ["high", "low"]


def test_recorded_querybatch_shape():
    batch = load("osv-querybatch-flask.json")
    assert [v["id"] for v in batch["results"][1]["vulns"]] == ["GHSA-68rp-wp8r-4726", "PYSEC-2026-2151"]


# --- stale ---

def days_ago(n):
    return date.fromordinal(TODAY.toordinal() - n)


def test_stale_at_364_365_366_days_and_unknown():
    deps = ["pkg:pypi/a@1", "pkg:pypi/b@1", "pkg:pypi/c@1", "pkg:pypi/d@1"]
    dates = {"pkg:pypi/a": days_ago(364), "pkg:pypi/b": days_ago(365),
             "pkg:pypi/c": days_ago(366), "pkg:pypi/d": None}
    out = core.stale(deps, dates, TODAY)
    assert [(s["library"], s["status"], s["days"]) for s in out] == [("c", "stale", 366), ("d", "unknown", None)]


def test_stale_package_missing_from_dates_is_unknown():
    assert core.stale(["pkg:npm/%40vue/shared@1"], {}, TODAY)[0]["status"] == "unknown"


def test_latest_release_dates_from_recorded_registry_answers():
    pypi = load("pypi-flask.json")
    assert core.parse_iso_date(pypi["urls"][0]["upload_time_iso_8601"]) == date(2026, 2, 19)
    npm = load("npm-vue-shared.json")
    assert core.parse_iso_date(npm["time"][npm["dist-tags"]["latest"]]) == date(2026, 10, 13)


@pytest.mark.parametrize("text", [None, "", "not a date"])
def test_parse_iso_date_unreadable(text):
    assert core.parse_iso_date(text) is None


# --- exit_code / report ---

def test_exit_codes():
    def rows(*severities):
        return [{"severity": s} for s in severities]

    assert core.exit_code([], []) == 0
    assert core.exit_code(rows("low", "moderate"), []) == 0
    assert core.exit_code(rows("high"), []) == 1
    assert core.exit_code(rows("critical"), []) == 1
    assert core.exit_code(rows("unknown"), []) == 1
    assert core.exit_code([], ["OSV unreachable"]) == 2
    assert core.exit_code(rows("critical"), ["OSV unreachable"]) == 2


def test_render_report_lists_findings_stale_and_errors():
    rows = core.findings({FLASK_NEW: ["GHSA-68rp-wp8r-4726"]}, osv("GHSA-68rp-wp8r-4726"), [FLASK_NEW])
    rows[0].update(sbom="backend.cdx.json", scope="runtime")
    stale_rows = core.stale(["pkg:pypi/old@1"], {"pkg:pypi/old": date(2020, 1, 1)}, TODAY)
    sboms = [{"name": "backend.cdx.json", "lockfile": "backend/uv.lock", "libraries": 23, "direct": 9}]
    text = core.render_report(TODAY, sboms, rows, stale_rows, ["npm export failed"])
    for needle in ("CVE-2026-27205", "GHSA-68rp-wp8r-4726", "3.1.3", "runtime", "backend/uv.lock",
                   "old", "npm export failed", "exit code 2"):
        assert needle in text
    assert "None found." not in text


def test_render_report_when_clean():
    text = core.render_report(TODAY, [], [], [], [])
    assert "exit code 0" in text and "None found." in text


def test_report_shows_advisory_id_when_there_is_no_cve():
    row = {"severity": "high", "library": "pillow", "version": "1", "cve": None, "ids": ["GHSA-4fx9-vc88-q2xc"],
           "fixed": [], "sbom": "backend.cdx.json", "scope": "runtime"}
    assert core.finding_id(row) == "GHSA-4fx9-vc88-q2xc"
    text = core.render_report(TODAY, [], [row], [], [])
    assert "| high | pillow | 1 | GHSA-4fx9-vc88-q2xc | GHSA-4fx9-vc88-q2xc |" in text


def test_pair_batch_results_pairs_in_order():
    assert core.pair_batch_results(["a", "b"], [{"x": 1}, {}]) == [("a", {"x": 1}), ("b", {})]


@pytest.mark.parametrize("results", [[], [{}]])
def test_pair_batch_results_count_mismatch_raises(results):
    with pytest.raises(ValueError):
        core.pair_batch_results(["a", "b"], results)
