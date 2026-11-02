"""The Help pages of help/ (S103): the three gallery apps `home`, `guide` and `documents`.

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
APPS = ("home", "guide", "documents")
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


def test_help_has_exactly_the_three_apps():
    folders = sorted(p.name for p in HELP.iterdir() if p.is_dir())
    assert folders == sorted(APPS)


@pytest.mark.parametrize("app", APPS)
def test_manifest_has_the_agreed_keys(app):
    manifest = tomllib.loads((HELP / app / "gallery.toml").read_text(encoding="utf-8"))
    assert set(manifest) == {"contract", "title", "description", "access"}
    assert manifest["contract"] == 1 and isinstance(manifest["contract"], int)
    assert 1 <= len(manifest["title"].strip()) <= 80
    assert 1 <= len(manifest["description"]) <= 300
    assert manifest["access"] == ACCESS


@pytest.mark.parametrize("app", APPS)
def test_file_names_and_sizes_follow_the_contract(app):
    files = [p for p in app_files(app) if p.name != "gallery.toml"]
    for path in files:
        parts = path.relative_to(HELP / app).parts
        assert all(PART.match(part) and not part.endswith(".") for part in parts), path
        assert path.suffix[1:] in EXTENSIONS, f"{path}: the extension must be lower case and allowed"
        assert path.stat().st_size <= MAX_FILE, path
        assert all(len(part) <= 100 for part in parts), f"{path}: a name is over 100 characters"
        assert len("/".join(parts)) <= 120, f"{path}: the path below the app folder is over 120 characters"
    assert sum(p.stat().st_size for p in files) <= MAX_APP
    # as the collector: every folder prefix is compared too, not only whole paths
    spellings = {}
    for path in files:
        parts = path.relative_to(HELP / app).parts
        for end in range(1, len(parts) + 1):
            prefix = "/".join(parts[:end])
            spellings.setdefault(prefix.lower(), set()).add(prefix)
    clashes = sorted(sorted(names) for names in spellings.values() if len(names) > 1)
    assert not clashes, f"{app}: paths that differ only in capitals: {clashes}"


@pytest.mark.parametrize("app", APPS)
def test_every_url_is_relative_and_stays_in_the_gallery(app):
    for tag, key, url in read_page(app).links:
        parts = urlsplit(url)
        assert not parts.scheme and not parts.netloc, f"{app}: <{tag} {key}={url!r}> names another site"
        assert not url.startswith("/"), f"{app}: <{tag} {key}={url!r}> starts with / (outside the app)"
        assert "_blob" not in url and "claude.ai" not in url


@pytest.mark.parametrize("app", ("guide", "documents"))
def test_every_picture_exists_has_an_alt_and_is_used(app):
    page = read_page(app)
    named = {Path(img["src"]) for img in page.images}
    for img in page.images:
        assert (HELP / app / img["src"]).is_file(), f"{app}: {img['src']} is not a file"
        assert img.get("alt", "").strip(), f"{app}: {img['src']} has no alt text"
    shots = {p.relative_to(HELP / app) for p in (HELP / app / "shots").glob("*")}
    assert shots - named == set(), f"{app}: pictures no page uses"


@pytest.mark.parametrize("app", ("guide", "documents"))
def test_section_ids_are_unique(app):
    page = read_page(app)
    assert len(page.ids) == len(set(page.ids)), "an id is used twice"
    assert page.section_ids


def targets_of(app):
    """(page, id) pairs: each link that names a section, in this page or in the guide."""
    pairs = []
    for _tag, key, url in read_page(app).links:
        parts = urlsplit(url)
        if key == "href" and parts.fragment:
            page = {"": app, "../guide/": "guide", "../documents/": "documents"}.get(parts.path)
            assert page, f"{app}: {url!r} points at a page this test does not know"
            pairs.append((page, parts.fragment))
    return pairs


@pytest.mark.parametrize("app", APPS)
def test_every_section_link_names_a_section(app):
    for page, fragment in targets_of(app):
        assert fragment in read_page(page).ids, f"{app}: #{fragment} is not in {page}"


def test_the_home_links_to_the_guide_and_to_documents_and_the_onboarding_section():
    hrefs = {url for _tag, key, url in read_page("home").links if key == "href"}
    assert {"../guide/", "../guide/#mt1", "../documents/"} <= hrefs
    assert "mt1" in read_page("guide").section_ids


def test_every_folder_a_link_names_has_its_entry_page():
    for app in APPS:
        for _tag, key, url in read_page(app).links:
            parts = urlsplit(url)
            if key == "href" and parts.path.startswith("../"):
                assert (HELP / app / parts.path / "index.html").resolve().is_file(), f"{app}: {url!r}"
