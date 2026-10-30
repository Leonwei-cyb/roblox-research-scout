# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| reddit-robloxdev [cooling down — not retried] (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |
| roblox-devforum-latest (no element found: line 1, column 0) | 1 | Investigate public URL and source schema. |
| roblox-devforum-updates (no element found: line 1, column 0) | 1 | Investigate public URL and source schema. |
| roblox-ui-showcase (no element found: line 1, column 0) | 1 | Investigate public URL and source schema. |
| roblox-wip-2026 (no element found: line 1, column 0) | 1 | Investigate public URL and source schema. |

Never assume a Google News result is original media or that a 200 response proves content quality.
