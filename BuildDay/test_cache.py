import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import assistant
import meter
import qcache


def fake_out(text, action="answer", sql="SELECT 1"):
    return {"rows": [(1.0,)], "text": text, "sql": sql, "action": action}


class CacheCascadeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patches = [
            mock.patch.object(qcache, "DB_PATH", os.path.join(self.tmp, "cache.db")),
            mock.patch.object(meter, "LOG_DB", os.path.join(self.tmp, "log.db")),
        ]
        for p in self.patches:
            p.start()
        qcache._locks.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_key_differs_by_user_and_ignores_case_and_spacing(self):
        k = lambda u, q: qcache.make_key(u, q, "v")
        self.assertNotEqual(k("ana", "net sales?"), k("ravi", "net sales?"))
        self.assertEqual(k("ana", "Net  sales ?"), k("ana", "net sales"))

    def test_key_changes_with_prompt_version(self):
        self.assertNotEqual(qcache.make_key("ana", "q", "v1"), qcache.make_key("ana", "q", "v2"))

    def test_second_ask_is_a_cache_hit_with_zero_tokens(self):
        with mock.patch.object(assistant, "_answer", side_effect=lambda q, u, usage, m: (usage.add(m, 100, 10), fake_out("a"))[1]) as f:
            first = assistant.answer("What was my net sales last month?", "ana")
            second = assistant.answer("what was my net sales last month", "ana")
        self.assertEqual(f.call_count, 1)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual((second["tokens_in"], second["cost_rs"]), (0, 0.0))
        self.assertEqual(second["text"], first["text"])

    def test_two_users_never_share_an_answer(self):
        with mock.patch.object(assistant, "_answer", side_effect=lambda q, u, usage, m: fake_out(f"for {u}")) as f:
            a = assistant.answer("net sales last month", "ana")
            r = assistant.answer("net sales last month", "ravi")
            a2 = assistant.answer("net sales last month", "ana")
        self.assertEqual(f.call_count, 2)
        self.assertEqual((a["text"], r["text"], a2["text"]), ("for ana", "for ravi", "for ana"))

    def test_entries_expire(self):
        with mock.patch.dict(qcache.CONFIG["cache"], {"ttl_s": 0}):
            with mock.patch.object(assistant, "_answer", side_effect=lambda q, u, usage, m: fake_out("a")) as f:
                assistant.answer("q", "ana")
                time.sleep(0.05)
                assistant.answer("q", "ana")
        self.assertEqual(f.call_count, 2)

    def test_errors_are_not_cached(self):
        with mock.patch.object(assistant, "_answer", side_effect=lambda q, u, usage, m: fake_out("bad", action="error")) as f:
            assistant.answer("q", "ana")
            assistant.answer("q", "ana")
        self.assertEqual(f.call_count, 4)  # small then large, twice: nothing was cached

    def test_cascade_escalates_when_small_model_raises(self):
        models = []

        def fake(q, u, usage, m):
            models.append(m)
            if m == assistant.CONFIG["models"]["small"]:
                raise RuntimeError("503")
            return fake_out("from large")

        with mock.patch.object(assistant, "_answer", side_effect=fake):
            out = assistant.answer("q", "ana")
        self.assertEqual(models, [assistant.CONFIG["models"]["small"], assistant.CONFIG["models"]["large"]])
        self.assertEqual(out["text"], "from large")

    def test_cascade_escalates_on_invalid_query_and_skips_large_when_small_works(self):
        models = []

        def fake(q, u, usage, m):
            models.append(m)
            return fake_out("x", action="error" if m == assistant.CONFIG["models"]["small"] else "answer")

        with mock.patch.object(assistant, "_answer", side_effect=fake):
            assistant.answer("q1", "ana")
        self.assertEqual(len(models), 2)
        models.clear()
        with mock.patch.object(assistant, "_answer", side_effect=lambda q, u, usage, m: (models.append(m), fake_out("ok"))[1]):
            assistant.answer("q2", "ana")
        self.assertEqual(models, [assistant.CONFIG["models"]["small"]])

    def test_identical_concurrent_questions_share_one_model_call(self):
        def slow(q, u, usage, m):
            time.sleep(0.3)
            return fake_out("a")

        results = []
        with mock.patch.object(assistant, "_answer", side_effect=slow) as f:
            ts = [threading.Thread(target=lambda: results.append(assistant.answer("same q", "ana"))) for _ in range(8)]
            [t.start() for t in ts]
            [t.join() for t in ts]
        self.assertEqual(f.call_count, 1)
        self.assertEqual(sum(r["cached"] for r in results), 7)


if __name__ == "__main__":
    unittest.main()
