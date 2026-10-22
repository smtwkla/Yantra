"""tooling/deploy.py (S025 § 1.1, § 5.4): the schema-ready poll, the required health URL, and
the rollback lines printed on any failure after the stamp.  No network and no plink: the
opener, the clock and the remote calls are fakes."""

import http.client
import io
import json
import urllib.error

import pytest

import deploy

URL = "https://yantra.example/api/health"


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status = status
        self._body = json.dumps(body if body is not None else {"status": "ok", "schema_ready": True}).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener:
    """Answers in turn — a FakeResponse, or an exception to raise; the last one repeats."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, url, timeout):
        assert url == URL and timeout == deploy.HEALTH_REQUEST_TIMEOUT_SECONDS
        self.calls += 1
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


class Clock:
    """A clock that moves only when the poll sleeps."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def _wait(opener, clock):
    return deploy.wait_for_schema(URL, opener=opener, clock=clock, sleep=clock.sleep)


NOT_READY = FakeResponse(body={"status": "ok", "schema_ready": False})


class TestPoll:

    def test_ready_at_once(self):
        clock = Clock()
        assert _wait(Opener(FakeResponse()), clock) is True
        assert clock.sleeps == []

    def test_not_yet_then_ready(self):
        clock, opener = Clock(), Opener(NOT_READY, NOT_READY, FakeResponse())
        assert _wait(opener, clock) is True
        assert clock.sleeps == [deploy.HEALTH_POLL_SECONDS] * 2

    @pytest.mark.parametrize("first", [
        FakeResponse(status=502),
        urllib.error.HTTPError(URL, 502, "Bad Gateway", {}, io.BytesIO(b"<html>")),
        urllib.error.URLError("connection refused"),
        ConnectionResetError(),
        http.client.RemoteDisconnected("closed"),
        http.client.IncompleteRead(b"{"),
        FakeResponse(body=["not", "an", "object"]),
    ], ids=["non-200", "http-error", "connection-error", "reset", "remote-disconnected", "incomplete-read", "odd-body"])
    def test_anything_else_is_not_yet(self, first):
        clock = Clock()
        assert _wait(Opener(first, FakeResponse()), clock) is True
        assert clock.sleeps == [deploy.HEALTH_POLL_SECONDS]

    def test_gives_up_after_the_timeout(self):
        clock, opener = Clock(), Opener(NOT_READY)
        assert _wait(opener, clock) is False
        assert sum(clock.sleeps) == deploy.HEALTH_TIMEOUT_SECONDS
        assert opener.calls == deploy.HEALTH_TIMEOUT_SECONDS // deploy.HEALTH_POLL_SECONDS + 1


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(deploy, "SESSION", "ansible-ws")
    monkeypatch.setattr(deploy, "ERP_SERVER_DIR", "/srv/erp_server")
    monkeypatch.setattr(deploy, "HEALTH_URL", URL)
    monkeypatch.setattr(deploy.sys, "argv", ["deploy.py"])


class TestSettings:

    def test_the_health_url_is_required_for_a_deploy_only(self, settings, monkeypatch):
        monkeypatch.setattr(deploy, "HEALTH_URL", None)
        assert deploy.missing_settings([]) == ["DEPLOY_HEALTH_URL"]
        assert deploy.missing_settings(["--check"]) == []
        assert deploy.missing_settings(["--stamp-only"]) == []

    def test_a_missing_url_aborts_before_anything_runs(self, settings, monkeypatch, capsys):
        monkeypatch.setattr(deploy, "HEALTH_URL", None)
        monkeypatch.setattr(deploy, "run_remote", lambda cmd: pytest.fail(f"ran {cmd}"))
        assert deploy.main() == 1
        assert "ABORT: not set: DEPLOY_HEALTH_URL" in capsys.readouterr().out


class TestStampedVersion:

    @pytest.mark.parametrize("output, expected", [
        ('YANTRA_VER: "0.1.3"\n', "0.1.3"),
        ("host\nYANTRA_VER: 0.1.3\n", "0.1.3"),
        ("", None),
        ("OTHER: 1\n", None),
    ])
    def test_parse(self, output, expected):
        assert deploy.parse_stamped_version(output) == expected


class _Remote:
    def __init__(self, returncode=0, stdout=""):
        self.returncode, self.stdout = returncode, stdout


@pytest.fixture
def pipeline(settings, monkeypatch, tmp_path):
    """main() with every remote call faked -> the list of remote commands run, in order."""
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.2.0\n")
    monkeypatch.setattr(deploy, "VERSION_FILE", version_file)
    commands = []

    def run_remote(cmd):
        commands.append(cmd)
        if cmd.startswith("cd /srv/erp_server && grep"):
            return _Remote(stdout='YANTRA_VER: "0.1.3"\n')   # the read before the stamp
        return _Remote(stdout='YANTRA_VER: "0.2.0"\n')   # the stamp
    monkeypatch.setattr(deploy, "run_remote", run_remote)
    return commands


class TestRollback:

    def test_the_lines_are_the_stamp_and_deploy_commands(self):
        lines = "\n".join(deploy.rollback_lines("0.1.3"))
        assert deploy.stamp_command("0.1.3") in lines
        assert deploy.deploy_command() in lines
        assert 'YANTRA_VER: "0.1.3"' in lines
        assert "restore" in lines and "dump" in lines

    def test_the_stamp_runs_the_same_command(self, pipeline):
        assert deploy.stamp("0.2.0") is True
        assert pipeline == [deploy.stamp_command("0.2.0")]

    def test_a_schema_that_never_gets_ready_prints_the_rollback_to_the_previous_version(
            self, pipeline, monkeypatch, capsys):
        monkeypatch.setattr(deploy, "deploy", lambda: True)
        monkeypatch.setattr(deploy, "wait_for_schema", lambda url: False)
        assert deploy.main() == 1
        out = capsys.readouterr().out
        assert "did not report schema_ready" in out
        assert deploy.stamp_command("0.1.3") in out
        # The current version is read before the stamp
        assert pipeline[0].startswith("cd /srv/erp_server && grep")
        assert pipeline[1] == deploy.stamp_command("0.2.0")

    def test_a_failed_playbook_prints_the_rollback_too(self, pipeline, monkeypatch, capsys):
        monkeypatch.setattr(deploy, "deploy", lambda: False)
        monkeypatch.setattr(deploy, "wait_for_schema", lambda url: pytest.fail("polled after a failed deploy"))
        assert deploy.main() == 1
        assert deploy.stamp_command("0.1.3") in capsys.readouterr().out

    def test_success_prints_no_rollback(self, pipeline, monkeypatch, capsys):
        monkeypatch.setattr(deploy, "deploy", lambda: True)
        monkeypatch.setattr(deploy, "wait_for_schema", lambda url: url == URL)
        assert deploy.main() == 0
        out = capsys.readouterr().out
        assert "schema ready" in out and "ROLLBACK" not in out

    def test_an_unreadable_current_version_aborts_before_the_stamp(self, pipeline, monkeypatch):
        monkeypatch.setattr(deploy, "read_stamped_version", lambda: None)
        assert deploy.main() == 1
        assert pipeline == []
