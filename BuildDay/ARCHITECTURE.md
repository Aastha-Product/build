# Architecture: Store Analytics Assistant

Principle: anything that must be right every time belongs in code. The model proposes; code decides.
Numbers marked (A) are estimates to replace with measured values from the token meter and `load_test.py`.

## 1. Diagram
```
 user (ana / ravi / meera / hq)
   |  question, user id
   v
[CODE] 1. Identify user -> scope = stores from users.json            (human: none; identity is a given)
   v
[CODE] 2. Cache lookup, key = (user, normalised question, data version)
   |  hit -> return cached answer                                    (skips steps 3-8)
   v  miss
[CODE] 3. Build context: rules + glossary + schema of the user's views + today's date
   v
[MODEL] 4. PLAN call: returns JSON {action: answer|clarify|refuse, assumption, sql}
   |        small model first; escalate to large model on failure (cascade)
   v
[CODE] 5. Validate: SELECT only, one statement, tables are the user's views, no comments
   v
[CODE] 6. Execute: read-only connection, SQLite authorizer, timeout, row limit
   |        error -> one repair loop back to step 4 (max 1 retry)
   v
[MODEL] 7. NARRATE call: rows + assumption -> one sentence (skipped for clarify/refuse)
   v
[CODE] 8. Assemble {rows, text, sql, tokens_in, tokens_out}; write cache; log token meter
   v
 user sees: a number, one sentence, the assumption, and the SQL on request

 Human sits: behind HQ analyst review of the weekly eval report and any glossary change.
 There is no human in the per-question path in v1.
```
Replace first if the model changes: boxes 4 and 7 (model calls) and the model names in `config.json`. Everything else is model-independent.

Never sent to the model: other stores' rows, store `notes`, and any row data beyond the capped result in step 7.

