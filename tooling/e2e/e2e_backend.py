"""The backend of the browser tests (S024): the Flask app on 127.0.0.1:5002 against a
throw-away database, vel_yantra_e2e, rebuilt by the migrations at every start.

Started by Playwright (frontend/playwright.config.js, webServer) in the backend's uv
environment:  uv run --project ../backend python ../tooling/e2e/e2e_backend.py

Who the user is comes from the test headers (X-Test-Role, X-Test-User, X-Test-Email), as in the pytest
suite: TESTING on, with a TEST_USER_FACTORY.  A request without them falls to the dev stub
user, which is set to "nobody" here, so a lost header gets no access, never admin
(S024 § 5.1).  Dev only: FLASK_DEBUG=1 (config.py allows the auth bypass only then),
bound to 127.0.0.1, and the guard below refuses any database but a local *_e2e one before
anything is dropped.

Lanes (tooling/e2e/run_lanes.py): with E2E_LANE=<n> set, the backend takes the lane's own
database (vel_yantra_lane<n>_e2e: still *_e2e, so the guard is unchanged), port (5010 + n)
and files folder, so several lanes run side by side and share nothing.  Unset, it is the
single stack above.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BACKEND = os.path.join(REPO, "backend")

# The lane, as frontend/e2e/support/stack.js reads it ("" = the single stack)
LANE = os.environ.get("E2E_LANE", "")
if LANE and not LANE.isdigit():
    sys.exit(f"e2e backend: E2E_LANE must be a number, not {LANE!r}")
LANE_PORT_BASE = 5010
E2E_DATABASE = f"vel_yantra_lane{LANE}_e2e" if LANE else "vel_yantra_e2e"
HOST = "127.0.0.1"
PORT = LANE_PORT_BASE + int(LANE) if LANE else 5002
DATA_DIR = os.path.join(REPO, "scratch", "e2e-data", *([f"lane{LANE}"] if LANE else []))
LOCAL_HOSTS = ("localhost", "127.0.0.1")
# A request without the test headers: no role, no membership (auth_utils._get_dev_stub_user)
NO_ACCESS_ROLE = "nobody"


def check_target(db_config):
    """None when the database may be dropped and rebuilt: a local host and a name ending in
    _e2e; else why not.  A mistyped setting can then never drop the dev or test database,
    nor reach another server."""
    host, name = db_config.get("host"), db_config.get("database") or ""
    if host not in LOCAL_HOSTS:
        return f"refusing database host {host!r}: the e2e database must be local ({', '.join(LOCAL_HOSTS)})"
    if not name.endswith("_e2e"):
        return f"refusing database {name!r}: the e2e database's name must end in _e2e"
    return None


def _recreate_database(db_config):
    """DROP and CREATE the database on a plain connection with none selected, with the
    charset and collation of tooling/dev/init-test-db.sql."""
    import pymysql
    conn = pymysql.connect(host=db_config["host"], port=db_config["port"], user=db_config["user"],
                           password=db_config["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            name = db_config["database"]
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
            cur.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


def _empty_data_dir():
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    os.makedirs(DATA_DIR)    # parents too: scratch/e2e-data/lane<n>


def _user_factory(harness_user, names):
    """X-Test-Role / X-Test-User / X-Test-Email -> g.user, as the pytest factory, with the seed
    person's name for the top bar.  The username defaults to e2e_<role>: created_by is NOT NULL,
    so a missing X-Test-User must not make a write fail (BR2-02).  X-Test-Email is the token's
    email claim (S032 BR1-04), "" when absent."""
    def factory(role_name, username, email=""):
        username = username or f"e2e_{role_name}"
        return harness_user(role_name, username, names.get(username, username), email=email)
    return factory


def main():
    # 1. Before config is imported: it reads these at import, and refuses the bypass
    #    without FLASK_DEBUG
    sys.path.insert(0, BACKEND)
    sys.path.insert(0, HERE)
    os.environ["FLASK_DEBUG"] = "1"
    os.environ["DEV_AUTH_BYPASS"] = "1"   # the frontend skips Keycloak, as in dev
    os.environ["DATA_DIR"] = DATA_DIR

    # 2. The database and the stub user, then the guard on what is now set
    import config
    config.DB_CONFIG["database"] = E2E_DATABASE
    config.DEV_STUB_ROLE = NO_ACCESS_ROLE
    # Push on (S021 BR1-06, BS1-03): a fresh VAPID pair per process, so each lane has its own.
    # Nothing is ever sent: the e2e stack runs no worker.
    from vapid_keys import make_key_pair
    config.VAPID_PUBLIC_KEY, config.VAPID_PRIVATE_KEY = make_key_pair()
    config.VAPID_SUBJECT = "mailto:e2e@example.invalid"
    # Email on (S032 § 8) with reserved test values, whatever the local secrets hold: the test
    # email stays a queued task, since no worker runs.  The dev stub gets no address.
    config.SMTP_HOST, config.SMTP_PORT, config.SMTP_FROM = "smtp.example.test", 2525, "yantra@example.test"
    config.SMTP_USER, config.SMTP_PASSWORD = "", ""
    config.DEV_STUB_EMAIL = ""
    refusal = check_target(config.DB_CONFIG)
    if refusal:
        sys.exit(f"e2e backend: {refusal}")

    # 3. A fresh database and data folder at every run
    _recreate_database(config.DB_CONFIG)
    _empty_data_dir()

    # 4. Then the app: it opens the pool and runs the migrations at import
    from app import app
    from seed_e2e import display_names
    from tests.harness import harness_user
    app.config["TESTING"] = True
    app.config["TEST_USER_FACTORY"] = _user_factory(harness_user, display_names())

    # 5. No reloader: it would run this launcher (and the drop) again in a child process
    app.run(host=HOST, port=PORT, use_reloader=False)


if __name__ == "__main__":
    main()
