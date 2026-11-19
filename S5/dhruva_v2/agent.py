"""v2: an interaction agent talks to Ira and hands work to two specialists (the Samora split)."""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from dhruva_core import config
from dhruva_tools import escalate_to_analyst, get_application, list_applications, score_application

analyst = Agent(
    model=config.MODEL,
    name="analyst",
    description="Reads and scores startup applications. Ask it for facts and recommendations. It cannot open tickets.",
    instruction=(
        "You read and score Dhruva Capital applications. Use the tools for every fact; never guess. "
        "Reply with the line 'Recommendation: <the recommendation text exactly as returned>', then the fit score "
        "and any criteria that could not be established. For several applications, list them first, then score each. "
        "If a tool returns an error, report it plainly and do not retry."
    ),
    tools=[list_applications, get_application, score_application],
)

ops = Agent(
    model=config.MODEL,
    name="ops",
    description="Opens a ticket for a human analyst. Ask it to escalate one application with a reason.",
    instruction=(
        "You open tickets for human analysts using escalate_to_analyst. Report the ticket number, and say clearly "
        "if the ticket was already open. If a tool returns an error, report it plainly and do not retry."
    ),
    tools=[escalate_to_analyst],
)

root_agent = Agent(
    model=config.MODEL,
    name="dhruva_partner_assistant",
    description="Talks to Ira Bhandari about startup applications at Dhruva Capital.",
    instruction=(
        "You talk to Ira Bhandari, founding partner at Dhruva Capital. You do not look anything up yourself. "
        "Ask the analyst agent for facts and recommendations, and the ops agent to open tickets. "
        "Reply in plain language, in three lines or fewer. Keep the specialist's 'Recommendation:' line exactly as "
        "given, and never state a number the specialists did not return. Open a ticket only when asked. "
        "You recommend; a person decides."
    ),
    tools=[AgentTool(agent=analyst), AgentTool(agent=ops)],
)
