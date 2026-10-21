# Cat Magic School — first research acceptance brief (2026-10-20)

**Scope:** Research only. Cat Magic gameplay development stays paused until the first evidence-gated research cycle is complete. No Claude, GitHub Actions dispatch, paid APIs, or Studio edits. This is a *research checkpoint*, not an implementation order.

## Evidence classification

- **Developer-confirmed description (text inspected):** original app's developer-maintained Apple App Store listing: https://apps.apple.com/ca/app/cat-magic-school-cute-tycoon/id6547838700
- **Developer-confirmed reference description (text inspected):** Sell Lemons' official Roblox experience listing: https://www.roblox.com/games/79268393072444/Sell-Lemons
- **Source-checked code candidate:** license and relevant code/README inspected directly at the linked GitHub repositories; *not* executed in Studio.
- **Media lead only:** press screenshots and Scout video metadata are NOT a watched video, reproduced interaction, game test or asset-reuse license.
- **Actual player footage, normal-player test, mobile test, Mac Peekaboo capture:** **not verified in this brief**.

## Verified claims relevant to the adaptation

**Original Cat Magic School (developer's store description):**
- Students queue to attend magical classes; class duration can be shortened if queues grow.
- Teacher quality relates to student success in difficult classes.
- Expansion includes classrooms, dormitories and dining halls.
- The Cat Snack Bar and its recipes are an additional revenue system.
- The school operates while the player is away (offline-idle design).
- These facts establish scope of the *original*, not the precise order, prices, timings or visual behavior of its first minute. Those still need inspected gameplay evidence.

**Sell Lemons (developer's Roblox page):**
- Explicit cash earning, new powers/deals and offline income are part of the advertised loop.
- Its official page does NOT independently prove any specific starting camera, pad position, interaction timing or purchase animation. Those must be inspected before using them as acceptance examples.
- Adapt the low-complexity, legible Roblox-tycoon presentation; do not reproduce proprietary assets, scripts or branding.

## Source-licensed implementation references — NOT approved integrations

| Topic | Direct source | Verified from source | Unverified / risk |
|---|---|---|---|
| Tycoon purchases and income | [spavdigital/roblox-tycoon](https://github.com/spavdigital/roblox-tycoon) ([MIT LICENSE](https://github.com/spavdigital/roblox-tycoon/blob/main/LICENSE)) | MIT license; README describes server-controlled purchases, plot ownership, shared income loop and DataStore retry behavior. | README explicitly notes **no client UI** and **no periodic autosave**. No Studio proof or Cat Magic compatibility. Keep current game persistence unless properly tested. |
| Cat/NPC idle motion | [Virtual3D/roblox-npc-motion](https://github.com/Virtual3D/roblox-npc-motion) ([MIT LICENSE](https://github.com/Virtual3D/roblox-npc-motion/blob/main/LICENSE), [NPCMotion source](https://github.com/Virtual3D/roblox-npc-motion/blob/main/src/NPCMotion.luau)) | MIT license and source functions for breathing, stance shifts, short pulses and noise-based drift. | The provided motion is **not a ready-made quadruped walk/sit/cast controller**. No Cat Magic rig, replication or performance test. |
| UI/prop tween feel | [Fraktality/spr](https://github.com/Fraktality/spr) ([MIT LICENSE](https://github.com/Fraktality/spr/blob/master/LICENSE)) | MIT license located and inspected. | Existing use, animation feel, mobile cost and fit are untested. Do not replace skeletal animation with a UI tween module. |

License files govern their own repositories; verify dependencies, assets, attribution and exact pinned revisions before reuse.

## First research cycle: objective finish line

1. **PR #21 specialist discovery:** in a disposable checkout, execute the full offline regression tests, prove a failed Cat Magic search is retried when a later search succeeds, then complete **one bounded local scan** (up to 15 specialist queries, within GitHub quota). Record active lane status and actual Cat Magic candidates. Never use GitHub Actions.
2. **Original gameplay evidence:** inspect original publicly permitted Cat Magic footage or the app itself, with creator/source, exact timestamps and visible evidence for (a) first lesson, (b) student movement/idle/study, (c) income/upgrades. Separately inspect a real Sell Lemons first minute for legible Roblox purchase presentation. If no footage is available, mark the source missing, not watched.
3. **UI reference audit:** obtain permitted actual shop/HUD screenshots, list readable prices, affordability feedback, open/close behavior and device occlusion; do not copy proprietary assets.
4. **Cat animation evaluation:** confirm which available Cat Magic quadruped rig and Animator setup are actually present *once Studio QA is authorized*. Until then compare documented animation design and source-licensed code, not rig outcomes.
5. **Produce a single prioritized blueprint:** source link + exact observation + rights status + proposed acceptance test + implementation dependency for each item. Explicitly separate verified from unknown; stop adding general AI-infrastructure candidates as substitutes for gameplay evidence.

**Research-cycle exit is NOT 'every internet source has been collected'.** It is a bounded, evidence-backed gameplay/UI/animation blueprint with the Mac discovery system verifiably running and zero false `watched`/`adopted` claims.

## Known blockers at this checkpoint

- Main's `.github/workflows/` still includes automatic GitHub-hosted triggers; a PR or merge can consume Actions minutes. Do not trigger hosted jobs.
- Existing PR #21 has not passed a full **Mac** offline suite or live bounded specialist scan. The isolated cursor fix is staged on `research/pr21-cursor-regression-20261020`; no PR/merge/deployment is claimed.
- Existing `watch/cat_magic_research_report.json` records **0 inspected videos and 0 gameplay findings**, despite many indexed links. Its top ranking contains generic non-gameplay content; the source-quality gap remains.
- Peekaboo Mac acceptance (exact-window capture and no-focus verification) requires access to the running Mac; repository code and GitHub commits alone cannot prove it.
- No gameplay development changes are authorized before completion of this first research cycle.

**Next action:** verify PR #21's staged cursor fix with the *actual* complete offline repo tests on the Mac, then run one quota-safe Cat Magic specialist discovery cycle and record factual output.
