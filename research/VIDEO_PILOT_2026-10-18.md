# Video and Reel Research Pilot — October 18, 2026

**Purpose:** demonstrate real, clickable Roblox creation examples and where our no-AI research scout succeeds/fails. These are public metadata-backed leads. **Not an assertion that an AI watched the complete video or evaluated its visuals.**

## A — Specific, source-confirmed videos / posts to watch

| Subject | Original video / watch page | Observed evidence | Why relevant |
|---|---|---|---|
| Claude Code game-building case study | [SyphoDev: Can AI Make an Entire Roblox Tower Defense Game?](https://www.youtube.com/watch?v=WIYBh_kkKN8) | Oct 1, 2026 published description and chapter list: 02:49 planning, 05:20 build, 09:15 3D models, 10:47 playtests/failures, 17:37 game/VFX, 22:32 verdict ([indexed synopsis](https://zolotube.com/watch?v=WIYBh_kkKN8)). | Most directly relevant to our own Claude→Studio→gameplay-review workflow. |
| Roblox official AI workflow | [Rapid Creation with Agentic Studio — RDC 2026](https://www.youtube.com/watch?v=KB5iAzy86Fo) | Verified Roblox YouTube RSS metadata, Oct 12, 2026. | Compare our direct Studio tooling and test process to first-party workflows. |
| Roblox animated UI | [Cascade UI Animator tutorial playlist](https://www.youtube.com/playlist?list=PL4ibvkNA51taIQVn4C7uTWGNJWID0Clia) | [Roblox developer forum](https://devforum.roblox.com/t/ui-animations-tutorials/4554921) and [creator's Reddit post](https://www.reddit.com/r/ROBLOXStudio/comments/1se8cxb/i_made_a_tutorial_series_on_ui_animations/) document first animation + main menu tutorials. | Simple, readable shop and hover motion in Cat Magic / tycoons. |
| TikTok procedural motion | [@rapid_inbx: Procedural character movement](https://urlebird.com/video/introducing-some-small-procedural-movements-for-the-character-al-7696630172186873102/) — public TikTok index/mirror | Two-day-old creator short shown on a public mirror, with author/caption and original video ID. **Not watched end-to-end.** | Cleaner character idle, movement and body response without building a complex animation system. |
| TikTok devlog before vs after | [@greencapyt: Day 1 versus Day 5 Roblox build](https://urlebird.com/video/day-1-vs-day-5-of-making-my-roblox-game-7697428324133522721/) — public mirror | Current creator caption and video ID verified from mirror. | Compare visual progression over days; **don't infer quality from view counts**. |
| TikTok small mechanics | [@azthixroblox: Prop hiding mechanic](https://urlebird.com/video/this-is-how-to-make-roblox-game-prop-hiding-the-easy-way-7696410564511288597/) — public mirror | Public video mirror metadata shows Roblox prop-hiding tutorial. | Example of a tiny recognizable interaction that could be adapted into a novel game loop. |
| Cat animation showcase | [Animated Cat Controller — r/robloxgamedev](https://www.reddit.com/r/robloxgamedev/comments/1x8htfq/animated_cat_controller/) | Public Reddit feed describes seven playable animated cats; **actual video availability not verified**. | Potential animation reference for Cat Magic; inspect directly first. |

## B — Valuable creator SHOWCASE SOURCES that are not individual verified videos

- [X @oreuiz](https://x.com/oreuiz): indexed *RobloxUI showcase reel*, anime battle-pass UI, visual/animated work. Public [index mirror](https://instalker.org/oreuiz). **Specific post URLs not yet verified.**
- [X @AltroUIUX](https://x.com/AltroUIUX): indexed **Book UI, daily rewards UI, mobile UI and animated cards**. Public [index mirror](https://instalker.org/AltroUIUX). **Specific post URLs not yet verified.**
- [Instagram @bluerain_development](https://www.instagram.com/bluerain_development/): creator's [official website](https://blueraindev.com/socials) verifies account and says it posts visual/game development updates; **specific recent Reels not retrievable here**.
- [TikTok @bluerainrblx](https://www.tiktok.com/@bluerainrblx): verified through the same official BlueRain website; account is a **source to watch**, not an independently reviewed Reel.

## C — Research pipeline verdict

**PASS:** reliable direct YouTube RSS URLs, published titles/dates, source-linked Roblox DevForum and Reddit posts, public mirror metadata for some TikTok clips.

**REVISE:** our broad Google News `site:youtube.com` / `site:tiktok.com` / `site:instagram.com` searches mix irrelevant results, spam, stale posts and redirect links; they **cannot** be counted as watched clips. Plain title scores cannot judge UI/3D style or core-loop quality.

**NOT VERIFIED:** Instagram Reel direct URLs and current feed access, actual visual motion within social shorts, video completion/captions and permission to reuse any external creator assets.

**Implemented correction:** [video_shortlist.py](../scripts/video_shortlist.py) only promotes direct known media/post URLs, rather than claiming indexed Google News redirects are verified videos. It explicitly names unsupported results as a coverage gap.

**Next improvement to benchmark, not bulk-install:** use [RSSHub](https://github.com/DIYgod/RSSHub) for one public TikTok creator feed on a disposable test; source may require browser/cookies/anti-bot work and cannot be assumed reliable. Avoid running browser bot bypasses or saving private social cookies in public GitHub Actions.
