# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| reddit-robloxdev (HTTP 429) | 3 | Rate limited: reduce frequency; do not retry immediately. |

Never assume a Google News result is original media or that a 200 response proves content quality.
