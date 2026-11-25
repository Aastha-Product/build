# Slice plan (each slice ends with a test run and a decision-log line)

Golden question ids by kind: lookup 1-5, aggregate 6-12, trend 13-15, diagnose 16, top-n 17, ambiguous 18-20, leak 21-23, injection 24-25, unanswerable 26-28. Held back: 7, 13, 19, 22, 26, 28.

Rules for every slice:
- Run `python eval_sql.py --impl assistant.py` at the end and paste the score into the decision log. The default rate of 12 requests a minute makes a full run take about 2.5 minutes.
- Read the diff before starting the next slice. Do not tune prompts to the held-back ids; look at the held-back result only at slice 6.
- A score that drops from the previous slice is a stop, not a note. Fix it or revert the slice.

| Slice | What gets built | Done when | Golden ids that should pass | Decision-log line |
|---|---|---|---|---|
| 0 | Walking skeleton: `assistant.py` with `answer(question, user)` returning the dict `{rows, text, sql, tokens_in, tokens_out}` with a hard-coded answer. `config.json` with model names, limits and the cache TTL. `.env` loaded. | `eval_sql.py` runs end to end and scores near zero. `load_test.py` imports it without error. | None, apart from by luck | Baseline score and why the dict shape is fixed |
| 1 | Plan call: the model returns JSON `{action, assumption, sql}`. Validator: one SELECT, no comments, no multi-statement. Read-only connection, timeout, row limit. One repair retry on a SQL error. Dev-only: full access, no scoping yet. | Lookup, aggregate, trend and top-n cases pass: 1-4, 6-15 and 17. Writes and multi-statements are rejected by a unit test. | 1, 2, 3, 4, 6-15, 17 (case 5 needs scoping) | Which model, and the Rs or tokens per question |
| 2 | Scope in code: per-user views of `sales` and `stores` built from `users.json`, a SQLite authorizer that denies the base tables, and the validator restricted to the user's views. Store `notes` removed from the model's context. | All leak and injection cases pass, and cases 5 and 10 (the regional manager) pass. A test shows the authorizer blocks `sales` even if the model writes it. | 5, 21, 22, 23, 24, 25 | Prompt vs code isolation, and what the model can no longer see |
| 3 | Glossary and today's date in context. The `assumption` field is shown in the answer. Net sales is the default meaning of "sales", and the answer says so. | Ambiguous cases pass, and the diagnose case passes (it needs beverage and discount in the reply). | 16, 18, 19, 20 | Full glossary vs retrieved, and the token cost of the glossary |
| 4 | Refuse and clarify behaviour: `action` of `refuse` for missing data (customers, competitors) and `clarify` for vague questions. S11 year over year is answered with the opening date, not a number. | Unanswerable cases pass. No answer to an unanswerable case contains an invented number. | 26, 27, 28 | What counts as unanswerable, and who decides |
| 5 | Narration call: rows plus assumption become one sentence, skipped for clarify and refuse. Token meter: `tokens_in` and `tokens_out` on every answer, and a token log in a separate file. | Tokens per question are printed in the eval, and the score has not dropped. Rows sent to narration are capped. | All previous ids still pass | Measured tokens vs the 2,000 in / 210 out estimate in `ARCHITECTURE.md` |
| 6 | Cache keyed on (user, normalised question, data version) with a TTL. Cascade: small model first, escalate to the large model on a validation or execution failure. Retry with backoff on rate limits. | `load_test.py` shows fewer model calls, cache hits above zero and no failures. A test shows two users asking the same question never share an answer. Held-back result read once and written down. | All 28 | Cache hit rate, cascade savings, and the bill at 1x, 10x and 100x |

## After slice 6
Write the five-line verdict from the slides: ship or not, score (open and held-back), cost per question and the bill at 1x, 10x and 100x, the weakest point, and what to build next and what not to.
