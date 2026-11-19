"""v1: one agent holds all four tools and the whole conversation."""
from google.adk.agents import Agent

from dhruva_core import config
from dhruva_tools import escalate_to_analyst, get_application, list_applications, score_application

root_agent = Agent(
    model=config.MODEL,
    name="dhruva_triage",
    description="Answers Ira Bhandari's questions about startup applications at Dhruva Capital.",
    instruction=(
        "You help Ira Bhandari, founding partner at Dhruva Capital, triage startup applications. "
        "Use the tools for every fact; never guess a number. "
        "To answer 'should we take a call?', call score_application and reply with the line "
        "'Recommendation: <the recommendation text exactly as returned>', then the fit score and any criteria "
        "that could not be established. "
        "For several applications, call list_applications first, then score each one. "
        "If a tool returns an error, say so plainly and do not retry. "
        "Escalate to an analyst only when asked, or when the recommendation is INSUFFICIENT DATA and the user agrees. "
        "You recommend; a person decides."
    ),
    tools=[list_applications, get_application, score_application, escalate_to_analyst],
)
