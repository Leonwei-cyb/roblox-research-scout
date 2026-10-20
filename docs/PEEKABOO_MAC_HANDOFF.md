# Leon Mac Research Scout ↔ Peekaboo — integration gate

**State:** code in Scout PR #22 and Hub PR #87; **not deployed/merged**. Owner Mac already has Peekaboo 4.9.5 GUI + CLI, Screen Recording, Accessibility and Event Synthesizing granted. No reinstall or manual permission changes required.

## What can work

- The existing **one** Mac launchd Scout collects public media metadata and writes `watch/media_state.json`. When PR #22 is reviewed, merged and pulled into its existing working clone, the already-called `research_dispatcher.py` also produces `watch/learning_index.json` and `watch/learning_queue.md`. No extra daemon.
- `scripts/peekaboo_handoff.py` can select ONE original-post lead and optionally capture its **already-open exact browser window** via Hub's Peekaboo adapter. A screenshot is private local evidence, not a gameplay/video/audio review.
- Neither Peekaboo nor the Scout can unlock X/Instagram APIs, navigate login walls, inspect every post automatically, or authorize bulk collection. Site/platform restrictions and licensing still apply.

## Codex-only Mac staging (no Claude and no live-scout edits until proof)

1. In a **separate disposable checkout** of Scout PR #22 on the Mac (not `~/Library/Application Support/LeonScout/repo`, which launchd owns), run:
   ```sh
   python3 -m unittest discover -s tests -v
   python3 scripts/stage_peekaboo_mac.py --stage
   ```
   The second command uses the Mac's existing authenticated `gh` connection, fetches exactly two PINNED files from Leon Hub PR #87, validates Git blob SHA-1 **and** syntax, runs Hub adapter's offline tests, and stages it in ignored `local-peekaboo/`. It does not run screenshots, browsers, models or any scheduler and will not overwrite differing local files.
2. Prove CLI availability and screenshot permissions, without prompting for new permissions:
   ```sh
   python3 local-peekaboo/peekaboo_probe.py check
   python3 local-peekaboo/peekaboo_probe.py windows --app Finder
   ```
   Prior Finder snapshot failed because its windows were **minimized**, so don't repeat the same failing capture. Select a **known visible, nonminimized, background** Finder or TextEdit window already open and inspect one temporary capture. Do not activate/restore anything on the owner's behalf, and do not use owner's signed-in Chrome or page navigation.
3. With an explicitly authorized public-only test window, run one exact-window capture using the stored ID. Retain one **local-only** screenshot only with `--keep-private` to inspect its content. Confirm intended window and unchanged frontmost application; if no suitable safe window exists, **BLOCKED** rather than inventing a PASS.
4. Run `python3 scripts/learning_radar.py` in the isolated Scout checkout using its already collected `watch/media_state.json`. Confirm original links, source-health/cooldowns, no duplicate top-level queue links and no mistaken "watched" claims.
5. As a separate optional **user-approved** step, open ONE publicly accessible source post manually in a dedicated isolated browser window without disturbing other windows; use `scripts/peekaboo_handoff.py <exact-post-key> --capture --app Safari --window-id <ID> --keep-private --confirm-public-only-window`. Then manually inspect the retained image locally, confirm the actual post URL/creator and timing, and record one testable Cat Magic insight. The screenshot itself never leaves the Mac.
6. Only after stage tests + actual safe capture + no-focus receipt + source/rights review: independent Codex review, merge the exact reviewed source, and stage the same PINNED adapter in the existing Scout clone. Its existing launchd job pulls only the approved Scout main; **do not add a second LaunchAgent or run `gh pr checkout` inside the live checkout**. Preserve rollback and STOP.

## What counts as proof

- **PASS**: real Mac screenshot visually inspected; correct exact window; focus unchanged; no private content in GitHub; both test suites verified at same source SHAs; one existing Scout launchd cycle keeps running and writes a new source-health/learning-index commit.
- **UNKNOWN**: code staged, CLI present, GitHub CI green, but no real Mac capture.
- **BLOCKED**: minimized/hidden window, failed image, incomplete window identity, restricted page or platform rule.
- **NOT CLAIMED**: full video understanding, audio review, new automated social API access, Codex/Claude background agent execution.

Do not edit active Roblox game, publish, buy APIs, run Claude, change billing, touch macOS privacy settings or copy personal browsing credentials. See [Hub PR #87](https://github.com/Leonwei-cyb/Roblox-Studio-Hub/pull/87), [Scout PR #22](https://github.com/Leonwei-cyb/roblox-research-scout/pull/22), and [source access issue #11](https://github.com/Leonwei-cyb/roblox-research-scout/issues/11).
