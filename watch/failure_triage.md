# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| youtube-UC1g8RAPLVidtYUzZFFiX2GA (HTTP 404) | 244 | Investigate public URL and source schema. |
| reddit-robloxstudio (HTTP 404) | 22 | Investigate public URL and source schema. |
| reddit-robloxdev [cooling down — not retried] (HTTP 429) | 20 | Rate limited: reduce frequency; do not retry immediately. |

Never assume a Google News result is original media or that a 200 response proves content quality.
