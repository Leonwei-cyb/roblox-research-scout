# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| youtube-UC1g8RAPLVidtYUzZFFiX2GA (HTTP 404) | 234 | Investigate public URL and source schema. |
| reddit-robloxstudio (HTTP 404) | 14 | Investigate public URL and source schema. |
| reddit-robloxdev [cooling down — not retried] (HTTP 429) | 13 | Rate limited: reduce frequency; do not retry immediately. |
| automation (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |
| brock-tiktok (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |
| roblox-news (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |

Never assume a Google News result is original media or that a 200 response proves content quality.
