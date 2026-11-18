# S4: Plug it in (MCP lab setup)

| File | What it is |
|---|---|
| `dhruva-vault/` | Starter Obsidian vault: three notes provided, two for you to write |
| `server_fallback.py` | A working MCP server exposing `get_application` and `escalate_to_analyst`. Use it only if Claude Code could not produce one for you |
| `call_tool.py` | A small client: starts a server, lists its tools, calls them |

About 25 minutes. Do this before class. If a step fails, bring the error message to class.

## 1. Python 3.10 or newer

```
python --version
```

If it says 3.9 or lower, the MCP library will not install. On a Mac, `brew install python@3.11` and use `python3.11` everywhere below instead of `python`. On Windows, install from https://www.python.org/downloads/ and tick "Add to PATH". If you cannot upgrade, tell us at the start of class and use the fallback server.

## 2. Get the files

```
git clone https://github.com/Ekta-Shah/ai-builds.git
cd ai-builds
git pull          # if you already cloned it earlier
```

Your own `dhruva-triage` folder from S2 and your `tools.py` from S3 stay where they are. The commands below assume you are in that folder. If you work in the clone instead, `dhruva-triage/` here is the same code.

## 3. Install the MCP library in a virtual environment

A virtual environment is a private box for a project's Python packages.

Mac or Linux:

```
cd dhruva-triage
python3.11 -m venv .venv        # or: python -m venv .venv
source .venv/bin/activate
pip install "mcp>=2" python-dotenv
python -c "from mcp.server import MCPServer; print('ok')"
```

Windows (PowerShell):

```
cd dhruva-triage
python -m venv .venv
.venv\Scripts\activate
pip install "mcp>=2" python-dotenv
python -c "from mcp.server import MCPServer; print('ok')"
```

You should see `ok`. Next time, you only need the `activate` line.

## 4. Check the fallback server runs

From the `dhruva-triage` folder, with the environment active:

```
cp ../S4/server_fallback.py mcp_server.py          # Windows: copy ..\S4\server_fallback.py mcp_server.py
python ../S4/call_tool.py mcp_server.py            # Windows: python ..\S4\call_tool.py mcp_server.py
```

You should see two tools listed, `FactoryDesk` for `A03`, a `NOT_FOUND` for `A99`, and then two escalations for `A02`: the second says `already_open: true`. In class you ask Claude Code to write `mcp_server.py` first, and copy the fallback over it only if that fails.

## 5. Obsidian and the starter vault

1. Download Obsidian from https://obsidian.md and install it.
2. Choose "Open folder as vault" and pick `ai-builds/S4/dhruva-vault`.
3. Open the note `thesis` and click the link to `anti-thesis`.

## 6. Register the server with Claude Code (optional, after step 4 works)

Use the full path to the Python inside your virtual environment:

```
claude mcp add dhruva -- /full/path/to/dhruva-triage/.venv/bin/python /full/path/to/dhruva-triage/mcp_server.py
claude mcp list
```

On Windows, the Python is at `.venv\Scripts\python.exe`. Inside Claude Code you can also type `/mcp`. `dhruva` should show as connected.

## Do not

- Do not install any extra Claude Code add-ons or skills before class. We show one on screen.
- Do not put an API key in a note or in your code.
- Do not commit `.venv/`.

## If something fails

| You see | Do this |
|---|---|
| `No matching distribution found for mcp` | Python is 3.9 or lower. Use 3.10 or newer |
| `No module named 'mcp'` | The environment is not active. Run the `activate` line again |
| `python: command not found` (Mac) | Use `python3` or `python3.11` |
| `call_tool.py` cannot find the server | Run it from the `dhruva-triage` folder, and check `mcp_server.py` is there |
| `claude mcp list` shows `dhruva` as failed | Use the full path to the venv's Python, not just `python` |
