# Verdict: Store Analytics Assistant v1

| Line | Verdict |
|---|---|
| 1. Ship or not | Ship to one pilot: a few store managers and one regional manager, with an analyst checking answers for the first two weeks. Do not ship wider yet. The isolation is enforced in code and holds, but the free tier cannot carry a burst, and results vary from run to run. |
| 2. Score | Golden set 28 of 28 and held-back 6 of 6 in the final run. Earlier runs of the same design scored 24, 25, 27 and 28, so treat 25 to 28 as the honest range. Leak and injection cases pass 5 of 5, and 27 unit tests pass, including attacks on the authorizer. |
| 3. Cost | About Rs 0.08 per uncached question (measured: Rs 0.073 in one eval, about Rs 0.08 in the last), against the Rs 0.50 ceiling. Cache hits cost Rs 0. Monthly bill if no question were ever cached: about Rs 1,100 at 1x (500 a day), Rs 11,000 at 10x and Rs 110,000 at 100x. A 50% hit rate halves each. The Rs 1,500 budget holds at 1x only. Rs 90 per USD is assumed, and the large model's price doubles on 2027-01-01. |
| 4. Weakest point | Provider rate limits. The free tier allows 15 requests a minute per model, so about 7 uncached questions a minute. Under a burst of 60 requests, 6 failed and p95 reached about 120 s against a 10 s target. The large model allows only 20 requests a day on the free tier, so the cascade is not usable there. You would notice it as 429 errors and queue waits in `token_log.db` and `load_test.py`. |
| 5. Next | Build next: move to a paid tier or a second provider so the limits stop being the ceiling, then re-run `load_test.py` and the golden set on the exact models chosen. Do not build yet: charts, forecasting, voice or a UI, because none of them makes the number more trustworthy. |

## What is not proven
- The "today" baselines in the PRD (analyst time, Rs per request) are assumptions, not measurements.
- The BI-tool comparison in the PRD was not checked against a real vendor.
- Prices were read from the pricing page through a summary and should be confirmed.
- The 6 load-test failures were all 429s, but I did not confirm per call whether they came from the small or the large model.
- The cache hit rate in the load test is synthetic (15 distinct questions in 60 requests). The real rate is unknown.
