#!/usr/bin/env python3
"""Which Leon game the research reports are for, read from the shared authority.

The Mac's studio gate keeps one line naming the single active game. Research
reports follow it, so a held game never gets fresh "current" questions. If the
authority is missing or names an unknown game (for example on GitHub Actions),
the result is None and reports carry NO game-specific tasks.
"""
from __future__ import annotations

import os
from pathlib import Path

AUTHORITY = Path.home() / "Documents/ChatGPT/leon/coordination/studio-gate/active_game.txt"
AUTHORITY_LABEL = "studio-gate/active_game.txt"

ALIASES = {
    "hex-haven": "colonists", "hex haven": "colonists", "colonists": "colonists",
    "colonist": "colonists", "cat-magic": "cat-magic", "cat magic": "cat-magic",
    "cat-magic-school": "cat-magic",
}

# Report lanes are (learning_radar.FOCUS label, priority, player-test question).
PROFILES = {
    "cat-magic": {
        "name": "Cat Magic",
        "slug": "cat_magic",
        "lanes": (
            ("first-session and mobile", "P0", "Can a new player identify and reach the first FREE pad from the normal spawn camera?"),
            ("building and purchases", "P0", "Does buying a pad visibly build a desk and bring a cat into the classroom?"),
            ("animation and audio", "P1", "Does an arriving cat walk, sit, study and cast without clipping through the player?"),
            ("UI and menus", "P1", "Is the next upgrade price readable without covering the cat or Roblox mobile controls?"),
            ("economy and income", "P1", "Does a completed lesson produce server-owned tuition and enable the next purchase?"),
            ("world and visual design", "P1", "Are the blue grounds, simple entrance and first classroom visible and uncluttered?"),
        ),
        "radar": {
            "first-session and mobile": "Can a first-time phone player find and buy a desk within 20 seconds?",
            "building and purchases": "Does buying one physical pad build a desk and cat in 0.5-1 second?",
            "economy and income": "Does server-earned tuition visibly increase and reveal the next expansion pad?",
            "UI and menus": "Is the simple Pet Simulator-style HUD readable at desktop and 390px phone width?",
            "animation and audio": "Do cat movement, construction effects and sound land together in a player recording?",
            "world and visual design": "Can the player clearly see the first pad and classroom on simple blue outdoor grass?",
        },
    },
    "colonists": {
        "name": "Colonists",
        "slug": "colonists",
        "lanes": (
            ("board game and turn flow", "P0", "At the same game state as the Colonist.io original, does a turn read as roll, collect, build or trade, end?"),
            ("first-session and mobile", "P0", "Can a first-time desktop player place both opening settlements and roads without help text?"),
            ("UI and menus", "P1", "Are hand cards, build costs, dice and end-turn readable at full desktop viewport without covering the board?"),
            ("world and visual design", "P1", "Does the board read as one restrained 2D Colonist-style board (tiles, numbers, ports, pieces), not an asset collage?"),
            ("animation and audio", "P1", "Do dice, resource gains and robber moves give short feedback tied to the real action, with no decorative motion?"),
        ),
        "radar": {
            "board game and turn flow": "Compare one turn phase against the Colonist.io original at the same state.",
            "first-session and mobile": "Can a first-time desktop player finish opening placement without help text?",
            "UI and menus": "Is the hand/build/dice bar readable at full desktop viewport without covering the board?",
            "world and visual design": "Does the board stay one restrained 2D Colonist-style composition?",
            "animation and audio": "Is every motion or sound tied to a real roll, gain, build or robber action?",
        },
    },
}
GENERIC_QUESTION = "Name one existing player-visible defect in the active game this could test before acting."
NO_GAME_QUESTION = "No active game resolved: do not create game tasks from this lead."


def resolve(environ=None):
    """Return (game_id or None, provenance). LEON_ACTIVE_GAME / _FILE override the authority."""
    environ = os.environ if environ is None else environ
    raw, source = environ.get("LEON_ACTIVE_GAME"), "LEON_ACTIVE_GAME"
    if raw is None:
        path = Path(environ.get("LEON_ACTIVE_GAME_FILE") or AUTHORITY)
        source = AUTHORITY_LABEL if path == AUTHORITY else "LEON_ACTIVE_GAME_FILE"
        try:
            raw = path.read_text(encoding="utf-8")[:200] if path.stat().st_size <= 4096 else ""
        except OSError:
            return None, source + ": MISSING"
    lines = str(raw).strip().splitlines()
    value = lines[0].strip().lower() if lines else ""
    game = ALIASES.get(value)
    if game is None:
        return None, source + ": UNRECOGNIZED"
    return game, source


def held(game):
    """Every other known profile is on hold while one game is active.

    With no resolved game nothing is called held: that would be a false claim.
    """
    return [g for g in PROFILES if g != game] if game in PROFILES else []
