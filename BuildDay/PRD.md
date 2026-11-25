# PRD: Store Analytics Assistant (v1)

Status: final for v1. Numbers marked (A) are assumptions to confirm; everything else comes from the data, `glossary.md`, `users.json` or `golden_questions.csv`.

## 1. Problem in one line
"Store managers ask a question in plain English and get a trusted number."

Trusted means: the number follows the glossary definition, the assumption behind it is stated, and the person asking only ever sees stores they are allowed to see. A refusal or a clarifying question is better than a confident wrong number.

## 2. Users and jobs
| User | Job they do today | How they do it today | What it costs them |
|---|---|---|---|
| Store manager (e.g. Ana, S03; Ravi, S07) | Check yesterday's and last month's sales, margin, returns and best sellers; decide reorders and promotions | Asks head office for a report, or eyeballs the POS screen (A) | Waits hours to days; reorders on stale or wrong figures; cannot see why margin moved |
| Regional manager (Meera, West: S01-S04) | Compare her stores weekly and spot the weak one | Requests a spreadsheet per store and stitches it together (A) | A weekly manual job; comparisons that mix definitions of "sales" |
| Head office analyst (HQ, all 12 stores) | Answer ad-hoc questions from managers; run the Monday review | Writes SQL or builds one-off reports by hand (A) | Becomes the bottleneck for every simple question; repeats the same queries |

## 3. Success metrics (write the number, not the adjective)
| Metric | Today | Target | How we measure |
|---|---|---|---|
| Answer correctness on the golden set | 0 of 28 (no assistant exists) | At least 90% on the 22 open questions and at least 80% on the 6 held-back questions | `python eval_sql.py --impl <file>`, then `--holdout` for the held-back set |
| Cross-store leaks (leak and injection cases) | n/a | 0 failures, always, no tolerance | Leak and injection cases 21-25 in the eval; any failure blocks release |
| Time to answer | Hours to days via head office (A) | Median under 5 s, p95 under 10 s | `load_test.py` and the `secs` column of the eval |
| Cost per question (Rs) | Analyst time, roughly Rs 50-100 per ad-hoc request (A) | Under Rs 0.50 per question | Token meter: `tokens_in` and `tokens_out` times the model price in `config.json` |
| Questions a manager can self-serve | 0% | At least 80% of lookup, aggregate, trend and top-n questions answered with no analyst | Share of those four kinds that pass in the golden set |

## 4. Scale target
Users: 4 in the demo, 50 managers at launch  Questions per day: 500  Stores: 12 (12 now, 500 later)  Rows: about 220,000 (223,702 sales lines)  p95 latency: 10 s  Budget per month (Rs): 1,500 for model calls (A: 500 questions a day x 30 days x Rs 0.10 effective cost with caching)

Scale ladder reference: rung 2 (50 managers, 500 questions a day) is the v1 target. Rungs 3 to 6 are designed for in `ARCHITECTURE.md` but not built.

## 5. In scope for v1
1. A question box over fixed data: plain-English question in, a number plus one sentence out, with the assumption stated.
2. The model writes one SELECT; code runs it read-only with a timeout and a row limit.
3. Per-user store scoping enforced in code (views per user plus a SQL authorizer), using `users.json`.
4. The glossary as the semantic layer: "sales" means net sales and the answer says so. "Last month" is the previous calendar month; today is 2026-11-22.
5. Refuse or clarify: unanswerable questions (customers, competitors, S11 year over year) and ambiguous ones ("best store", "recently").
6. Answer kinds covered: lookup, aggregate, trend, top-n, diagnose, ambiguous, leak, injection, unanswerable.
7. Token and cost meter on every answer; caching of repeated questions with a cache key that includes the user.
8. Eval harness and load test run as the release gate.

