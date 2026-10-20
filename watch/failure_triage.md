# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| automation (HTTP 503) | 1 | Investigate public URL and source schema. |
| brock-ig-reels (HTTP 503) | 1 | Investigate public URL and source schema. |
| brock-tiktok (HTTP 503) | 1 | Investigate public URL and source schema. |
| brock-x (HTTP 503) | 1 | Investigate public URL and source schema. |
| reddit-robloxstudio [cooling down — not retried] (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |
| roblox-animation-showcases (HTTP 503) | 1 | Investigate public URL and source schema. |
| roblox-dev-scripts (HTTP 503) | 1 | Investigate public URL and source schema. |
| roblox-news (HTTP 503) | 1 | Investigate public URL and source schema. |
| syphodev-claude (HTTP 503) | 1 | Investigate public URL and source schema. |
| tizzy-roblox-design (HTTP 503) | 1 | Investigate public URL and source schema. |
| x-ui (HTTP 503) | 1 | Investigate public URL and source schema. |

Never assume a Google News result is original media or that a 200 response proves content quality.
