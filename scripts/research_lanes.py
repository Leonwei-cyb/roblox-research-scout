"""Bounded, fair research lanes for the existing Leon discovery engine.

No network calls, model calls, subprocesses or scheduler are created here. All
lanes share the caller's GitHub search quota, stored candidates and state.
"""

import re


def plan_queries(config, state, budget):
    """Return (topic, query, lane) tuples, UI summary, and next cursors.

    The caller commits cursors only after a real successful search so a quota
    outage does not rotate away unsearched queries. Lanes rotate their own
    queries between runs. Each distinct query is scheduled at most once/run.
    """
    budget = max(0, int(budget))
    topics = {t.get("id"): [q for q in t.get("queries", []) if isinstance(q, str) and q]
              for t in config.get("topics", []) if isinstance(t, dict)}
    current = state.get("research_lane_cursor", {})
    cursors = dict(current) if isinstance(current, dict) else {}
    lanes = config.get("research_lanes")
    if not isinstance(lanes, list) or not lanes:
        queries = [(tid, q, "general") for tid, values in topics.items() for q in values][:budget]
        return queries, [{"id": "general", "active": True, "planned": len(queries),
                          "available": sum(map(len, topics.values()))}], cursors

    active, summary = [], []
    seen_ids = set()
    for order, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            continue
        lid = str(lane.get("id", ""))
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", lid) or lid in seen_ids:
            continue
        seen_ids.add(lid)
        try:
            weight = max(0, min(20, int(lane.get("weight", 1))))
        except (ValueError, TypeError):
            weight = 0
        items, seen_query = [], set()
        for tid in lane.get("topics", []):
            for query in topics.get(tid, []):
                if query not in seen_query:
                    items.append((tid, query, lid))
                    seen_query.add(query)
        enabled = bool(lane.get("enabled", True)) and weight > 0 and bool(items)
        item = {"id": lid, "label": str(lane.get("label", lid))[:70],
                "active": enabled, "weight": weight, "planned": 0, "available": len(items)}
        summary.append(item)
        if not enabled:
            continue
        try:
            offset = max(0, int(cursors.get(lid, 0))) % len(items)
        except (ValueError, TypeError):
            offset = 0
        rotated = items[offset:] + items[:offset]
        active.append({"id": lid, "items": rotated, "credit": 0, "weight": weight,
                       "offset": offset, "taken": 0, "order": order, "status": item})

    selected, seen_query = [], set()
    def take(entry):
        topic, query, lid = entry["items"][entry["taken"]]
        entry["taken"] += 1
        if query in seen_query:
            return
        seen_query.add(query)
        selected.append((topic, query, lid))
        entry["status"]["planned"] += 1

    # Reserve one opportunity for every specialist if the budget fits.
    # With fewer slots than lanes, rotate the reserved slots across runs.
    if budget >= len(active):
        for entry in active:
            take(entry)
    elif active and budget:
        try:
            offset = max(0, int(state.get("research_lane_run", 0))) % len(active)
        except (ValueError, TypeError):
            offset = 0
        for entry in (active[offset:] + active[:offset])[:budget]:
            take(entry)

    while len(selected) < budget:
        eligible = [a for a in active if a["taken"] < len(a["items"])]
        if not eligible:
            break
        total_weight = sum(a["weight"] for a in eligible)
        for a in eligible:
            a["credit"] += a["weight"]
        winner = max(eligible, key=lambda a: (a["credit"], a["weight"], -a["order"]))
        winner["credit"] -= total_weight
        take(winner)

    for a in active:
        cursors[a["id"]] = (a["offset"] + a["taken"]) % len(a["items"])
    return selected, summary, cursors


def prioritize_hits(hits, topic_to_lane, config, limit):
    """Fairly allocate GitHub enrichment candidates across specialist lanes.

    Input hits are unique repository records (repo, topic, GitHub metadata).
    Each active lane with hits gets one slot if the budget permits; remaining
    slots follow configured lane weights. Repositories are ranked by stars
    *within* a lane, so general tooling cannot crowd out Roblox game leads.
    """
    limit = max(0, int(limit))
    weights = {str(lane.get("id")): max(0, min(20, int(lane.get("weight", 1))))
               for lane in config.get("research_lanes", []) if isinstance(lane, dict)
               and str(lane.get("weight", 1)).lstrip("-").isdigit()
               and lane.get("enabled", True)}
    groups = {}
    for hit in hits:
        lane = topic_to_lane.get(hit[1], "general")
        groups.setdefault(lane, []).append(hit)
    for group in groups.values():
        group.sort(key=lambda x: (-int(x[2].get("stars", 0)), x[0].lower()))
    order = [l.get("id") for l in config.get("research_lanes", []) if isinstance(l, dict)]
    order = [lid for lid in order if lid in groups] + sorted(set(groups) - set(order))
    available = [{"id": lid, "items": groups[lid], "pos": 0, "credit": 0,
                  "weight": max(1, weights.get(lid, 1)), "order": i}
                 for i, lid in enumerate(order)]
    chosen = []
    if limit >= len(available):
        for lane in available:
            chosen.append(lane["items"][0])
            lane["pos"] += 1
    while len(chosen) < limit:
        remaining = [lane for lane in available if lane["pos"] < len(lane["items"])]
        if not remaining:
            break
        total = sum(lane["weight"] for lane in remaining)
        for lane in remaining:
            lane["credit"] += lane["weight"]
        winner = max(remaining, key=lambda lane: (lane["credit"], lane["weight"], -lane["order"]))
        winner["credit"] -= total
        chosen.append(winner["items"][winner["pos"]])
        winner["pos"] += 1
    return chosen