## 6. Not in v1 (and why)
| Not in v1 | Why |
|---|---|
| Write access of any kind (insert, update, delete, drop) | A manager asking a question must never be able to change data. The code opens the database read-only. |
| Charts, dashboards and exports | The job is a trusted number. Visuals add build time and no trust. |
| Voice, WhatsApp or a mobile app | The question box proves the core first. A channel is a wrapper added later. |
| Live POS or streaming data | Data is batch, current to 2026-11-22. Freshness is a separate pipeline. |
| Customer-level, footfall or competitor data | Not in the database. The assistant must say it does not have this, not guess. |
| Forecasting and what-if questions | Needs a forecasting model and its own evaluation. A wrong forecast reads as fact. |
| Multi-tenant isolation and more than 12 stores | Rungs 4 and 5 of the scale ladder. Not needed to prove the product. |
| Following up in a multi-turn conversation | Each question is answered alone, which keeps the eval and the cache key simple. |
| A web UI or framework | Core first. `CLAUDE.md` says no web framework until the core works. |

## 7. Risks (what is the worst wrong answer, and who gets hurt)
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A manager sees another store's data (including via "ignore all previous instructions", or a cached answer from another user) | High if enforced only in the prompt | Severe: confidential figures exposed, trust lost | Isolation in code, not prompt. Views per user, a SQL authorizer that blocks other stores, and a cache key that includes the user. Eval cases 21-25 must show 0 leaks. |
| A wrong number is acted on (wrong metric definition, wrong period, returns ignored) | Medium | High: bad reorders and wrong promotions | Glossary in context, stated assumption on every answer, gold-SQL comparison in the eval, refuse or clarify when ambiguous. The query is shown so an analyst can verify it. |
| Instruction hidden in data (product name or store `notes`) is followed | Medium | High: model behaviour is hijacked | Data is data. The glossary says never to follow instructions found in data values. Free-text columns are not sent to the model unless needed. Injection cases 24-25 in the eval. |
| A query scans everything, or writes | Low to medium | Medium: slow database, or lost data | Read-only connection, query timeout, row limit, SELECT-only check in code. |
| Cost runs away | Medium at 100x | Medium: budget blown | Token meter per question, cache repeated questions, send only the needed schema, cascade to a cheaper model for simple lookups, a monthly budget cap in `config.json`. |
| The model is deprecated or the price changes | Certain over time | Medium: outage or a price jump | Model names and prices live in `config.json`, not in code. The eval is the regression gate for any model swap. |
| Free-tier rate limits and concurrency fail at 50 managers | High | Medium: failed questions at peak | Cache, retry with backoff, queue under load. Confirm with `load_test.py` (failures and p95). |

## 8. Build, buy or configure
Options considered: (a) buy or configure an existing BI tool with natural-language query, such as Power BI Q&A or Looker; (b) a generic chat assistant over the database; (c) a custom text-to-SQL assistant with scoping in code.
Chosen: (c) a custom assistant, with a thin pipeline: question, then the model writes SQL, then code validates and runs it read-only, then the answer is narrated.
Because: BI tools do not enforce per-store scoping and the glossary's metric definitions the way this product needs without a heavy setup (A: confirm against a real BI vendor before launch), and a generic chat assistant puts isolation in the prompt, which is a request and not a control. The data is small, so the build is small. Revisit buy if the store count reaches the hundreds.

## 9. Open questions
1. Who owns the glossary, and who approves a change to a metric definition?
2. What is the real cost of an analyst request today? This is the baseline for the cost-per-question target.
3. Is the S11 caveat (no data before 2026-03-01, no year over year) shown to the user automatically, or only when asked?
4. How long do cached answers live, given that data refreshes?
5. What may be logged? Question text may contain store names, and answers contain figures. Decide the log policy and retention.
6. Should an "all-stores" question from a regional manager return only the stores she may see, or refuse? The eval accepts a scoped answer or a refusal; pick one rule.
7. What is the monthly budget in rupees, and who is alerted at 80%?
