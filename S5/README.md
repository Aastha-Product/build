# S5: One agent, then an orchestrator (Google ADK)

You build the same Dhruva assistant twice and measure whether splitting it into specialists earns its cost.

| File | What it is |
|---|---|
| `dhruva_tools.py` | Four tools: `list_applications`, `get_application`, `score_application`, `escalate_to_analyst`. The type hints and docstrings are the job cards the model reads |
| `dhruva_core/` | Dhruva's loader, scoring and guard code, with the six applications and their cached assessments. Scores are the same on every run |
| `dhruva_v1/agent.py` | v1: one agent with all four tools. Use it only if Claude Code could not produce one |
| `dhruva_v2/agent.py` | v2: an interaction agent that talks to Ira and hands work to an analyst agent and an ops agent. Same rule |
| `scenarios.csv` | The 5 core questions both versions answer (`scenarios_extra.csv` has 5 more) |
| `eval_agent.py` | Runs the 5 questions and prints pass rate, model calls per query and latency |

## Setup (about 15 minutes)

Python 3.10 or newer. If you did S4, use the same virtual environment: `google-adk` and `mcp` install side by side.

```
git clone https://github.com/Ekta-Shah/ai-builds.git     # or: git pull
cd ai-builds/S5
python -m venv .venv                       # Mac: python3.11 -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install google-adk python-dotenv
cp .env.example .env                       # Windows: copy .env.example .env
```

Open `.env` and paste your Gemini key after `GOOGLE_API_KEY=`. A free key from https://aistudio.google.com/apikey works. If you already have `GEMINI_API_KEY` set from S1, that works too. Do not commit `.env`.

Check the tools, which need no key:

```
python -c "import dhruva_tools as t; print(t.score_application('A03'))"
```

You should see FactoryDesk, fit 7.5, `ADVANCE TO CALL`. Then check the agent talks to Gemini:

```
adk web
```

Open http://localhost:8000, choose `dhruva_v1` at the top left, and ask "Should we take a call with FactoryDesk?". `adk web` is for development only.

## Run the comparison

```
python eval_agent.py dhruva_v1
python eval_agent.py dhruva_v2
```

Each prints one line per question and a summary: passed, model calls per query, median latency, tokens. It also saves `results_<name>.csv`.

A free key limits requests per minute and per day. Add `--rpm 5` to stay under the per-minute limit; it waits between calls and does not count the wait as latency. `--all` adds five more questions and about doubles the calls: do not use it on a free key. On the key we tested, `gemini-2.5-flash` allowed only 20 requests a day, which is less than one full run of both versions, so the default is `gemini-flash-lite-latest`.

## If something fails

| You see | Do this |
|---|---|
| `No module named 'google'` | The environment is not active. Run the `activate` line again |
| `API key not valid` or `403` | The key is wrong or missing in `.env`. Paste it after `GOOGLE_API_KEY=` with no quotes or spaces |
| `429` or `RESOURCE_EXHAUSTED` | A per-minute or per-day limit. Use `--rpm 5`. A daily limit resets after some hours: try another model with `DHRUVA_MODEL` in `.env`, or share a neighbour's screen |
| `model not found` (404) | That model name is not available to your key. Set `DHRUVA_MODEL` in `.env` to one that is, such as `gemini-flash-lite-latest` |
| `503 UNAVAILABLE` | Gemini is busy. Wait a minute and run again; `eval_agent.py` retries twice by itself |
| `adk: command not found` | Activate the environment, or use `python -m google.adk.cli web` |
| The dev UI lists no agents | Run `adk web` from the `S5` folder, not from inside `dhruva_v1` |
