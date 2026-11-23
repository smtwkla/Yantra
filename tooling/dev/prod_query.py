"""Read-only SQL against Yantra's production MariaDB, for diagnosing issues (or the dev DB with --dev).

Production: connects as the read-only user from the PROD_RO_DB_* values in backend/secrets_app.py
(on the dev laptop only; the production container never has them). The database user is what keeps
this read-only: before any query the script reads SHOW GRANTS and stops unless the user holds only
SELECT (and USAGE). The session is also set READ ONLY, which blocks a DML write but not DDL, hence
the grant check. Dev: connects with config.DB_CONFIG (the dev DB on 3307), no grant check.

The session time zone is +05:30, as the app's own connections (local_db), so times read as IST.

Usage (wrappers tooling/run-prod-query.bat and tooling/run-dev-query.bat, run from the repo root):
    run-prod-query.bat "SELECT * FROM task_queue WHERE status = 'failed' ORDER BY id DESC LIMIT 20"
    run-prod-query.bat --file scratch/q.sql     SQL from a file (long queries; no cmd quoting or %)
    run-prod-query.bat --ddl                    SHOW CREATE TABLE for every table the user can see
    run-prod-query.bat                          the probe (version, tables, approx rows), then a prompt
"""

import argparse
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pymysql
import pymysql.cursors

MAX_ROWS_SHOWN = 200
# A guard for a shared production server: a query that runs longer is stopped by MariaDB.
MAX_STATEMENT_SECONDS = 60
# The only privileges the production user may hold; anything else and the script refuses to run.
ALLOWED_PRIVILEGES = {"SELECT", "USAGE"}
PROD_KEYS = ("PROD_RO_DB_HOST", "PROD_RO_DB_PORT", "PROD_RO_DB_USER", "PROD_RO_DB_PASSWORD", "PROD_RO_DB_NAME")


def _prod_config():
    try:
        import secrets_app
    except ImportError:
        sys.exit("ERROR: backend/secrets_app.py not found. It must hold the PROD_RO_DB_* values.")
    missing = [k for k in PROD_KEYS if not getattr(secrets_app, k, None)]
    if missing:
        sys.exit(f"ERROR: set {', '.join(missing)} in backend/secrets_app.py (see example_secrets_app.py).")
    return {
        "host": secrets_app.PROD_RO_DB_HOST,
        "port": int(secrets_app.PROD_RO_DB_PORT),
        "user": secrets_app.PROD_RO_DB_USER,
        "password": secrets_app.PROD_RO_DB_PASSWORD,
        "database": secrets_app.PROD_RO_DB_NAME,
    }


def _dev_config():
    from config import DB_CONFIG
    return DB_CONFIG


def connect(config):
    conn = pymysql.connect(
        **config,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=10,
        init_command="SET time_zone = '+05:30'",
    )
    with conn.cursor() as cur:
        cur.execute("SET SESSION TRANSACTION READ ONLY")
        cur.execute(f"SET SESSION max_statement_time = {MAX_STATEMENT_SECONDS}")
    return conn


def grant_problems(grant_lines):
    """The grant lines that give more than ALLOWED_PRIVILEGES (pure: SHOW GRANTS text in, lines out).

    A line is 'GRANT <privileges> ON <object> TO <user> ...'; a column grant reads 'SELECT (a, b)'.
    A line of another shape (a role grant, PROXY) counts as a problem, so the check fails closed.
    """
    problems = []
    for line in grant_lines:
        match = re.match(r"GRANT (.+?) ON ", line)
        if not match:
            problems.append(line)
            continue
        privileges = re.sub(r"\([^)]*\)", "", match.group(1))
        names = {p.strip().upper() for p in privileges.split(",")}
        if not names <= ALLOWED_PRIVILEGES:
            problems.append(line)
    return problems


