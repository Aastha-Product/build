"""The checker's three exits, and the callbacks that wire maker and checker together through session state.

State keys: sources (everything the tools returned), draft (the maker's reply), verdict (PASS, FAIL or HOLD), feedback.
The tool_context argument is filled in by ADK; the model never sees it.
"""
import csv
import json
import re
import time
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

HELD_LOG = Path("held_for_review.csv")


def _numbers(text):
    """Numbers in a text, normalised so 7.50 and 7.5 match. List markers like '1.' at a line start are ignored."""
    text = re.sub(r"(?m)^\s*\d+[.)]\s", "", text)
    return {f"{float(x):g}" for x in re.findall(r"\d+(?:\.\d+)?", text)}


def unsupported_numbers(draft, sources):
    """STAGE 2 (you write this): the numbers in the draft that do not appear in the sources, as a sorted list of strings.

    Use _numbers(text), which returns a set of normalised number strings. Sort numerically: key=float.
    """
    raise NotImplementedError("Stage 2: write unsupported_numbers")


def log_hold(reason, draft):
    """STAGE 3 (you write this): append one row (time, reason, draft) to HELD_LOG.

    Write the header ["time", "reason", "draft"] first if the file does not exist yet.
    Replace line breaks in the draft with spaces. Use csv.writer and time.strftime.
    """
    raise NotImplementedError("Stage 3: write log_hold")


def check_numbers(tool_context: ToolContext) -> dict:
    """Code check for rule 1. Call this FIRST. Returns the numbers in the draft that are not in the sources. If the list is not empty, reject."""
    bad = unsupported_numbers(tool_context.state.get("draft", ""), tool_context.state.get("sources", ""))
    return {"ok": not bad, "unsupported_numbers": bad}


def approve(tool_context: ToolContext) -> dict:
    """Release the draft. Call this only when the draft passes all three rules. Ends the loop."""
    tool_context.state["verdict"] = "PASS"
    tool_context.actions.escalate = True  # escalate = leave the loop
    return {"ok": True, "verdict": "PASS"}


def reject(reason: str, tool_context: ToolContext) -> dict:
    """Send the draft back to the maker. Give one sentence: which rule failed and what to fix. Use it when a redraft could fix the problem."""
    tool_context.state["verdict"] = "FAIL"
    tool_context.state["feedback"] = reason
    return {"ok": True, "verdict": "FAIL"}


def hold_for_human(reason: str, tool_context: ToolContext) -> dict:
    """Stop and hand the case to a person. Use it when the request asks the company to commit to something, or involves hardship or a complaint. Redrafting cannot fix these. Ends the loop."""
    tool_context.state["verdict"] = "HOLD"
    tool_context.state["feedback"] = reason
    log_hold(reason, tool_context.state.get("draft", ""))
    tool_context.actions.escalate = True
    return {"ok": True, "verdict": "HOLD"}


def log_sources(tool, args, tool_context, tool_response):
    """after_tool_callback for the maker: keep what each tool returned, so the checker can compare the draft with it."""
    log = tool_context.state.get("sources", "")
    tool_context.state["sources"] = log + f"\n{tool.name}({json.dumps(args)}) -> {json.dumps(tool_response)}"
    return None


def start_round(callback_context):
    """before_agent_callback for the maker: wipe the notes at the start of a new question, keep them on a redraft."""
    if callback_context.state.get("verdict") != "FAIL":
        callback_context.state["sources"] = ""
        callback_context.state["feedback"] = ""
    return None
