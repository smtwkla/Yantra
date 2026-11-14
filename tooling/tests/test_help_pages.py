"""The Help page of help/ (S103): one gallery app, `help` (published at /yantra/help/).

The pages are plain HTML published by SMTW's gallery, so a broken picture, a link to a missing slide or a
URL that points outside the app is found here, not by a user.  The rules of the gallery's app contract
(docs/SMTW-Utils-Gallery.md in the Gallery repo, § 2-§ 5) are checked in part: the manifest's keys, the file
names and sizes, relative URLs.  The collector checks all of them again before it publishes."""
import re
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

HELP = Path(__file__).resolve().parents[2] / "help"
APP = "help"
ACCESS = {"client": "vel-yantra-master", "roles": ["maintenance_team", "it_admin"]}
PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
EXTENSIONS = {"html", "htm", "js", "mjs", "css", "json", "csv", "txt", "md", "svg", "png", "jpg", "jpeg", "gif",
              "webp", "avif", "ico", "pdf"}
MB = 1024 * 1024
MAX_FILE, MAX_APP = 25 * MB, 50 * MB


class Page(HTMLParser):
    """The ids, the section ids, the picture tags and every link of one page."""

    def __init__(self, text):
        super().__init__()
        self.ids, self.section_ids, self.images, self.links = [], [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
            if tag == "section":
                self.section_ids.append(attrs["id"])
        if tag == "img":
            self.images.append(attrs)
        for key in ("href", "src"):
            if attrs.get(key) is not None:
                self.links.append((tag, key, attrs[key]))


def read_page(app):
    return Page((HELP / app / "index.html").read_text(encoding="utf-8"))


def app_files(app):
    return [p for p in (HELP / app).rglob("*") if p.is_file()]


def test_help_has_exactly_the_one_app():
    folders = sorted(p.name for p in HELP.iterdir() if p.is_dir())
    assert folders == [APP]


def test_manifest_has_the_agreed_keys():
    manifest = tomllib.loads((HELP / APP / "gallery.toml").read_text(encoding="utf-8"))
    assert set(manifest) == {"contract", "title", "description", "access"}
    assert manifest["contract"] == 1 and isinstance(manifest["contract"], int)
    assert 1 <= len(manifest["title"].strip()) <= 80
    assert 1 <= len(manifest["description"]) <= 300
    assert manifest["access"] == ACCESS


def test_file_names_and_sizes_follow_the_contract():
    files = [p for p in app_files(APP) if p.name != "gallery.toml"]
    for path in files:
        parts = path.relative_to(HELP / APP).parts
        assert all(PART.match(part) and not part.endswith(".") for part in parts), path
        assert path.suffix[1:] in EXTENSIONS, f"{path}: the extension must be lower case and allowed"
        assert path.stat().st_size <= MAX_FILE, path
        assert all(len(part) <= 100 for part in parts), f"{path}: a name is over 100 characters"
        assert len("/".join(parts)) <= 120, f"{path}: the path below the app folder is over 120 characters"
    assert sum(p.stat().st_size for p in files) <= MAX_APP
    # as the collector: every folder prefix is compared too, not only whole paths
    spellings = {}
    for path in files:
        parts = path.relative_to(HELP / APP).parts
        for end in range(1, len(parts) + 1):
            prefix = "/".join(parts[:end])
            spellings.setdefault(prefix.lower(), set()).add(prefix)
    clashes = sorted(sorted(names) for names in spellings.values() if len(names) > 1)
    assert not clashes, f"paths that differ only in capitals: {clashes}"


def test_every_url_is_relative_and_stays_in_the_app():
    for tag, key, url in read_page(APP).links:
        parts = urlsplit(url)
        assert not parts.scheme and not parts.netloc, f"<{tag} {key}={url!r}> names another site"
        assert not url.startswith("/"), f"<{tag} {key}={url!r}> starts with / (outside the app)"
        assert not url.startswith("../"), f"<{tag} {key}={url!r}> leaves the app (one app since 15-11-2026)"
        assert "_blob" not in url and "claude.ai" not in url


def test_every_picture_exists_has_an_alt_and_is_used():
    page = read_page(APP)
    named = {Path(img["src"]) for img in page.images}
    for img in page.images:
        assert (HELP / APP / img["src"]).is_file(), f"{img['src']} is not a file"
        assert img.get("alt", "").strip(), f"{img['src']} has no alt text"
    shots = {p.relative_to(HELP / APP) for p in (HELP / APP / "shots").glob("*")}
    assert shots - named == set(), "pictures no slide uses"


def test_section_ids_are_unique():
    page = read_page(APP)
    assert len(page.ids) == len(set(page.ids)), "an id is used twice"
    assert page.section_ids


def test_every_section_link_names_a_section():
    page = read_page(APP)
    for _tag, key, url in page.links:
        parts = urlsplit(url)
        if key == "href" and parts.fragment:
            assert not parts.path, f"{url!r} names another page"
            assert parts.fragment in page.ids, f"#{parts.fragment} is not a section"


def test_the_contents_name_every_section_and_the_onboarding_and_documents_slides():
    page = read_page(APP)
    hrefs = {url for _tag, key, url in page.links if key == "href"}
    assert {"#contents", "#mt1", "#d1"} <= hrefs
    assert {"contents", "mt1", "d1"} <= set(page.section_ids)
