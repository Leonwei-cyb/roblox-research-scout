# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| youtube-UC1g8RAPLVidtYUzZFFiX2GA (HTTP 404) | 224 | Investigate public URL and source schema. |
| reddit-robloxdev (HTTP 429) | 7 | Rate limited: reduce frequency; do not retry immediately. |
| reddit-robloxstudio (HTTP 404) | 7 | Investigate public URL and source schema. |

Never assume a Google News result is original media or that a 200 response proves content quality.
