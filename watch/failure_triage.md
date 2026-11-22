# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| youtube-UC1g8RAPLVidtYUzZFFiX2GA (HTTP 404) | 233 | Investigate public URL and source schema. |
| reddit-robloxdev [cooling down — not retried] (HTTP 429) | 13 | Rate limited: reduce frequency; do not retry immediately. |
| reddit-robloxstudio (HTTP 404) | 13 | Investigate public URL and source schema. |

Never assume a Google News result is original media or that a 200 response proves content quality.
