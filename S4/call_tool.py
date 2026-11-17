"""S4 exemplar client: start the server, list its tools, call them. Run from the dhruva-triage folder.
    python call_tool.py /path/to/server.py
This is the host's job, done by hand: list the tools, then call one.
"""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(server_path):
    params = StdioServerParameters(command=sys.executable, args=[server_path])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS THE SERVER OFFERS:")
            for t in tools.tools:
                print(" -", t.name, "|", (t.description or "").split(".")[0])
            for name, args in [("get_application", {"app_id": "A03"}),
                               ("get_application", {"app_id": "A99"}),
                               ("escalate_to_analyst", {"app_id": "A02", "reason": "5 criteria missing"}),
                               ("escalate_to_analyst", {"app_id": "A02", "reason": "again"})]:
                r = await session.call_tool(name, args)
                text = r.content[0].text if r.content else ""
                print("\nCALL", name, args, "\n ->", text[:200].replace("\n", " "))


asyncio.run(main(sys.argv[1]))
