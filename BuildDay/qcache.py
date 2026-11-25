"""Exact-match answer cache.

The key includes the user, so one user can never be served another user's cached answer. It also includes the
data version and a hash of the prompts, so a data refresh or a prompt change invalidates old entries.
Entries expire after cache.ttl_s. Errors are never cached (the caller decides what to store).
"""
import hashlib
import json
import os
import re
import sqlite3
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "config.json")))
DB_PATH = os.path.join(HERE, CONFIG["paths"]["cache_db"])

_SCHEMA = "CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, created REAL, payload TEXT)"
_locks = {}
_locks_guard = threading.Lock()


def normalise(question):
    return re.sub(r"\s+", " ", question.strip().lower()).rstrip("?.! ")


def make_key(user, question, prompt_version):
    raw = "|".join([user, normalise(question), CONFIG["cache"]["data_version"], prompt_version])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _connect():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute(_SCHEMA)
    return con


def get(key):
    try:
        con = _connect()
        try:
            row = con.execute("SELECT created, payload FROM answers WHERE key=?", (key,)).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    if not row or time.time() - row[0] > CONFIG["cache"]["ttl_s"]:
        return None
    return json.loads(row[1])


def put(key, payload):
    try:
        con = _connect()
        try:
            con.execute("INSERT OR REPLACE INTO answers VALUES (?,?,?)", (key, time.time(), json.dumps(payload, default=str)))
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        pass  # a cache failure must never break an answer


def lock_for(key):
    """One lock per key, so identical questions that arrive together share a single model call."""
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())
