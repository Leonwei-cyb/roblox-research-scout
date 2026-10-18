# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| apple-appstore-ca-games-subset [cooling down — not retried] (The read operation timed out) | 1 | Timeout: try later; preserve last good report. |
| apple-appstore-us-games-subset [cooling down — not retried] (The read operation timed out) | 0 | Timeout: try later; preserve last good report. |
| reddit-claudeai [cooling down — not retried] (HTTP 429) | 0 | Rate limited: reduce frequency; do not retry immediately. |
| reddit-claudecode [cooling down — not retried] (HTTP 429) | 0 | Rate limited: reduce frequency; do not retry immediately. |
| reddit-robloxdev [cooling down — not retried] (HTTP 429) | 0 | Rate limited: reduce frequency; do not retry immediately. |

Never assume a Google News result is original media or that a 200 response proves content quality.
