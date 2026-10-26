"""tooling/changelog/release_changelog.py (S048 § 1.2).

The pure core with plain text; the shell once, with the Claude CLI absent and git stubbed, in a
temp folder.  No test calls the real Claude CLI."""

import sys
from pathlib import Path

CHANGELOG_DIR = Path(__file__).resolve().parent.parent / "changelog"
sys.path.insert(0, str(CHANGELOG_DIR))

import release_changelog as rc  # noqa: E402

SHA = "a" * 40
OTHER = "b" * 40
TITLE = "# What changed in Yantra\n"


# --- insert_section ---------------------------------------------------------------------------

def test_insert_section_after_the_title():
    text = f"{TITLE}\n## 0.1.10 — 25-10-2026\n- Old.\n"
    out = rc.insert_section(text, "0.1.11", "27-10-2026", ["- New."])
    assert out == (f"{TITLE}\n## 0.1.11 — 27-10-2026\n- New.\n\n"
                   "## 0.1.10 — 25-10-2026\n- Old.\n")


def test_insert_section_with_no_title_goes_to_the_top():
    out = rc.insert_section("## 0.1.10 — 25-10-2026\n- Old.\n", "0.1.11", "27-10-2026", ["- New."])
    assert out.startswith("## 0.1.11 — 27-10-2026\n- New.\n\n## 0.1.10")


def test_insert_section_into_an_empty_file():
    assert rc.insert_section("", "0.1.11", "27-10-2026", ["- New."]) == "## 0.1.11 — 27-10-2026\n- New.\n"


def test_insert_section_with_no_items_is_a_heading_only():
    out = rc.insert_section(TITLE, "0.1.11", "27-10-2026", [])
    assert out == f"{TITLE}\n## 0.1.11 — 27-10-2026\n"


# --- notes_for_head ---------------------------------------------------------------------------

def test_notes_for_head_with_the_matching_sha():
    text = f"<!-- commit {SHA} -->\n- One.\nnot an item\n- Two.\n"
    assert rc.notes_for_head(text, SHA) == ["- One.", "- Two."]


def test_notes_for_head_for_another_commit_is_none():
    assert rc.notes_for_head(f"<!-- commit {OTHER} -->\n- One.\n", SHA) is None


def test_notes_for_head_with_no_sha_line_is_none():
    assert rc.notes_for_head("- One.\n", SHA) is None
    assert rc.notes_for_head("", SHA) is None


# --- clean_items ------------------------------------------------------------------------------

def test_clean_items_keeps_only_bullet_lines():
    assert rc.clean_items("Here are the notes:\n\n- One.\n  - Two. \nend") == ["- One.", "- Two."]


def test_clean_items_of_empty_output_is_empty():
    assert rc.clean_items("") == []


# --- the shell --------------------------------------------------------------------------------

