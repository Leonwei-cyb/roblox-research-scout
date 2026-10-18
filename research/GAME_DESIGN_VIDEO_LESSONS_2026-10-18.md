# Roblox Game Design — 2026-10-18 developer-video study

This note separates **first-party creator claims in a published video transcript** from independently verified gameplay. The transcript is text extracted from a recent video; **we did not play the game or watch every video frame**.

## Original developer sources

1. [Tizzy RBLX: I Made 3 Viral Roblox Games in a Row (Here's What I Wish I Knew Sooner)](https://sozai.app/transcript/made-3-viral-roblox-games/) — October 17, 2026, ~24:55 min with timestamps. Developer describes mistakes in *Raise Anomaly*, *Hack a Business*, *Build a Base and Steal*. Revenue and retention screenshots are **his self-reported figures**, not independent Roblox analytics.
2. [Tizzy RBLX: Roblox Game Design Explained Like You're 5 Yrs Old](https://www.youtube.com/watch?v=CRCcsYEB_6A) — September 23, 2026. [Caption analysis](https://prepublish.ai/youtube-transcript/CRCcsYEB_6A) is available. This discusses copying the genre's underlying player-action structure but changing the key interaction.
3. [Steal An Egg by and Collect Rare Pets — official game](https://www.roblox.com/games/107778070777162/Steal-An-Egg) — official documented loop; owned/publicated group differs from named co-developers. [Brockodile creator case study](STEAL_AN_EGG_CREATOR_STUDY.md).

## The four actionable lessons from the creator's own transcript

| Creator-described mistake | Source timestamp | Reusable game design test |
|---|---|---|
| Players dropped before completing the core “steal egg” action, and the title/fantasy didn't match the action | Tizzy **02:24–02:48** | Make the opening action and game's promise identical. A tycoon player must visibly build/earn/upgrade in the opening minute, not fight unrelated waves or work through menus. |
| Forced hotbar equipping added friction to the earliest steps | **03:03–05:09** | Automatic first item placement/animation where appropriate, and one obvious next purchase; avoid unnecessary equip/move/confirm steps before first reward. |
| Spamming all tutorial cues at spawn overwhelmed the first session | **06:44–07:51** | Teach teacher/staff upgrades, capacity and later features **when first relevant**, not during the first desk purchase. |
| First-session progression had a serious ~5–10 min stall; developer had tested on a previously upgraded account | **08:03–10:18** | Always use a **fresh save/account** for the first 10-minute loop. Record exact actions, cash earned, next purchase cost, time-to-upgrade and where waiting becomes dead time. |

These aren't statistical general laws. They are specific lessons the creator reports and should be tested against our games.

## Tests to apply to our OWN games (only at useful implementation milestone)

**Cat Magic School**, faithful original mobile game in a simple Roblox tycoon presentation:

- Normal avatar spawn → physical **desk/classroom purchase** → cat arrives/studies → clear tuition payout → buy another in-world upgrade.
- First player reward before staff menu, card collections and late-game features. Keep all original mobile mechanics when unlocked in the correct later order.
- Save the first 90 seconds of actual desktop and simulated phone player input.
- Teacher/equipment menu migration is not done merely because the server correctly buys a pad; player must understand cost and see classroom change.
- Track (when needed) join → first pad → first lesson → first tuition → next pad, without assuming Roblox analytics have already verified retention.

**One Tower Tycoon**, a NORMAL tycoon with a single shooter:

- First **free dropper** with visible belt/collector payment, buy physical walls/equipment, upgrade the SAME shooter. Enemy waves support the loop, not replace it.
- Check that GO!/wave prompts and weapon tray don't compete with the one next purchase in the first 90 seconds.
- On a fresh save inspect whether the next cost is understandable, pad placement is reachable on A06, tower is fully visible, and a new purchase clearly boosts cash/shooter.
- Existing PR#29 pass 8 Studio screenshots improve readability, but one A06 after-legs frame still crops the upper shooter behind the HUD; a review comment documents the observation.

**Longer-term:** after there's a tested playable progression, apply contextual quests and onboarding funnel metrics. Do not delay getting the first-classroom loop working just to add analytics.

## Limitations and ethics

Never reproduce Tizzy's original scripts, models, promotional renders or UI. Use permitted assets and generic principles. The video transcript is not a substitute for direct observation of animation, latency, controls or visuals; exact timecodes need verification when somebody watches the original video.
