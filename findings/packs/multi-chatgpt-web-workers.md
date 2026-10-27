# Query pack: Multiple ChatGPT web workers \(browser-session orchestration, not API-only\)

Problem-first GitHub search, one bounded run. Not full GitHub coverage: GitHub search returns at most 15 results per query here, ranked by GitHub's own relevance.

- Run: 2026-10-27T12:41:24Z (schedule) - **PARTIAL**: search stopped early: GitHub rate limit for /search/repositories
- API calls: 21 total (rest 21)
- Distinct repos found: 68; inspected: 0

## Rediscovery check (known repos were NOT used as search input)

- Xalzeroph/Charterion: **not found** by this run
- megamen32/chatgpt-multi: **not found** by this run
- paritoshv/multi-llm-web-orchestrator: **not found** by this run

## Ranked candidates

| # | Repo @ SHA | Mode | Pack verdict | Score | Why |
|---:|---|---|---|---:|---|

## Searches

- pack:multi-chatgpt-web-workers:a:strict: ok (13 results)
- pack:multi-chatgpt-web-workers:a:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:b:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:b:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:c:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:c:relaxed: deferred GitHub rate limit for /search/repositories

Verdicts are pack-specific. Only a tested review in findings/reviews can make anything adopt.
