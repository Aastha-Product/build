import json
import os
import sqlite3
import unittest

import sqlguard
from sqlguard import SqlRejected, run_readonly, validate

USERS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")))
ALL = USERS["hq"]["stores"]


class ValidateTests(unittest.TestCase):
    def test_accepts_select(self):
        self.assertEqual(validate("SELECT 1;"), "SELECT 1")
        self.assertTrue(validate("WITH a AS (SELECT 1 x) SELECT x FROM a"))

    def test_rejects_writes(self):
        for q in ["DELETE FROM sales", "UPDATE sales SET qty=0", "DROP TABLE sales", "INSERT INTO stores VALUES (1)",
                  "PRAGMA table_info(sales)", "ATTACH DATABASE 'x' AS y", "CREATE TABLE t(a)"]:
            with self.assertRaises(SqlRejected, msg=q):
                validate(q)

    def test_rejects_multi_statement(self):
        with self.assertRaises(SqlRejected):
            validate("SELECT 1; DROP TABLE sales")

    def test_rejects_comments(self):
        for q in ["SELECT 1 -- hi", "SELECT /* x */ 1"]:
            with self.assertRaises(SqlRejected, msg=q):
                validate(q)

    def test_keyword_inside_string_is_fine(self):
        self.assertTrue(validate("SELECT city FROM stores WHERE city = 'please delete; this -- ok'"))

    def test_rejects_empty(self):
        with self.assertRaises(SqlRejected):
            validate("   ")


class RunTests(unittest.TestCase):
    def test_reads(self):
        rows, truncated = run_readonly("SELECT city FROM stores WHERE store_id='S03'", ["S03"])
        self.assertEqual(rows, [("Pune",)])
        self.assertFalse(truncated)

    def test_row_limit(self):
        rows, truncated = run_readonly("SELECT line_id FROM sales", ALL, row_limit=5)
        self.assertEqual(len(rows), 5)
        self.assertTrue(truncated)

    def test_timeout(self):
        slow = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c"
        with self.assertRaises(SqlRejected):
            run_readonly(slow, ALL, timeout_s=1)

    def test_connection_is_read_only(self):
        uri = "file:" + sqlguard.DB_PATH.replace("\\", "/") + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("DELETE FROM sales")
        con.close()

    def test_authorizer_blocks_write_even_if_validate_skipped(self):
        con = sqlguard.open_scoped(["S03"])
        with self.assertRaises(sqlite3.DatabaseError):
            con.execute("DELETE FROM sales")
        con.close()


class ScopeTests(unittest.TestCase):
    def test_each_user_sees_only_their_stores_in_sales_and_stores(self):
        for user, info in USERS.items():
            scope = set(info["stores"])
            sales, _ = run_readonly("SELECT DISTINCT store_id FROM sales", info["stores"])
            stores, _ = run_readonly("SELECT store_id FROM stores", info["stores"])
            self.assertEqual({r[0] for r in sales}, scope, user)
            self.assertEqual({r[0] for r in stores}, scope, user)

    def test_other_store_is_empty_not_visible(self):
        rows, _ = run_readonly("SELECT COUNT(*) FROM sales WHERE store_id='S07'", USERS["ana"]["stores"])
        self.assertEqual(rows, [(0,)])

    def test_base_tables_are_denied(self):
        ana = USERS["ana"]["stores"]
        for q in [
            "SELECT COUNT(*) FROM main.sales",
            "SELECT * FROM main.stores",
            "WITH sales AS (SELECT * FROM main.sales) SELECT COUNT(*) FROM sales",
            "SELECT * FROM sqlite_master",
            "SELECT * FROM sqlite_temp_master",
        ]:
            with self.assertRaises(SqlRejected, msg=q):
                run_readonly(q, ana)

    def test_notes_column_is_not_exposed(self):
        with self.assertRaises(SqlRejected):
            run_readonly("SELECT notes FROM stores", USERS["ana"]["stores"])

    def test_products_are_shared(self):
        rows, _ = run_readonly("SELECT COUNT(*) FROM products", USERS["ana"]["stores"])
        self.assertEqual(rows, [(60,)])

    def test_bad_scope_is_rejected(self):
        for bad in [[], ["S03'; DROP TABLE sales;--"], ["x"]]:
            with self.assertRaises(SqlRejected, msg=str(bad)):
                sqlguard.open_scoped(bad)

    def test_totals_differ_by_scope(self):
        q = "SELECT COUNT(*) FROM sales"
        ana, _ = run_readonly(q, USERS["ana"]["stores"])
        hq, _ = run_readonly(q, ALL)
        self.assertLess(ana[0][0], hq[0][0])
        self.assertEqual(hq[0][0], 223702)


if __name__ == "__main__":
    unittest.main()
