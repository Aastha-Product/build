"""The measuring tools for the S7 benchmark. Students write the functions marked STAGE; no model key needed to test them."""
import math
import random
import re
import time

RETRYABLE = ("429", "503", "504", "RESOURCE_EXHAUSTED", "ResourceExhausted", "UNAVAILABLE", "DEADLINE_EXCEEDED", "ReadError", "ConnectError")


def passed(row, reply):
    """Given: a reply passes if every & part has one | alternative in it, and bad_if (a regex) does not match."""
    t = reply.lower()
    if row.get("bad_if") and re.search(row["bad_if"], t, re.I):
        return False
    return all(any(alt.strip().lower() in t for alt in must.split("|")) for must in row["must_have"].split("&"))


# STAGE 2
def backoff_call(fn, retries=4, base=2.0, sleep=time.sleep):
    """Call fn(). If it raises an error whose text contains a RETRYABLE marker, wait base*2**attempt seconds
    (plus up to 1 s of jitter) and try again, up to `retries` retries. Any other error, or the last failure, is raised."""
    raise NotImplementedError("Stage 2: write backoff_call")


# STAGE 3
def p95(values):
    """Nearest-rank 95th percentile: sort, take the value at position ceil(0.95 * n), counting from 1."""
    raise NotImplementedError("Stage 3: write p95")


def cost_inr(in_tokens, out_tokens, price, usd_inr):
    """Rupees for one call. price = {"input_per_m": USD per million input tokens, "output_per_m": ...}."""
    raise NotImplementedError("Stage 3: write cost_inr")


def bucket_scores(rows):
    """rows: dicts with "bucket" and "passed" (True/False). Return {bucket: share passed, 0 to 1}, plus "all"."""
    raise NotImplementedError("Stage 3: write bucket_scores")


# STAGE 4
def decide(results, rule):
    """results: {model: {"score", "holdout", "p95", "cost_per_1000"}}. rule: min_score, max_holdout_drop,
    max_p95_seconds, max_cost_per_1000_inr. Return (chosen, why) where why maps each model to the list of limits it broke.
    chosen = the cheapest model that breaks none (ties: the higher score); None if every model breaks something."""
    raise NotImplementedError("Stage 4: write decide")


# STAGE 5
def monthly_cost(cost_per_query, queries_per_day, multiplier=1, days=30):
    """Rupees a month at `multiplier` times today's volume."""
    raise NotImplementedError("Stage 5: write monthly_cost")


def volume_at_ceiling(cost_per_query, monthly_ceiling, days=30):
    """Queries a day at which the monthly bill reaches the ceiling."""
    raise NotImplementedError("Stage 5: write volume_at_ceiling")