# Existing research scouts: reuse audit (2026-10-18)

Before writing another scraper, inspect these established open-source alternatives. They solve **different** pieces of research automation; none gives free guaranteed access to every TikTok, Instagram and X video.

| Software | Already solves | Costs / dependencies | Gap for our public GitHub Actions bot |
|---|---|---|---|
| [RSSHub](https://github.com/DIYgod/RSSHub) | Thousands of website-to-RSS routes, including many community-supported destinations | Self-hosting usually means a running server; public instances may be rate-limited or unstable; AGPL-3.0 | **Best feed-connector candidate.** Borrow permitted public feed URLs when stable, not an entire RSSHub deployment in a daily short CI job. |
| [changedetection.io](https://github.com/dgtlmoon/changedetection.io) | Detect webpage/JSON/PDF content changes, selector-based alerts, push to notifications | Self-hosted software or optional paid hosted service; browser-rendered pages require browser resources | Use on a small number of high-value release/announcement pages, not as a TikTok/Instagram bypass. |
| [Huginn](https://github.com/huginn/huginn) | Rule-based watch → filter → deliver flows from feeds and pages | Ruby/web process, DB, usually always-on Docker/server | Richer workflows, but heavy for an ephemeral GitHub Actions runner. |
| [OpenMagpie](https://github.com/obris-dev/openmagpie) | Social listening: X, YouTube, Reddit, Hacker News and RSS with topic filtering and digests | Requires self-hosting + an LLM endpoint. A LOCAL Ollama model avoids GPT/Claude API tokens but uses machine/GPU resources. TikTok and Instagram support listed as future work at review date. | Closest **social research product**, good future local trial, **not zero-compute** and not direct TikTok/Instagram coverage today. |
| [FreshRSS](https://github.com/FreshRSS/FreshRSS) | Visual feed reading, tags, retention and source organization | Self-hosted server; no built-in deep understanding of videos | Good optional human-facing dashboard if plain Markdown reports feel awkward. |
| [Scoutpost](https://github.com/buriedsignals/scoutpost-os) | Scheduled investigative scouts of news, public profiles, webpages and social posts; evidence-linked dedup | Self-hosting; parts use OpenRouter/Gemini and Firecrawl, with service costs depending on deployment | More sophisticated research tracking, but mismatched to a zero-model, zero-cost public GitHub-only job. |

## Existing media extractors and real social restrictions

- **[RSSHub social-media routes](https://docs.rsshub.app/en/social-media):** includes TikTok public user feeds (`/tiktok/user/:user`) marked **strict anti-crawler/Puppeteer**, and some Instagram/X routes with authentication/cookie restrictions. A route existing in the docs is **not proof it works from GitHub Actions**, and we will not scrape accounts or store login cookies in public CI.
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp):** already includes many short-form video extractors. Supported-site listing explicitly says extractors can break as sites change. Good candidate for opt-in **metadata checks on verified PUBLIC video links**, not for circumventing access controls or automatically copying videos.
- **[gallery-dl](https://github.com/mikf/gallery-dl):** handles many image/social sources, but X/Twitter media listings commonly need cookies. No credentials in GitHub Actions.
- **[OpenMagpie current connectors](https://github.com/obris-dev/openmagpie):** X/YouTube/Reddit are supported; TikTok/Instagram are on its roadmap. The project warns that some X/YouTube approaches are unofficial and may need browser session cookies. Do not run it on the free public CI with a personal account cookie.
- **[Community experience](https://www.reddit.com/r/selfhosted/comments/1sss1zl/anything_better_than_changedetectionio/):** developers report browser anti-bot challenges even with Playwright/changedetection. This is a signal to keep failure logs and avoid assuming arbitrary social sites can be scraped for free.

The public bot's currently successful TikTok/Instagram/X categories are **Google News indexed headlines**, not actual complete platform feeds or watched clips.

## Adopt only measured improvements

1. **Use RSSHub when native RSS is unavailable** and the route is legally accessible without credentials; label its reliability and respect publisher limits.
2. **Use change detection** only for specific important pages that lack feeds. Monitor public release pages first, not login-gated social accounts.
3. **Keep the lightweight Python scout** for public GitHub Actions: single daily run, zero LLM APIs, source reports plus clear coverage failures, safe config.
4. If wanting actual semantic ranking/deep social listening, **test OpenMagpie locally** on a small set of public sources (with an already-installed local model), then compare insight/time/CPU cost against our manual source reviews. Never claim an indexed post was actually viewed.

**None of the following is solved by automatic feed aggregation:** directly watching 60-second TikTok/Instagram Reels, judging 3D models or UI animations, determining IP rights for assets, or proving what makes a Roblox game enjoyable. These require original-media inspection.

Source verification: the original GitHub README and project docs of each tool, reviewed October 18, 2026. These are research recommendations, not software installed or security-audited.
