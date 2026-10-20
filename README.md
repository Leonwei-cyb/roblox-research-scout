# Roblox Research Scout

**Public, no-AI-token research monitors for Roblox Studio, Claude Code, open-source tools and game-development showcases.**

This is a PUBLIC repository. Everything gathered here is public information, and the workflows never access the owner's private games or chats.

## What the bots do

- **GitHub Scout:** watches official releases, new tool repositories and public source changes.
- **Media Scout:** checks public Roblox and Claude feeds, YouTube channel uploads, news, developer forums, Reddit where available, and limited indexed leads for TikTok/X/Instagram.
- **Research Digest:** stores deduplicated, source-linked findings and reports sources that are blocked. Titles and excerpts are discovery leads, **not** a claim that the video or game was personally watched.

## Using it

- **Reports:** after the first successful run, open [watch/latest.md](watch/latest.md), [watch/media_brief.md](watch/media_brief.md) and the stricter [watch/video_candidates.md](watch/video_candidates.md). A link is not a claim anyone watched the video.
- **Curated example set:** [research/VIDEO_PILOT_2026-10-18.md](research/VIDEO_PILOT_2026-10-18.md) contains source-confirmed video/watch pages plus clearly labeled X/Instagram account leads.
- **Source coverage:** check [watch/source_health.md](watch/source_health.md) for blocked or failed feeds.
- **Configuration:** [watch/config.json](watch/config.json) and [watch/feeds.json](watch/feeds.json).
- **Actions:** the existing research workflow runs hourly (cron `23 * * * *` since 2026-10-19), plus relevant source/config changes; urgent scans can be run manually. Independent health checks react to completions and run on an hourly fallback.
- **Tests:** `python3 -m unittest discover -s tests -v`.

## Game and topic research specialists (one shared bot)

The Mac's existing `com.leon.research-scout` launchd job remains the **only**
research process. `scripts/discovery_scout.py` now uses `scripts/research_lanes.py`
to rotate GitHub search queries fairly across the specialists configured in
[`watch/discovery.json`](watch/discovery.json):

- Cat Magic School (highest weight while it is the active game)
- One Tower Tycoon
- Anime Fortress
- Roblox art, UI and animation
- Roblox engineering and performance
- AI / Codex tools
- Leon reliability tools
- Unexpected open-source gameplay ideas

**Change priorities without writing code:** edit `research_lanes[].weight`
(0 pauses a lane) or `research_lanes[].enabled`, and
`active_projects` to move game-specific candidates to the top of the
evaluation backlog. To add another game, add topic queries under `topics`
and reference those topic IDs in a new `research_lanes` entry. The
weights share **one bounded search budget** (`max_search_queries`, still 15
topic queries per discovery run), not separate budgets or new API accounts.
Enabled lanes receive one query each when that budget allows; remaining
queries are weighted and rotate between runs. Existing problem-first query
packs may make additional calls under the same GitHub rate-limit guard.

Outputs to `status/discovery.json`: `research_lanes` with selected,
completed, deferred and failed queries per specialist; `active_projects`;
and game-prioritized candidates in `backlog`. The ordinary candidates
store is shared, deduplicated by GitHub repository ID/version. Only
independently tested `findings/reviews/` records can say **adopted**.
Neither a search result nor a green status means a game was improved.

**Mac operation:** the existing hourly local research cycle and
approximately six-hour discovery interval remain unchanged. Locally
running these scripts uses no GitHub-hosted Actions minutes, but consumes
Mac resources and GitHub API quotas. This PR does not install a new
scheduler or increase request frequency. Check the real run receipt and
rate-limit fields before claiming the new specialist configuration is active.
No paid models, automated Instagram/X login, game publishing or
third-party code installs are enabled.

**Offline tests:** `python3 -m unittest discover -s tests -p 'test_discovery*.py'`.

## Research must become tested game work

Research is **not** a production milestone. The collection has previously amassed hundreds of entries, dominated by search redirects that have no verified original gameplay. The current focused feed set pauses low-yield broad Google News searches and incomplete Apple chart polls. Historical `watch/media_state.json` remains intact: paused searches can be reinstated for a specific problem, not by default.

Follow this rule before suggesting an implementation: **original source or actual inspected frame → one concrete player-visible defect in an active game → use existing source/tool → make the change → normal player test → evidence-backed acceptance.** If no corresponding real defect, **DEFER** the research. Don't generate a new implementation document/issue or install a tool just because it was discovered. `watch/review_queue.md` now excludes all Google News redirect links and offers at most three primary leads per topic. `watch/source_quality.md` continues to measure the broader stored discovery sample honestly.

