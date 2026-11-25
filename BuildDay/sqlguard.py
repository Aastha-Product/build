"""Code-side guard for model-written SQL. The model proposes; this module decides.

validate(sql)                 -> cleaned single SELECT, or raises SqlRejected
run_readonly(sql, stores)     -> (rows, truncated), run against per-user views on a read-only connection

Isolation (slice 2): the connection exposes `sales` and `stores` as TEMP views filtered to the user's
stores. The `stores` view omits the free-text `notes` column. An authorizer denies any direct read of the
base tables (main.sales, main.stores) and of sqlite_master, so the model cannot step around the views.
"""
import json
import os
import re
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "config.json")))
DB_PATH = os.path.join(HERE, CONFIG["paths"]["retail_db"])

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex|analyze|begin|commit|rollback|savepoint|load_extension)\b",
    re.I,
)
STORE_ID = re.compile(r"^S\d\d$")
SCOPED_TABLES = ("sales", "stores")


class SqlRejected(ValueError):
    pass


def _strip_literals(sql):
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate(sql):
    if not isinstance(sql, str) or not sql.strip():
        raise SqlRejected("empty query")
    s = sql.strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    bare = _strip_literals(s)
    if "--" in bare or "/*" in bare or "*/" in bare:
        raise SqlRejected("comments are not allowed")
    if ";" in bare:
        raise SqlRejected("only one statement is allowed")
    if not re.match(r"(select|with)\b", bare, re.I):
        raise SqlRejected("only SELECT is allowed")
    bad = FORBIDDEN.search(bare)
    if bad:
        raise SqlRejected(f"forbidden keyword: {bad.group(1).lower()}")
    return s


def _authorizer(action, arg1, arg2, db_name, source):
    """arg1 is the table for READ. `source` is the view responsible for the access, or None for top-level SQL."""
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        table = (arg1 or "").lower()
        if table.startswith("sqlite_"):
            return sqlite3.SQLITE_DENY
        if db_name == "main" and table in SCOPED_TABLES:
            return sqlite3.SQLITE_OK if (source or "").lower() in SCOPED_TABLES else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def open_scoped(stores):
    """Read-only connection whose `sales` and `stores` are views over the given stores only."""
    stores = list(stores)
    if not stores or not all(STORE_ID.match(s) for s in stores):
        raise SqlRejected("invalid store scope")
    ids = ",".join(f"'{s}'" for s in stores)
    uri = "file:" + DB_PATH.replace("\\", "/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, check_same_thread=False)
    con.execute(f"CREATE TEMP VIEW sales AS SELECT * FROM main.sales WHERE store_id IN ({ids})")
    con.execute(
        f"CREATE TEMP VIEW stores AS SELECT store_id, store_name, city, region, opened_on FROM main.stores WHERE store_id IN ({ids})"
    )
    con.set_authorizer(_authorizer)
    return con


def run_query(sql, stores, timeout_s=None, row_limit=None):
    """Returns {rows, columns, truncated}. Raises SqlRejected on anything the guard refuses or SQLite rejects."""
    timeout_s = timeout_s or CONFIG["limits"]["query_timeout_s"]
    row_limit = row_limit or CONFIG["limits"]["row_limit"]
    sql = validate(sql)
    con = open_scoped(stores)
    try:
        deadline = time.time() + timeout_s
        con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
        try:
            cur = con.execute(sql)
            columns = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(row_limit + 1)
        except sqlite3.Error as e:
            raise SqlRejected(f"query failed: {e}") from e
        return {"rows": [tuple(r) for r in rows[:row_limit]], "columns": columns, "truncated": len(rows) > row_limit}
    finally:
        con.close()


def run_readonly(sql, stores, timeout_s=None, row_limit=None):
    r = run_query(sql, stores, timeout_s, row_limit)
    return r["rows"], r["truncated"]
