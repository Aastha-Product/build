# S4 materials

| File | What it is |
|---|---|
| `dhruva-vault/` | Starter Obsidian vault: three notes provided, two for students to write |
| `server_fallback.py` | A working MCP server exposing get_application and escalate_to_analyst. Give it out only if Claude Code could not produce one. Copy it into a dhruva-triage folder |
| `call_tool.py` | A small client: starts the server, lists its tools, calls them. Run from the dhruva-triage folder |

Needs Python 3.10 or newer and `pip install "mcp>=2"` in a virtual environment.

```
cd dhruva-triage
python -m venv .venv && source .venv/bin/activate
pip install "mcp>=2" python-dotenv
cp ../S4/server_fallback.py mcp_server.py
python ../S4/call_tool.py mcp_server.py
```

On Windows use `.venv\Scripts\activate`.
