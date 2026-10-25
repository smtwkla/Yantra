"""tooling/roadmap/render_mockups.mjs: a roadmap's mock-ups become PNG screenshots (25-10-2026).
Runs the real script on two tiny mock-ups; skipped where Node or the browser tests' Chromium is
missing (a fresh checkout before the first e2e run)."""
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tooling" / "roadmap" / "render_mockups.mjs"

needs_node = pytest.mark.skipif(
    shutil.which("node") is None or not (ROOT / "frontend" / "node_modules" / "playwright").exists(),
    reason="Node or frontend/node_modules/playwright is missing")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", head[16:24])


def run(*args):
    return subprocess.run(["node", str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, timeout=120)


@needs_node
def test_phone_and_desktop_mockups_render_at_their_sizes(tmp_path):
    (tmp_path / "a-phone.html").write_text(
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="mockup-viewport" content="phone"></head><body>Today\'s jobs</body></html>')
    (tmp_path / "b-desktop.html").write_text(
        '<html><head><meta name="mockup-viewport" content="desktop"></head><body>PM report</body></html>')
    result = run(str(tmp_path))
    if result.returncode != 0 and "Executable doesn't exist" in result.stdout + result.stderr:
        pytest.skip("the browser tests' Chromium is not installed yet")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 of 2 mock-ups rendered." in result.stdout
    width, _ = png_size(tmp_path / "a-phone.png")
    assert width == 412 * 2                     # phone: 412 px at scale 2
    width, _ = png_size(tmp_path / "b-desktop.png")
    assert width == 1366


@needs_node
def test_a_folder_without_mockups_says_so(tmp_path):
    result = run(str(tmp_path))
    assert result.returncode == 1
    assert "No .html mock-ups" in result.stdout


@needs_node
def test_no_folder_named_says_how_to_call_it():
    result = run()
    assert result.returncode == 1
    assert "Name the mock-up folder" in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is missing")
def test_playwright_missing_says_so(tmp_path):
    """S057: in a repo without frontend/node_modules/playwright the script explains instead of throwing."""
    script = tmp_path / "tooling" / "roadmap" / "render_mockups.mjs"
    script.parent.mkdir(parents=True)
    script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    (mockups / "a.html").write_text("<html><body>x</body></html>")
    result = subprocess.run(["node", str(script), str(mockups)], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert result.returncode == 1
    assert "Playwright is not installed in frontend/." in result.stdout
