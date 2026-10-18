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
- **Actions:** open the **Actions** tab and run **Roblox research scout (no AI)** manually, or let the scheduled run check daily.
- **Tests:** `python3 -m unittest discover -s tests -v`.

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
