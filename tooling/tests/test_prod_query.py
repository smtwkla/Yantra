"""tooling/dev/prod_query.py: the grant check that keeps the production tool read-only.

The tooling suite runs without the backend's packages, so pymysql is a stub here; the check is pure.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "dev" / "prod_query.py"


@pytest.fixture(scope="module")
def prod_query():
    stub = types.ModuleType("pymysql")
    stub.cursors = types.ModuleType("pymysql.cursors")
    stub.MySQLError = Exception
    saved = {k: sys.modules.get(k) for k in ("pymysql", "pymysql.cursors")}
    sys.modules["pymysql"], sys.modules["pymysql.cursors"] = stub, stub.cursors
    try:
        spec = importlib.util.spec_from_file_location("prod_query", _PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def test_select_only_user_passes(prod_query):
    lines = [
        "GRANT USAGE ON *.* TO `vel_yantra_ro`@`%` IDENTIFIED BY PASSWORD '*AB' WITH MAX_USER_CONNECTIONS 3",
        "GRANT SELECT ON `vel_yantra_master`.`tickets` TO `vel_yantra_ro`@`%`",
        "GRANT SELECT (`id`, `name`, `active`) ON `vel_yantra_master`.`people` TO `vel_yantra_ro`@`%`",
    ]
    assert prod_query.grant_problems(lines) == []


@pytest.mark.parametrize("line", [
    "GRANT ALL PRIVILEGES ON `vel_yantra_master`.* TO `vel_yantra_master`@`%`",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON `vel_yantra_master`.* TO `x`@`%`",
    "GRANT SELECT (`id`), UPDATE (`name`) ON `vel_yantra_master`.`people` TO `x`@`%`",
    "GRANT CREATE, DROP ON *.* TO `x`@`%`",
    "GRANT `app_role` TO `x`@`%`",
])
def test_any_other_privilege_is_a_problem(prod_query, line):
    assert prod_query.grant_problems([line]) == [line]
