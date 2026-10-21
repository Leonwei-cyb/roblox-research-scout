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

## Added firsthand-gameplay reporting and player-experience findings (2026-10-21)

**Important evidence boundary:** These are inspected public developer statements, a player's published review, a journalist's *written* firsthand review retrieved through a search index, and creator-posted **still-image descriptions**. **We did not watch gameplay video or personally play the original game.** No video timestamps, real timings, performance, player-camera footage, or actual Cat Magic Roblox behavior are asserted.

### A. The school income loop is tuition, NOT a generic dropper

- **Source:** [GameToc firsthand review, journalist Hong Su-min, 2025-04-03](https://www.gametoc.co.kr/news/articleView.html?idxno=90752). The site's direct page returned HTTP 403 here; its public search-indexed review text was available. This is *secondary firsthand reporting* (the journalist says they played), **not firsthand gameplay observation by Leon**.
- **Published account:** Cat students attend classes; the school collects tuition and reinvests it in facilities, which increases income. Quest guidance unlocks more lessons/courses. The game has passive earnings and additional timed prompts/efficiency boosts, and eventually shifts between branch schools. A cat's appearance changes on promotion. The journalist praised the school-management systems but criticized repetitive later adventure content and heavy ad prompts.
- **Implication for the future 3D adaptation, still a design hypothesis:** The first school loop should connect a visible teaching action to **tuition earned** and a next classroom/lesson upgrade. A simple dropper can be an internal rate abstraction, but the player-facing fantasy must be "cat attends lesson → school earns tuition." Avoid pay-to-progress pressure and premature RPG scope. **Exact opening sequence, costs, timing, camera and cat animation unverified.**

### B. Original developer's scope: tycoon early, RPG later

- **Source:** [Neptune/Treeplla March 28, 2025 launch announcement reprinted by Ruliweb](https://m.ruliweb.com/news/read/208925), inspected directly in text. It describes classes, examinations, graduation and later-world adventures. The publisher explicitly characterized **the early game as a tycoon and the middle/later game as RPG exploration/progression**.
- **Source:** [GameToc interview with Treeplla CEO, 2025](https://www.gametoc.co.kr/news/articleView.html?idxno=91688) (search-indexed interview excerpt; direct article request returned HTTP 403). The CEO described the roguelike adventure system as optional for enjoying the base tycoon, acknowledged its mixed/poor reception and weak initial engagement, and described it as a later extension to the tycoon's repetition.
- **Decision:** Prioritize the fully working first school lesson/tuition/investment cycle in the Roblox beta. Preserve *documented* adventure/branch-school systems in the longer-term research blueprint, but don't claim they occur during first-session footage or that early RPG is required to validate a slice.

### C. Direct player UX evidence: camera and navigation errors

- **Source:** [Apple App Store Korean review page](https://apps.apple.com/kr/app/%EA%B3%A0%EC%96%91%EC%9D%B4-%EB%A7%88%EB%B2%95%ED%95%99%EA%B5%90-%EC%8B%A0%EB%B9%84%ED%95%98%EA%B3%A0-%EA%B7%80%EC%97%AC%EC%9A%B4-%ED%83%80%EC%9D%B4%EC%BF%A4/id6547838700?platform=iphone&see-all=reviews). Public reviews and developer replies read directly. **Individual comments are not representative survey data.**
- **2025-04-25 player report:** On cat promotion, automatic zoom sometimes hides the cat's changed appearance; camera zoom-out range feels restrictive; scrolling/tapping near a gem action can unintentionally spend premium currency.
- **2025-04-24 player report:** Bottom-middle UI action enters adventure when the player expects "home," causing accidental navigation; reviewer liked varied resource rewards, upgrades, promotions and professor cards.
- **2025-05-01 official developer reply:** Other school maps accrue income within the offline-income cap while the player is away; the player must visit those maps to claim the saved income.
- **Roblox adaptation acceptance suggestions (not tested):** A promoted cat should remain visible throughout the effect; first-session camera should clearly frame teacher, cat, desk and next pad; "home/school" must not route to adventure; premium-currency taps must not fire while dragging/scrolling and require explicit confirmation; eventual school branches should communicate pending offline income.

### D. A creator-posted still-image sequence — not a watched playthrough

- **Source:** [Lemon8 Cat Magic School player showcase, 2025-08-22](https://www.lemon8-app.com/@qutequct/7541561163231379975?region=th). Its public page shows **still-image captions**, including "The Magic Theory class was a success!", room/equipment upgrade and teacher hiring, a battle scene, and the "1. Magical Forest" school map. The author describes classroom upgrades, broom training, exams and wizard promotion.
- **Evidence scope:** This corroborates the **presence of multiple systems and visible lesson-completion feedback**, NOT their chronological order, exact timings or real cat movement/casting animation.
- **Future beta check:** lesson success and tuition should be visually readable near the action (not hidden by a shop); upgrade affordability should remain legible; a first-session player can distinguish school from optional exploration.

### E. Public screenshot reference: information architecture, not license to copy assets

- **Source:** [GameToc image-rich 2025 review](https://www.gametoc.co.kr/news/articleView.html?idxno=90752) and [Ruliweb developer announcement with classroom art](https://m.ruliweb.com/news/read/208925). Published stills depict a dense, portrait-oriented management HUD with resource counters, upgrade/menu panels, teacher cards, classroom desks and small status indicators.
- **Design interpretation:** Re-create **function and legibility** in a simpler native Roblox visual vocabulary, **not copyrighted sprite layouts, sound files, art or 1:1 UI graphics**. Treat images as *reference stills*; do not infer animations or first-camera composition from them.

### F. Concrete economy bottleneck evidence from a player's detailed hands-on review

- **Source:** [Detailed Cat Magic School player review, r/incremental_games, 2024](https://www.reddit.com/r/incremental_games/comments/1gnbhg5). The public search-indexed original Reddit review was inspected; direct Reddit page access was unavailable. **Player report, version/date-dependent and not independently reproduced.**
- **Described revenue sources:** cat enrollments, classes, eating/dining and passing exams, not tuition alone. The author describes classroom **level, capacity and speed** upgrades as independent from **class pass rate**, with professor-card upgrades and other rarer resources affecting pass rates. Reported higher-level classrooms can have more students failing and progression slowing; this is the player's report, not a confirmed current balance formula.
- **Roblox-replica implication:** In the *full* system map, separate (1) class enrollment/queue, (2) classroom capacity/lesson timer, (3) professor success modifier, (4) enrollment and tuition payouts, (5) food/dining and exams, and (6) larger school unlocks. For the beta, show a class and a visible tuition reward, with player-readable "capacity", "speed" and "success" labels. Do **not** introduce a paywalled fail loop.

### G. Long-session progression evidence and balance warnings (not opening-minute footage)

- **Source:** [Natsuhiro's September 15, 2025 stage-five Cat Magic School progression guide](https://note.com/natsuhiro0715/n/ne0433e5e97b1?hl=en). Public full text inspected directly; first-person account, **not verified by running that version of the game**.
- **Described systems:** A sequence of named schools includes **Magic Forest, Snowy Forest, Prickly Tail Field, Nyans Bag and Magic Government**. The author distinguishes easily earned fame/regular income from much scarcer **spell power, professor improvement, gems and magic potions**; online reward prompts and rotating timed events are part of the progression. Author claims passive leaving-open does not grant every needed currency. These are late-game player observations, **not a verified map unlock specification or exact current formulas**.
- **Roblox planning:** Preserve the *concept* of multiple campuses and separate long-term progression resources in the future blueprint, without inventing precise stage costs, map order, idle caps or monetization. A future player acceptance test should verify that passive income does not misleadingly suggest all upgrades advance automatically. Keep initial classroom gameplay simple and self-contained.

### H. Independent English-language player UX corroboration

- **Source:** [App Store GB ratings and reviews](https://apps.apple.com/gb/app/cat-magic-school-cute-tycoon/id6547838700?platform=ipad&see-all=reviews) and [Google Play reviews](https://play.google.com/store/apps/details?hl=en_CA&id=com.tree.idle.cat.academy). These are individual player-reported experiences, not representative measured failure rates.
- **Pattern:** Several players liked the cats, lesson grading and school expansion, but reported that rare professor upgrades / potions / gems and ad dependencies obstructed progression. This supports a design requirement: each new classroom purchase should lead to an attainable visible reward *without* premium spending, and teacher performance should have understandable, non-opaque requirements.
- **Do not import exact balance numbers:** Original app reviews span multiple dates and versions.

### I. Rechecked permissively licensed tooling on 2026-10-21

- **UI:** [dphfox/Fusion](https://github.com/dphfox/Fusion) — [MIT license inspected](https://github.com/dphfox/Fusion/blob/main/LICENSE), README inspected at blob SHA \`d2dbc45c586c9440acc68536bcf67ddf9f242b53\`. Reactive Luau companion library with Roblox integration; **not integrated or benchmarked**. Prefer a tiny upgrade panel evaluation over replacing all Cat Magic UI.
- **QA:** [Chrrxs/robloxstudio-mcp](https://github.com/Chrrxs/robloxstudio-mcp) — [MIT license inspected](https://github.com/Chrrxs/robloxstudio-mcp/blob/main/LICENSE), blob \`3e4c4339bb797ed6d5d17beae5643be7f7d563b1\`. Do not claim Studio screenshots, testing, or installation until a real Mac test exists.
- **Existing tycoon and cat-motion references:** \`spavdigital/roblox-tycoon\` and \`Virtual3D/roblox-npc-motion\` license blobs were rechecked; still **untested** with the game.

---

### Focused follow-up research test (ONE most valuable next step)

Inspect a **real, permitted first-session gameplay recording** such as [KruMobile Part 1 (2025-04-03)](https://www.youtube.com/watch?v=N4u9-2ZNwXM) or [TanJinGames Part 1 (2025-04-25)](https://www.youtube.com/watch?v=J-FsPaDFgLg), with actual accessible media, and write **five timestamped observation rows**:
1. first visible player action / tutorial cue;
2. class/facility purchase and immediately visible build changes;
3. student arrival, walk/sit/study/cast with observable frame transitions;
4. lesson completion, tuition and upgrade affordability feedback;
5. next unlock, guided quest and menu/camera behavior.

Each row must carry exact video URL, **actually observed** timecode, player-visible detail, confidence, reuse-rights check and one Roblox-side acceptance criterion. If the source is unavailable, record **blocked: actual video playback** and do not fill timestamps from descriptions. Cat Magic game code remains paused.

---

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
