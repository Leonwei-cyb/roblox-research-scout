# Source quality and usefulness audit

**Public source metadata only.** No video was watched, no 3D model was graded.

| Classification | Entries |
|---|---:|
| original video/post URL (unwatched) | 8 |
| public metadata / page | 496 |
| indexed redirect (not original) | 95 |
| promotional / risky title | 1 |
| invalid | 0 |

Total sampled entries: **600**.
Direct-original share: **1.3%** (still unwatched).
Indexed redirects: **95**. They require primary-source verification.

## Active configured sources

The store keeps history from feeds that are no longer polled; this section counts only feeds in watch/feeds.json today.

Active-source entries: **520**; direct originals **8**; indexed redirects **16**.
Active-source direct-original share: **1.5%** (still unwatched).
Entries from paused/unconfigured sources: **80** (claude-news, instagram-index, instagram-reels, tiktok-index, video-index, x-index).

## Indexed redirects by publisher

Google News redirect links are not resolved: the current article format needs Google's undocumented batchexecute endpoint, which this bot does not call. Search the publisher directly instead.

| Publisher | Redirects |
|---|---:|
| YouTube (title suffix) | 22 |
| unknown | 17 |
| Instagram (title suffix) | 10 |
| X (title suffix) | 9 |
| TikTok (title suffix) | 8 |
| https://tech-insider.org/ (title suffix) | 6 |
| www.instagram.com | 5 |
| www.youtube.com | 4 |
| www.tiktok.com | 3 |
| Pasquale Pillitteri (title suffix) | 2 |
| CyberSecurityNews (title suffix) | 1 |
| HackerNoon (title suffix) | 1 |

## Actionable interpretation

- Prefer curated original creator uploads and first-party Studio/DevForum content over broad Google News search results.
- No ranking based on views, likes, search-index count or claims of gameplay quality.
- Stop retrying consistently blocked feeds too frequently; inspect source_health.md and failure_triage.md.
- Full visuals and gameplay remain dependent on permitted original footage and direct inspection.
