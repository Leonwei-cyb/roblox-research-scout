# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| youtube-UCjiPEaapiHbJMoAdi_L8fNA (HTTP 500) | 2 | Investigate public URL and source schema. |
| youtube-UCl-BrQMfynC7mpPDsg6MqlQ (HTTP 404) | 2 | Investigate public URL and source schema. |
| reddit-robloxdev (HTTP 429) | 1 | Rate limited: reduce frequency; do not retry immediately. |

Never assume a Google News result is original media or that a 200 response proves content quality.
