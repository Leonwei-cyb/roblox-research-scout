# Query pack: Multiple ChatGPT web workers \(browser-session orchestration, not API-only\)

Problem-first GitHub search, one bounded run. Not full GitHub coverage: GitHub search returns at most 15 results per query here, ranked by GitHub's own relevance.

- Run: 2026-10-21T21:59:21Z (schedule) - **PARTIAL**: search stopped early: GitHub rate limit for /search/code
- API calls: 30 total (rest 30)
- Distinct repos found: 152; inspected: 0

## Rediscovery check (known repos were NOT used as search input)

- Xalzeroph/Charterion: **not found** by this run
- megamen32/chatgpt-multi: **not found** by this run
- paritoshv/multi-llm-web-orchestrator: **not found** by this run

## Ranked candidates

| # | Repo @ SHA | Mode | Pack verdict | Score | Why |
|---:|---|---|---|---:|---|

## Searches

- pack:multi-chatgpt-web-workers:a:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:a:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:b:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:b:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:c:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:c:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:d:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:d:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:e:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:e:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:f:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:f:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:g:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:g:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:s1:source: deferred GitHub rate limit for /search/code

Verdicts are pack-specific. Only a tested review in findings/reviews can make anything adopt.