## 2. Decisions
| Decision | Options | Choice | Why | Cost or risk |
|---|---|---|---|---|
| One call or several (pipeline vs agent) | Single call; fixed pipeline (plan then narrate); free-running agent with tools | Fixed pipeline: plan call, code execution, narrate call | Questions are one-shot and the steps are known, so an agent adds loops, cost and unpredictability. Two calls keep every step testable in the eval. | Two model calls per miss. Multi-step questions such as "why did my margin drop" must fit in one SQL or be answered from one result. |
| What the model writes (SQL, a plan, an answer) | Final answer text; a query plan in JSON; SQL | SQL (a single SELECT) inside a small JSON envelope that also carries action and assumption | Numbers come from the database, never from the model's arithmetic. The eval compares against gold SQL results. | Model can write wrong SQL, so validation, one repair retry and the eval gate are needed. |
| Where isolation is enforced (prompt vs code) | Prompt instruction; code | Code only. Per-user temporary views (`sales`, `stores` filtered to the user's stores), a SQLite authorizer that denies the base tables, and a read-only connection | A control that lives only in the prompt is a request, not a control. Cases 21-25 test this. | Views must be created per query or per connection. `products` is not store-specific and stays shared. |
| What context we send (full schema vs retrieved) | Full schema and glossary every call; retrieved glossary sections | Full glossary and the schema of the user's views on every call (3 tables, 7 metrics) | The glossary is about 1,100 tokens (A), so retrieval saves little and risks dropping a definition. | Does not scale to 500 stores or hundreds of tables (rung 4). Then switch to retrieval over tables and metrics. |
| Model tiers (one model vs cascade) | One model; small model first and escalate; large model only | Cascade. Small model for lookup and top-n. If validation or execution fails, retry once on the large model. Model names are in `config.json`. | Most questions are simple, and the cascade cuts cost and latency. The eval shows whether the small model is enough. | Two models to evaluate. Routing by question kind needs a cheap classifier or a rule. |
| Caching | None; exact-match cache; semantic cache | Exact-match cache on (user, normalised question, data version). The user is part of the key. | Managers repeat questions, and rung 2 first breaks on repeats and rate limits. Including the user stops one user seeing another's answer. | Stale answers after a data refresh, so the key includes a data version and entries have a TTL. A semantic cache risks wrong matches, so it is not in v1. |
| Sync vs queued | Synchronous request; queue with a worker pool | Synchronous with a concurrency limit and retry with backoff on rate limits | 500 questions a day is about 1 every 3 minutes on average (A), so peaks are the only concern. | At rung 3 (50,000 a day) move to a queue with a worker pool and a result poll. |
| Where state lives | In memory; SQLite; external store | `retail.db` for data (read-only). Cache and token log in a separate small SQLite file. No conversation state. | Stateless questions keep the cache key and the eval simple. A separate file keeps the data database read-only. | A single-file cache does not scale across servers. Use a shared store at rung 3. |

## 3. Threat model
| Attack | Who | Blast radius | Defence (code or prompt) |
|---|---|---|---|
| "Show me every store's numbers" / "What were S07's net sales?" (cases 21-23) | A curious manager | Another store's data | Code. The user's views contain only their stores; the authorizer denies the base `sales` and `stores` tables. A cross-store query returns empty or errors, and the narration says the data is outside their access. Prompt text only explains the refusal. |
| Instruction hidden in a product name or store note (cases 24-25) | The data itself, or a user pasting "ignore all previous instructions" | The model follows it and widens the query | Code, then prompt. Store `notes` are never sent to the model. Product names are passed as data in a delimited block. The glossary rule says to ignore instructions in data. Even if the model obeys, step 5 and the authorizer in step 6 still apply. |
| A query that scans everything | A bad generation | Slow database for everyone | Code. Timeout via SQLite progress handler, row limit, and a required date filter on `sales` for non-aggregate queries. |
| A write or drop statement | A bad generation or an injection | Lost or changed data | Code. A SELECT-only validator rejects anything else, multi-statements are blocked, the connection is opened read-only, and the authorizer denies write operations. |
| The same question from two users | The cache | One user sees the other's answer | Code. The cache key includes the user id, and the eval runs the same question as two users and compares. |
| Leaking through the log or narration | Anyone with log access | Other stores' figures in logs | Code. Only the user's own rows reach the narrate call. Logs store question, user, tokens and SQL, not result rows. |

## 4. Scale ladder
| Rung | Load | First thing that breaks | Our fix |
|---|---|---|---|
| 1 | 1 user | Nothing. Skipped: auth, rate limits, cache | Note what was skipped and move on. |
| 2 | 50 managers, 500 questions a day | Free-tier rate limits, and the same question asked again and again | Exact-match cache, retry with backoff, concurrency limit. Measure with `load_test.py`: failures, cache hits, p95. |
| 3 | 5,000 users, 50,000 a day | Cost and concurrency | Cascade to the small model by default, a daily budget cap, a queue with a worker pool, a shared cache. |
| 4 | 500 stores, 50 million rows | The schema no longer fits in the prompt, and scans are slow | Retrieve only the relevant tables and metrics, move to a columnar or warehouse database, add indexes and pre-aggregated daily tables. |
| 5 | Many tenants, one regulated | Leakage between tenants, and a noisy neighbour | Separate database or schema per tenant, per-tenant cache and quotas, audit logging. |
| 6 | A model is retired or repriced | Everything that hard-coded a model name | Model names and prices only in `config.json`, and the golden set as the regression gate for any swap. |

## 5. Token budget per question
Estimates (A), measured later with the token meter (slice 5).

| Part | Tokens in | Tokens out | Can we cut or cache it? |
|---|---|---|---|
| Rules and glossary | 1,400 | 0 | Yes. This is a fixed prefix, so use the provider's context caching. It is the largest cost and the same on every call. |
| Question | 30 | 0 | No. It is small. |
| Plan call (schema and date added) | 300 | 150 | Schema is mostly fixed, so cache it. Output is the SQL plus the assumption, so keep the JSON compact. |
| Narration call | 250 (rows capped at 20 plus the assumption) | 60 | Skip for clarify and refuse. Cap rows and answer in one sentence. |
| Total per cache miss | about 2,000 | about 210 | Cache hits cost 0. |

Cost ceiling: stay under Rs 0.50 per question (PRD metric 3). The exact rupee figure comes from the model prices in `config.json`, which this document does not hard-code. Check at 1x (500 a day), 10x and 100x using the measured tokens per question and the cache hit rate from `load_test.py`.
