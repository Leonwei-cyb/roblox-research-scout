# Source failure triage

Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.

| Source | Consecutive observed failures | What to do |
|---|---:|---|
| reddit-robloxstudio [cooling down — not retried] (HTTP 429) | 2 | Rate limited: reduce frequency; do not retry immediately. |
| youtube-UC1g8RAPLVidtYUzZFFiX2GA (HTTP 404) | 2 | Investigate public URL and source schema. |
| youtube-UCjiPEaapiHbJMoAdi_L8fNA (HTTP 404) | 2 | Investigate public URL and source schema. |
| youtube-UCl-BrQMfynC7mpPDsg6MqlQ (HTTP 500) | 2 | Investigate public URL and source schema. |

Never assume a Google News result is original media or that a 200 response proves content quality.
