# Source quality and usefulness audit

**Public source metadata only.** No video was watched, no 3D model was graded.

| Classification | Entries |
|---|---:|
| original video/post URL (unwatched) | 7 |
| public metadata / page | 526 |
| indexed redirect (not original) | 66 |
| promotional / risky title | 1 |
| invalid | 0 |

Total sampled entries: **600**.
Direct-original share: **1.2%** (still unwatched).
Indexed redirects: **66**. They require primary-source verification.

## Active configured sources

The store keeps history from feeds that are no longer polled; this section counts only feeds in watch/feeds.json today.

Active-source entries: **546**; direct originals **7**; indexed redirects **13**.
Active-source direct-original share: **1.3%** (still unwatched).
Entries from paused/unconfigured sources: **54** (claude-news, instagram-index, instagram-reels, tiktok-index, video-index, x-index).

## Indexed redirects by publisher

Google News redirect links are not resolved: the current article format needs Google's undocumented batchexecute endpoint, which this bot does not call. Search the publisher directly instead.

| Publisher | Redirects |
|---|---:|
| YouTube (title suffix) | 14 |
| unknown | 13 |
| Instagram (title suffix) | 8 |
| X (title suffix) | 6 |
| https://tech-insider.org/ (title suffix) | 5 |
| www.youtube.com | 5 |
| TikTok (title suffix) | 4 |
| www.instagram.com | 3 |
| www.tiktok.com | 3 |
| CyberSecurityNews (title suffix) | 1 |
| MakeUseOf (title suffix) | 1 |
| Stocktwits (title suffix) | 1 |

## Actionable interpretation

- Prefer curated original creator uploads and first-party Studio/DevForum content over broad Google News search results.
- No ranking based on views, likes, search-index count or claims of gameplay quality.
- Stop retrying consistently blocked feeds too frequently; inspect source_health.md and failure_triage.md.
- Full visuals and gameplay remain dependent on permitted original footage and direct inspection.