def check_read_only_user(conn):
    with conn.cursor() as cur:
        cur.execute("SHOW GRANTS FOR CURRENT_USER()")
        lines = [list(row.values())[0] for row in cur.fetchall()]
    problems = grant_problems(lines)
    if problems:
        print("REFUSED: the production user holds more than SELECT. Use a read-only user.", file=sys.stderr)
        for line in problems:
            print(f"  {re.sub(r'IDENTIFIED BY .*', 'IDENTIFIED BY ...', line)}", file=sys.stderr)
        sys.exit(2)


def _cell(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if value is None:
        return "NULL"
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def format_results(rows):
    if not rows:
        print("(no rows)")
        return
    cols = list(rows[0].keys())
    shown = [[_cell(row[c]) for c in cols] for row in rows[:MAX_ROWS_SHOWN]]
    widths = [max([len(c)] + [len(r[i]) for r in shown]) for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("-+-".join("-" * w for w in widths))
    for r in shown:
        print(" | ".join(v.ljust(w) for v, w in zip(r, widths)))
    total = len(rows)
    if total > MAX_ROWS_SHOWN:
        print(f"\n... ({total - MAX_ROWS_SHOWN} more rows not shown, {total} in all)")
    else:
        print(f"\n({total} row{'' if total == 1 else 's'})")


def run_query(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            format_results(cur.fetchall())
        else:
            print(f"OK ({cur.rowcount} rows affected)")


def _visible_tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name AS name, table_rows AS approx_rows FROM information_schema.tables"
            " WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' ORDER BY table_name"
        )
        return cur.fetchall()


def probe(conn):
    """Version and tables. Row counts are InnoDB's estimates (information_schema), so no table is scanned."""
    with conn.cursor() as cur:
        cur.execute("SELECT DATABASE() AS db, CURRENT_USER() AS user, VERSION() AS server, NOW() AS now_ist")
        print(" ".join(f"{k}={_cell(v)}" for k, v in cur.fetchone().items()))
        try:
            cur.execute("SELECT MAX(version) AS v FROM db_version")
            print(f"schema version v{cur.fetchone()['v']}")
        except pymysql.MySQLError as e:
            print(f"schema version unknown: {e}")
    tables = _visible_tables(conn)
    print(f"\n{len(tables)} tables visible to this user")
    format_results(tables)


def ddl(conn):
    with conn.cursor() as cur:
        for t in _visible_tables(conn):
            try:
                cur.execute(f"SHOW CREATE TABLE `{t['name']}`")
                print(cur.fetchone()["Create Table"] + ";\n")
            except pymysql.MySQLError as e:
                print(f"-- {t['name']}: {e}\n")


def interactive(conn):
    print("\nEnter SQL (read-only). Type 'quit' or press Ctrl+C to leave.\n")
    while True:
        try:
            sql = input("sql> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not sql or sql.lower() in ("quit", "exit", "\\q"):
            break
        try:
            run_query(conn, sql)
        except pymysql.MySQLError as e:
            print(f"ERROR: {e}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Read-only SQL against Yantra's production (or dev) MariaDB.")
    parser.add_argument("sql", nargs="*", help="the query; several words are joined with spaces")
    parser.add_argument("--dev", action="store_true", help="the dev DB (config.DB_CONFIG), not production")
    parser.add_argument("--file", help="read the query from this file")
    parser.add_argument("--ddl", action="store_true", help="print SHOW CREATE TABLE for every visible table")
    args = parser.parse_args()

    conn = connect(_dev_config() if args.dev else _prod_config())
    try:
        if not args.dev:
            check_read_only_user(conn)
            print("NOTE: production data.")
        if args.ddl:
            ddl(conn)
        elif args.file or args.sql:
            if args.file:
                with open(args.file, encoding="utf-8") as f:
                    sql = f.read().strip()
            else:
                sql = " ".join(args.sql)
            print(f">>> {sql}\n")
            try:
                run_query(conn, sql)
            except pymysql.MySQLError as e:
                sys.exit(f"ERROR: {e}")
        else:
            probe(conn)
            interactive(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