Current testable example: [One Tower Tycoon passive rate code review](https://github.com/Leonwei-cyb/one-tower-tycoon/pull/35) implements an observed cash-rate principle from [timestamped tycoon frames](https://github.com/Leonwei-cyb/Roblox-Research/blob/main/findings/TYCOON_GAMEPLAY_FRAME_STUDY_20261018.md). This is code **awaiting integration + Studio visual verification**, NOT a completed game change.

The private [Roblox Development Kit adoption record](https://github.com/Leonwei-cyb/Roblox-Development-Kit/blob/main/ADOPTION.md) tracks what we actually used versus deferred. Source links are not implementation or licensing permission.

## Limits and price

No OpenAI, Claude, Codex or other paid model API is invoked. The standard public GitHub Actions `ubuntu-latest` runner is currently free under GitHub's standard-runner policy. GitHub's fair-use, job/runtime and API rate limits still apply. Other paid services or larger runners are not used.

TikTok, Instagram and X **do not provide unrestricted free authenticated feeds**. We collect only publicly indexed leads and accessible public metadata. In-depth review of actual UI, models and gameplay requires direct media viewing and judgment; collecting posts is not the same as understanding them.

**Security:** The workflow has minimal repository `contents: write` permission to store the reports, no extra secrets, and no access to your private repositories. It doesn't install Roblox plugins, change games, publish content, or use account cookies.

## Existing projects worth reusing

Rather than reinventing a research platform, consider these proven open-source projects for specific needs:

- [RSSHub](https://github.com/DIYgod/RSSHub): website-to-feed routes and social feed integrations.
- [changedetection.io](https://github.com/dgtlmoon/changedetection.io): page-diff monitoring and notifications.
- [Huginn](https://github.com/huginn/huginn): multi-step automation/notification agents.
- [OpenMagpie](https://github.com/obris-dev/openmagpie): social listening on X, YouTube, Reddit and RSS, with local-model support. TikTok/Instagram support is not yet claimed as live.
- [FreshRSS](https://github.com/FreshRSS/FreshRSS): organized feed reading.
- [Scoutpost](https://github.com/buriedsignals/scoutpost-os): journalistic research scouting; parts require external model/services.

Only integrate one when it concretely improves source coverage or saves time. Some require an always-on machine or paid third-party services, so we do not install them automatically.

## Automation bots (all no hosted AI calls)

The scheduled GitHub Actions workflow now runs separately scoped bots, reusing the same public feeds:

- **Release tracker**: public Roblox/Claude repo releases, commits and tool candidates.
- **Video shortlist and creator digest**: source-linked original video URLs and creator accounts, with indexed X/Instagram/TikTok results labeled **unverified**.
- **Game-design/UI/3D review queue**: [ranked sources](watch/review_queue.md) based on observable post titles, not claims of watching a video.
- **Topic keyword radar**: [sampled mentions](watch/topic_signals.md), not popularity or CCU predictions.
- **Coverage auditor**: [blocked sources versus direct media](watch/coverage_audit.md).
- **Public code/asset-license watcher**: [GitHub license metadata](watch/license_audit.md), not permission to reuse proprietary art/code.

For ACTUAL sampled video frames, there is an **opt-in local-only** [video lab](docs/LOCAL_VIDEO_LAB.md). It needs FFmpeg, a local authorized video file and optionally a local Ollama vision model (which uses your device CPU/GPU but NO ChatGPT/Claude/Codex credits). Neither media files nor images get uploaded to this public repo. No public bot actually watches the full original video.

These helpers run within **one lightweight workflow**, not several CPU-heavy watchers. Standard GitHub-hosted public runners are free under GitHub limits; provider APIs/site rate limits, account restrictions and legitimate rights still apply.

## Open-source discovery (agents, Claude/Codex/ChatGPT tools, Roblox tooling, dashboards, MCP, skills, testing)

[`scripts/discovery_scout.py`](scripts/discovery_scout.py) looks for open-source projects that could unblock current Leon work and records a verdict for each. No AI model is called and nothing found is installed or run by the bot.

- **What it searches:** topic queries and problem-first query packs in [`watch/discovery.json`](watch/discovery.json) (GitHub repository search, plus a bounded code search for files only a real solution would contain), a watchlist, carried-forward candidates named by HQ, and up to 5 repos named in a manual or dispatched request.
- **What it checks:** canonical repo (GitHub's numeric id, so renames do not duplicate) and version (latest release, or `head`), the pinned head SHA, license, last commit, releases, open issues and recently updated issues, security policy, tests and CI folders. Query-pack hits also get their README, manifests and key source files read at that SHA and are classified as browser-session orchestration, API-only, mixed or unknown.
- **Verdicts:** `reject` or `needs-test` from automation; **`adopt` only from a tested review** in [`findings/reviews/`](findings/reviews/). A review stops applying when the repo moves to a new version.
- **Outputs:** [`findings/candidates.jsonl`](findings/candidates.jsonl) (one line per repo and version: SHA, license, scores, verdict, suggested owner `Wheel` / `Work/dashboard` / `hub`, one-line task, evidence links), [`findings/SUMMARY.md`](findings/SUMMARY.md), [`findings/packs/`](findings/packs/) (each query pack's ranked report with every API call it made) and [`status/discovery.json`](status/discovery.json) (last run, feed health, counts of adopted findings and the actionable backlog; Dashboard V2 can read it).
- **Routing:** high-value query-pack candidates become at most 3 deduplicated research issues per run **in this repo only** ([`scripts/discovery_issues.py`](scripts/discovery_issues.py)). Nothing is posted to any other repository and nobody is pinged.
- **When it runs:** every 6 hours (best-effort GitHub cron), on pushes that change the discovery code/config/reviews, on manual runs, on `repository_dispatch` type `discovery-scan`, and when a collaborator labels an issue here `discovery-request`. It is polling, **not continuous coverage**: other people's repos cannot send us events, so their releases and issues are seen at the next run.
- **Limits:** ETag conditional requests where GitHub offers them (tree reads; the search API sends no ETag, so every search is a full request), one results page per query, hard caps per run, and a stop (no retry) when GitHub signals a rate limit, honoured until the reset time. GitHub search ranks by its own relevance, so this is never full coverage of GitHub.

## Automatic source backoff

The public media collector now records a temporary cooldown in `watch/media_cooldowns.json` on HTTP 429 (12 hours) or request timeout (6 hours). Other feeds remain active. Deferred sources remain visible in [watch/source_health.md](watch/source_health.md), and later retries clear the cooldown. This reduces wasted requests without bypassing logins, using proxies or buying social-media API access.
