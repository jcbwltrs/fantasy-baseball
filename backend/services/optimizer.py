"""Lineup optimizer logic — constraint-based assignment maximizing projected points."""

from itertools import permutations
from typing import Optional
from models import PlayerStats, LineupSlot

# Roster slot definitions and which positions can fill them
SLOT_ELIGIBILITY = {
    "C": ["C"],
    "1B": ["1B"],
    "2B": ["2B"],
    "3B": ["3B"],
    "SS": ["SS"],
    "OF_1": ["OF", "LF", "CF", "RF"],
    "OF_2": ["OF", "LF", "CF", "RF"],
    "OF_3": ["OF", "LF", "CF", "RF"],
    "Util": ["C", "1B", "2B", "3B", "SS", "OF", "LF", "CF", "RF", "DH"],
    "SP": ["SP"],
    "RP": ["RP"],
    "P_1": ["SP", "RP"],
    "P_2": ["SP", "RP"],
    "P_3": ["SP", "RP"],
}

# Display names for slots
SLOT_DISPLAY = {
    "OF_1": "OF", "OF_2": "OF", "OF_3": "OF",
    "P_1": "P", "P_2": "P", "P_3": "P",
}

BATTER_SLOTS = ["C", "1B", "2B", "3B", "SS", "OF_1", "OF_2", "OF_3", "Util"]
PITCHER_SLOTS = ["SP", "RP", "P_1", "P_2", "P_3"]
ALL_ACTIVE_SLOTS = BATTER_SLOTS + PITCHER_SLOTS


def can_fill_slot(player_positions: list[str], slot: str) -> bool:
    """Check if a player can fill a given roster slot."""
    eligible = SLOT_ELIGIBILITY.get(slot, [])
    return any(pos in eligible for pos in player_positions)


def optimize_lineup(players: list[dict], schedule_games: dict = None) -> dict:
    """Optimize lineup assignment to maximize total projected points.

    Args:
        players: list of dicts with keys: player_id, player_name, positions (list),
                 is_pitcher, projected_pts_per_game, games_this_week, projected_total
        schedule_games: dict of team -> games this week (optional)

    Returns:
        dict with 'lineup' (slot -> player), 'bench' (list), 'total_projected_pts', 'notes'
    """
    # Split into batters and pitchers
    batters = [p for p in players if not p.get("is_pitcher")]
    pitchers = [p for p in players if p.get("is_pitcher")]

    # Sort by projected total descending for greedy assignment
    batters.sort(key=lambda p: p.get("projected_total", 0), reverse=True)
    pitchers.sort(key=lambda p: p.get("projected_total", 0), reverse=True)

    lineup = {}
    assigned_ids = set()
    notes = []

    # Assign batters to batter slots using greedy approach
    # First pass: assign to specific position slots (C, 1B, 2B, 3B, SS)
    specific_slots = ["C", "1B", "2B", "3B", "SS"]
    for slot in specific_slots:
        best = _find_best_for_slot(batters, slot, assigned_ids)
        if best:
            lineup[slot] = best
            assigned_ids.add(best["player_id"])

    # Second pass: OF slots
    for slot in ["OF_1", "OF_2", "OF_3"]:
        best = _find_best_for_slot(batters, slot, assigned_ids)
        if best:
            lineup[slot] = best
            assigned_ids.add(best["player_id"])

    # Third pass: Util slot (any remaining batter)
    best = _find_best_for_slot(batters, "Util", assigned_ids)
    if best:
        lineup["Util"] = best
        assigned_ids.add(best["player_id"])

    # Assign pitchers to pitcher slots
    # SP slot first
    best = _find_best_for_slot(pitchers, "SP", assigned_ids)
    if best:
        lineup["SP"] = best
        assigned_ids.add(best["player_id"])

    # RP slot
    best = _find_best_for_slot(pitchers, "RP", assigned_ids)
    if best:
        lineup["RP"] = best
        assigned_ids.add(best["player_id"])

    # P slots (any pitcher)
    for slot in ["P_1", "P_2", "P_3"]:
        best = _find_best_for_slot(pitchers, slot, assigned_ids)
        if best:
            lineup[slot] = best
            assigned_ids.add(best["player_id"])

    # Bench = everyone not assigned
    bench = [p for p in players if p["player_id"] not in assigned_ids]

    # Flag players with 0 games
    for slot, player in lineup.items():
        if player.get("games_this_week", 0) == 0:
            notes.append(f"{player['player_name']} has 0 games this week — consider benching")

    total = sum(p.get("projected_total", 0) for p in lineup.values())

    return {
        "lineup": lineup,
        "bench": bench,
        "total_projected_pts": round(total, 1),
        "notes": notes,
    }


def _find_best_for_slot(players: list[dict], slot: str, assigned: set) -> Optional[dict]:
    """Find the best unassigned player eligible for a slot."""
    for p in players:
        if p["player_id"] in assigned:
            continue
        positions = p.get("positions", [])
        if isinstance(positions, str):
            positions = [x.strip() for x in positions.split(",")]
        if can_fill_slot(positions, slot):
            return p
    return None
