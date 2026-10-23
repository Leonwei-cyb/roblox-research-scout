# Source quality and usefulness audit

**Public source metadata only.** No video was watched, no 3D model was graded.

| Classification | Entries |
|---|---:|
| original video/post URL (unwatched) | 7 |
| public metadata / page | 546 |
| indexed redirect (not original) | 47 |
| promotional / risky title | 0 |
| invalid | 0 |

Total sampled entries: **600**.
Direct-original share: **1.2%** (still unwatched).
Indexed redirects: **47**. They require primary-source verification.

## Active configured sources

The store keeps history from feeds that are no longer polled; this section counts only feeds in watch/feeds.json today.

Active-source entries: **565**; direct originals **7**; indexed redirects **12**.
Active-source direct-original share: **1.2%** (still unwatched).
Entries from paused/unconfigured sources: **35** (claude-news, instagram-index, instagram-reels, tiktok-index, video-index, x-index).

## Indexed redirects by publisher

Google News redirect links are not resolved: the current article format needs Google's undocumented batchexecute endpoint, which this bot does not call. Search the publisher directly instead.

| Publisher | Redirects |
|---|---:|
| unknown | 10 |
| Instagram (title suffix) | 8 |
| www.youtube.com | 6 |
| YouTube (title suffix) | 5 |
| https://tech-insider.org/ (title suffix) | 5 |
| TikTok (title suffix) | 4 |
| X (title suffix) | 3 |
| www.tiktok.com | 3 |
| www.instagram.com | 2 |
| MakeUseOf (title suffix) | 1 |

## Actionable interpretation

- Prefer curated original creator uploads and first-party Studio/DevForum content over broad Google News search results.
- No ranking based on views, likes, search-index count or claims of gameplay quality.
- Stop retrying consistently blocked feeds too frequently; inspect source_health.md and failure_triage.md.
- Full visuals and gameplay remain dependent on permitted original footage and direct inspection.
