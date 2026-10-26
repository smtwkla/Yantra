"""config.py at import: the start-up refusals (S059 § 1.4)."""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_dev_auth_bypass_is_refused_outside_the_dev_server():
    """config runs the check at import, and the test session has imported it already: so a
    fresh interpreter.  A copy of os.environ keeps YANTRA_TESTING=1, so config falls back to
    the example secrets where secrets_app.py is absent (the release worktree, BR1-02)."""
    env = {**os.environ, "DEV_AUTH_BYPASS": "1", "FLASK_DEBUG": "0"}
    result = subprocess.run([sys.executable, "-c", "import config"], cwd=BACKEND_DIR, env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert "DEV_AUTH_BYPASS=1 is only allowed" in result.stderr
