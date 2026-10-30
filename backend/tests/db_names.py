"""The test databases' names: one pair per test run and per pytest-xdist worker, so parallel
workers, and two runs at once (a release's tests while an agent tests), never share data.

    vel_yantra_test_<run>_<worker>      the suite's database (conftest.py)
    vel_yantra_upgrade_<run>_<worker>   the migration upgrade tests' (test_migration_v2*.py)
    vel_yantra_test_<run>_schemadocs    tooling\schema-docs.bat's, built and dropped each run (S078)

<run> is YANTRA_TEST_RUN (default "dev"; tooling/release-tests.bat sets "release"); <worker> is
PYTEST_XDIST_WORKER (gw0, gw1, ...), or "main" without xdist.  Both are cut to lower-case
letters and digits so the name stays a plain identifier, well under MariaDB's 64 characters.

The databases are created by the tests (CREATE DATABASE IF NOT EXISTS) and kept between runs,
so a run only applies the migrations that are new.  The DB user's right to create them is a
wildcard grant on vel_yantra_test_% and vel_yantra_upgrade_% (tooling/run-backend-tests.bat,
tooling/dev/init-test-db.sql).
"""

import os
import re

from local_db import named_lock

DEFAULT_RUN = "dev"
NO_XDIST_WORKER = "main"
_PART_MAX = 12


def _part(value, default):
    cleaned = re.sub(r"[^a-z0-9]", "", (value or "").lower())[:_PART_MAX]
    return cleaned or default


def run_suffix(environ=os.environ):
    run = _part(environ.get("YANTRA_TEST_RUN"), DEFAULT_RUN)
    worker = _part(environ.get("PYTEST_XDIST_WORKER"), NO_XDIST_WORKER)
    return f"{run}_{worker}"


TEST_DB = f"vel_yantra_test_{run_suffix()}"
UPGRADE_DB = f"vel_yantra_upgrade_{run_suffix()}"

# The schema docs' database (tooling/schema/schema_docs.py, S078): one per run, built fresh from
# the migrations and dropped after the catalogue is read.  Inside the vel_yantra_test_% grant;
# "schemadocs" is never a worker part (gw0, gw1, ..., main).
SCHEMA_DOCS_DB = f"vel_yantra_test_{_part(os.environ.get('YANTRA_TEST_RUN'), DEFAULT_RUN)}_schemadocs"

# The worker tests' singleton lock (test_worker, test_task_queue, test_alerts): GET_LOCK names
# are server-wide, so the name carries this run's database, as the product's does (local_db).
TEST_WORKER_LOCK = named_lock("yantra_worker_test", TEST_DB)
