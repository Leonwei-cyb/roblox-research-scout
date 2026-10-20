# Source quality and usefulness audit

**Public source metadata only.** No video was watched, no 3D model was graded.

| Classification | Entries |
|---|---:|
| original video/post URL (unwatched) | 37 |
| public metadata / page | 271 |
| indexed redirect (not original) | 240 |
| promotional / risky title | 9 |
| invalid | 0 |

Total sampled entries: **557**.
Direct-original share: **6.6%** (still unwatched).
Indexed redirects: **240**. They require primary-source verification.

## Active configured sources

The store keeps history from feeds that are no longer polled; this section counts only feeds in watch/feeds.json today.

Active-source entries: **398**; direct originals **37**; indexed redirects **83**.
Active-source direct-original share: **9.3%** (still unwatched).
Entries from paused/unconfigured sources: **159** (brock-youtube, claude-news, instagram-index, instagram-reels, tiktok-index, video-index, x-index).

## Indexed redirects by publisher

Google News redirect links are not resolved: the current article format needs Google's undocumented batchexecute endpoint, which this bot does not call. Search the publisher directly instead.

| Publisher | Redirects |
|---|---:|
| YouTube (title suffix) | 50 |
| unknown | 43 |
| Instagram (title suffix) | 36 |
| TikTok (title suffix) | 25 |
| www.youtube.com | 22 |
| www.instagram.com | 18 |
| X (title suffix) | 10 |
| https://tech-insider.org/ (title suffix) | 9 |
| www.tiktok.com | 8 |
| Pasquale Pillitteri (title suffix) | 2 |
| A (title suffix) | 1 |
| Anthropic (title suffix) | 1 |

## Actionable interpretation

- Prefer curated original creator uploads and first-party Studio/DevForum content over broad Google News search results.
- No ranking based on views, likes, search-index count or claims of gameplay quality.
- Stop retrying consistently blocked feeds too frequently; inspect source_health.md and failure_triage.md.
- Full visuals and gameplay remain dependent on permitted original footage and direct inspection.
