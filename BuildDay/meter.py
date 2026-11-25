"""Token and cost meter. Logs question, user, models, tokens, cost and SQL. Never logs result rows."""
import json
import os
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "config.json")))
LOG_DB = os.path.join(HERE, CONFIG["paths"]["token_log_db"])

SCHEMA = """CREATE TABLE IF NOT EXISTS calls (
  ts REAL, user TEXT, question TEXT, models TEXT, tokens_in INTEGER, tokens_out INTEGER,
  cost_rs REAL, secs REAL, cached INTEGER, action TEXT, sql TEXT)"""


class Usage:
    """Accumulates tokens per model across the model calls made for one question."""

    def __init__(self):
        self.by_model = {}

    def add(self, model, tin, tout):
        a, b = self.by_model.get(model, (0, 0))
        self.by_model[model] = (a + tin, b + tout)

    @property
    def tokens_in(self):
        return sum(a for a, _ in self.by_model.values())

    @property
    def tokens_out(self):
        return sum(b for _, b in self.by_model.values())

    @property
    def cost_rs(self):
        prices = CONFIG["pricing"]["usd_per_1m_tokens"]
        usd = 0.0
        for model, (a, b) in self.by_model.items():
            p = prices.get(model)
            if p:
                usd += a / 1e6 * p["in"] + b / 1e6 * p["out"]
        return usd * CONFIG["pricing"]["usd_to_inr"]


def log(user, question, usage, secs, cached, action, sql):
    try:
        con = sqlite3.connect(LOG_DB, timeout=10)
        try:
            con.execute(SCHEMA)
            con.execute(
                "INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), user, question, ",".join(usage.by_model), usage.tokens_in, usage.tokens_out,
                 usage.cost_rs, secs, int(cached), action, sql),
            )
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        pass  # metering must never break an answer