def test_without_claude_or_notes_file_an_empty_section_is_written_and_exit_is_0(tmp_path, monkeypatch, capsys):
    (tmp_path / "VERSION").write_text("0.1.11\n", encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(TITLE, encoding="utf-8")
    monkeypatch.setattr(rc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rc, "CHANGELOG", changelog)
    monkeypatch.setattr(rc, "NOTES_FILE", tmp_path / "scratch" / "release-notes.md")
    monkeypatch.setattr(rc.shutil, "which", lambda _name: None)
    monkeypatch.setattr(rc, "head_sha", lambda: SHA)
    monkeypatch.setattr(rc, "commit_list", lambda: "commit abc\nA change\n")
    added = []
    monkeypatch.setattr(rc, "_git", lambda *args: added.append(args) or type(
        "R", (), {"returncode": 0, "stdout": "", "stderr": ""})())

    assert rc.main() == 0

    text = changelog.read_text(encoding="utf-8")
    assert text.startswith(f"{TITLE}\n## 0.1.11 — ")
    assert text.rstrip().endswith(text.splitlines()[2].rstrip())  # the heading is the last line
    assert ("add", "CHANGELOG.md") in added
    assert "Claude CLI not found" in capsys.readouterr().out


# --- choose_items and ask_claude (subprocess.run patched; the real CLI is never called) -------

class Done:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def shell(tmp_path, monkeypatch, run=None, notes_bytes=None):
    """Point the module at a temp folder; `run` replaces subprocess.run for the Claude call."""
    notes = tmp_path / "scratch" / "release-notes.md"
    if notes_bytes is not None:
        notes.parent.mkdir()
        notes.write_bytes(notes_bytes)
    monkeypatch.setattr(rc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rc, "NOTES_FILE", notes)
    monkeypatch.setattr(rc, "head_sha", lambda: SHA)
    monkeypatch.setattr(rc, "commit_list", lambda: "commit abc\nA change\n")
    monkeypatch.setattr(rc.shutil, "which", lambda _name: "claude")
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        if isinstance(run, Exception):
            raise run
        return run

    monkeypatch.setattr(rc.subprocess, "run", fake_run)
    return calls


def test_claude_success_keeps_only_the_bullet_lines(tmp_path, monkeypatch):
    calls = shell(tmp_path, monkeypatch, Done(0, "Here you go:\n- One.\n- Two.\nBye\n"))
    assert rc.choose_items() == (["- One.", "- Two."], "from Claude")
    assert calls[0][1]["input"] == "commit abc\nA change\n"


def test_claude_is_run_as_the_pre_flight_skill_from_the_repo_root(tmp_path, monkeypatch):
    calls = shell(tmp_path, monkeypatch, Done(0, "- One.\n"))
    rc.choose_items()
    args, kwargs = calls[0]
    assert args[0] == ["claude", "-p", "/pre-flight notes unattended", "--model", "sonnet",
                       "--tools", "Read", "--strict-mcp-config", "--no-session-persistence"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["input"] == "commit abc\nA change\n"
    assert kwargs["timeout"] == 300 == rc.CLAUDE_TIMEOUT_S


def test_claude_timeout_gives_an_empty_section_with_the_reason(tmp_path, monkeypatch):
    shell(tmp_path, monkeypatch, rc.subprocess.TimeoutExpired("claude", 300))
    items, source = rc.choose_items()
    assert items == [] and "timed out" in source


def test_claude_failing_exit_is_not_turned_into_items(tmp_path, monkeypatch):
    shell(tmp_path, monkeypatch, Done(1, "- Please run /login\n"))
    items, source = rc.choose_items()
    assert items == [] and "exit 1" in source


def test_claude_that_cannot_start_gives_an_empty_section(tmp_path, monkeypatch):
    shell(tmp_path, monkeypatch, OSError("no such file"))
    items, source = rc.choose_items()
    assert items == [] and "could not start" in source


def test_claude_output_with_no_bullet_gives_an_empty_section(tmp_path, monkeypatch):
    shell(tmp_path, monkeypatch, Done(0, "Nothing changed.\n"))
    assert rc.choose_items() == ([], "empty section: Claude gave no items")


def test_notes_file_for_head_is_used_and_claude_is_not_called(tmp_path, monkeypatch):
    calls = shell(tmp_path, monkeypatch, Done(0, "- Claude.\n"),
                  notes_bytes=f"<!-- commit {SHA} -->\n- Note.\n".encode())
    assert rc.choose_items() == (["- Note."], "from pre-flight")
    assert calls == []


def test_notes_file_for_another_commit_is_not_used(tmp_path, monkeypatch, capsys):
    shell(tmp_path, monkeypatch, Done(0, "- Claude.\n"),
          notes_bytes=f"<!-- commit {OTHER} -->\n- Note.\n".encode())
    assert rc.choose_items() == (["- Claude."], "from Claude")
    assert f"for commit {OTHER[:7]}, not HEAD; not used" in capsys.readouterr().out


def test_notes_file_that_is_not_utf8_is_skipped(tmp_path, monkeypatch, capsys):
    shell(tmp_path, monkeypatch, Done(0, "- Claude.\n"), notes_bytes=b"- Caf\xe9 \x97 item\n")
    assert rc.choose_items() == (["- Claude."], "from Claude")
    assert "cannot be read" in capsys.readouterr().out


def test_main_prints_the_items_it_wrote(tmp_path, monkeypatch, capsys):
    shell(tmp_path, monkeypatch, Done(0, "- One.\n"))
    (tmp_path / "VERSION").write_text("0.1.11\n", encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(TITLE, encoding="utf-8")
    monkeypatch.setattr(rc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rc, "CHANGELOG", changelog)
    monkeypatch.setattr(rc, "_git", lambda *args: Done())
    assert rc.main() == 0
    out = capsys.readouterr().out
    assert "from Claude (1 item)" in out and "  - One." in out


def test_main_prints_a_plural_count_for_two_items(tmp_path, monkeypatch, capsys):
    shell(tmp_path, monkeypatch, Done(0, "- One.\n- Two.\n"))
    (tmp_path / "VERSION").write_text("0.1.11\n", encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(TITLE, encoding="utf-8")
    monkeypatch.setattr(rc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rc, "CHANGELOG", changelog)
    monkeypatch.setattr(rc, "_git", lambda *args: Done())
    assert rc.main() == 0
    assert "from Claude (2 items)" in capsys.readouterr().out
