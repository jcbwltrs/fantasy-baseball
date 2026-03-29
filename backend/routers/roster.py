"""Roster management endpoints — multi-team league support."""

import csv
import io
import difflib
from fastapi import APIRouter, UploadFile, File, Query
from datetime import datetime, timedelta

from db import (
    get_db, get_roster, add_to_roster, drop_from_roster, move_roster_slot,
    get_all_players, get_player_game_logs, get_player_season_stats,
    get_roster_player_ids, get_all_rostered_player_ids,
    get_league_teams, update_league_team, get_roster_slot_counts,
    get_reference_date,
)
from services.run_support import calculate_wpps
from models import RosterAddRequest, RosterDropRequest, RosterMoveRequest, BulkRosterAddRequest, LeagueTeamUpdateRequest
from config import MAX_ACQUISITIONS_PER_WEEK, ROSTER_POSITIONS, CURRENT_SEASON

router = APIRouter(prefix="/api/roster", tags=["roster"])

WINDOW_DAYS = {"3d": 3, "7d": 7, "14d": 14, "30d": 30, "season": 365}

# Max slots per type based on ROSTER_POSITIONS
from collections import Counter
SLOT_LIMITS = Counter(ROSTER_POSITIONS)  # e.g. {"BN": 5, "OF": 3, "P": 3, ...}


# --- League Teams ---

@router.get("/teams")
async def list_league_teams():
    """Get all 10 league teams."""
    db = await get_db()
    teams = await get_league_teams(db)
    return {"teams": [dict(t) for t in teams]}


@router.put("/teams/{team_id}")
async def rename_league_team(team_id: int, req: LeagueTeamUpdateRequest):
    """Rename a league team."""
    db = await get_db()
    await update_league_team(db, team_id, req.team_name)
    await db.commit()
    return {"success": True}


# --- Roster CRUD ---

@router.get("/")
async def get_team_roster(league_team_id: int = Query(1, ge=1, le=10)):
    """Get full roster with current stats for a league team."""
    db = await get_db()
    ref_date = await get_reference_date(db)
    roster = await get_roster(db, league_team_id)
    players = []
    for row in roster:
        pid = row["player_id"]
        logs = await get_player_game_logs(db, pid)
        total_pts = sum(r["fantasy_points"] for r in logs) if logs else 0
        gp = len(logs) if logs else 0

        players.append({
            "player_id": pid,
            "player_name": row["player_name"],
            "team": row["team"],
            "positions": row["positions"],
            "roster_slot": row["roster_slot"],
            "added_date": row["added_date"],
            "is_pitcher": bool(row["is_pitcher"]) if "is_pitcher" in row.keys() else False,
            "games_played": gp,
            "fantasy_points": round(total_pts, 2),
            "pts_per_game": round(total_pts / gp, 2) if gp > 0 else 0,
        })

    slot_counts = await get_roster_slot_counts(db, league_team_id)
    return {
        "roster": players,
        "count": len(players),
        "league_team_id": league_team_id,
        "slot_counts": slot_counts,
        "slot_limits": dict(SLOT_LIMITS),
    }


@router.post("/add")
async def add_player(req: RosterAddRequest):
    """Add a player to a league team's roster."""
    db = await get_db()

    # Check roster size — skip acquisition limit if roster is being built (< 20 players)
    current_roster = await get_roster(db, req.league_team_id)
    roster_count = len(current_roster)

    if roster_count >= 20:
        # Only enforce weekly limit for established rosters
        week_start = _get_week_start()
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM weekly_acquisitions WHERE league_team_id = ? AND week_start = ? AND action = 'add'",
            (req.league_team_id, week_start)
        )
        row = await cursor.fetchone()
        count = row["cnt"] if row else 0
        if count >= MAX_ACQUISITIONS_PER_WEEK:
            return {"error": f"Weekly acquisition limit reached ({MAX_ACQUISITIONS_PER_WEEK})", "success": False}

    # Check slot availability
    slot_counts = await get_roster_slot_counts(db, req.league_team_id)
    slot = req.roster_slot
    max_for_slot = SLOT_LIMITS.get(slot, 0)
    current_in_slot = slot_counts.get(slot, 0)
    if current_in_slot >= max_for_slot:
        # Try to put on bench instead
        if slot_counts.get("BN", 0) < SLOT_LIMITS.get("BN", 5):
            slot = "BN"
        else:
            return {"error": f"No room in {req.roster_slot} slot (and bench is full)", "success": False}

    # Check player isn't already rostered by another team
    cursor = await db.execute(
        "SELECT league_team_id FROM league_rosters WHERE player_id = ? AND is_active = 1",
        (req.player_id,)
    )
    existing = await cursor.fetchone()
    if existing and existing["league_team_id"] != req.league_team_id:
        return {"error": f"Player is already on Team {existing['league_team_id']}'s roster", "success": False}

    await add_to_roster(db, req.league_team_id, req.player_id, req.player_name, req.team, req.positions, slot)

    # Track acquisition only for established rosters
    if roster_count >= 20:
        week_start = _get_week_start()
        await db.execute(
            "INSERT INTO weekly_acquisitions (league_team_id, player_id, week_start, action, action_date) VALUES (?, ?, ?, 'add', ?)",
            (req.league_team_id, req.player_id, week_start, datetime.utcnow().isoformat())
        )
    await db.commit()

    return {"success": True, "message": f"Added {req.player_name} to roster", "roster_slot": slot}


@router.post("/bulk-add")
async def bulk_add_players(req: BulkRosterAddRequest):
    """Add multiple players at once (for initial roster setup or opponent rosters)."""
    db = await get_db()
    added = 0
    errors = []
    for p in req.players:
        pid = p.get("player_id")
        name = p.get("player_name", "")
        team = p.get("team", "")
        pos = p.get("positions", "")
        slot = p.get("roster_slot", "BN")

        # Check not already on another team
        cursor = await db.execute(
            "SELECT league_team_id FROM league_rosters WHERE player_id = ? AND is_active = 1",
            (pid,)
        )
        existing = await cursor.fetchone()
        if existing and existing["league_team_id"] != req.league_team_id:
            errors.append(f"{name} already on Team {existing['league_team_id']}")
            continue

        await add_to_roster(db, req.league_team_id, pid, name, team, pos, slot)
        added += 1

    await db.commit()
    return {"success": True, "added": added, "errors": errors}


@router.post("/drop")
async def drop_player(req: RosterDropRequest):
    """Drop a player from a league team's roster."""
    db = await get_db()
    await drop_from_roster(db, req.league_team_id, req.player_id)
    await db.commit()
    return {"success": True, "message": "Player dropped"}


@router.post("/move")
async def move_player_slot(req: RosterMoveRequest):
    """Move a player to a different roster slot."""
    db = await get_db()

    # Validate slot exists
    if req.new_slot not in SLOT_LIMITS:
        return {"error": f"Invalid slot: {req.new_slot}", "success": False}

    # Check slot has room (excluding this player's current slot)
    roster = await get_roster(db, req.league_team_id)
    count_in_new_slot = sum(
        1 for r in roster
        if r["roster_slot"] == req.new_slot and r["player_id"] != req.player_id
    )
    if count_in_new_slot >= SLOT_LIMITS[req.new_slot]:
        return {"error": f"No room in {req.new_slot} slot", "success": False}

    await move_roster_slot(db, req.league_team_id, req.player_id, req.new_slot)
    await db.commit()
    return {"success": True, "message": f"Moved to {req.new_slot}"}


@router.get("/available-slots")
async def get_available_slots(league_team_id: int = Query(1, ge=1, le=10)):
    """Get which roster slots have open spots."""
    db = await get_db()
    slot_counts = await get_roster_slot_counts(db, league_team_id)
    available = {}
    for slot, limit in SLOT_LIMITS.items():
        current = slot_counts.get(slot, 0)
        available[slot] = {"limit": limit, "filled": current, "open": limit - current}
    return {"slots": available, "league_team_id": league_team_id}


# --- CSV Upload ---

@router.post("/upload-csv")
async def upload_roster_csv(
    file: UploadFile = File(...),
    league_team_id: int = Query(1, ge=1, le=10),
):
    """Upload a Yahoo Fantasy CSV export to populate a team's roster."""
    db = await get_db()
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    all_players = await get_all_players(db)
    player_names = {p["player_name"]: p for p in all_players}
    name_list = list(player_names.keys())

    matched = []
    unmatched = []

    for row in reader:
        name = row.get("Player") or row.get("player") or row.get("Name") or row.get("name", "")
        pos = row.get("Position") or row.get("position") or row.get("Pos") or row.get("pos", "BN")
        if not name:
            continue

        clean_name = name.split(" - ")[0].strip()
        parts = clean_name.rsplit(" ", 1)
        if len(parts) == 2 and len(parts[1]) <= 3 and parts[1].isupper():
            clean_name = parts[0]

        matches = difflib.get_close_matches(clean_name, name_list, n=1, cutoff=0.7)
        if matches:
            player = player_names[matches[0]]
            matched.append({
                "input_name": name,
                "matched_name": player["player_name"],
                "player_id": player["player_id"],
                "team": player["team"],
                "positions": player["positions"],
                "roster_slot": pos.upper() if pos else "BN",
                "confidence": difflib.SequenceMatcher(None, clean_name, matches[0]).ratio(),
            })
        else:
            unmatched.append({"input_name": name, "position": pos})

    return {
        "matched": matched,
        "unmatched": unmatched,
        "total_parsed": len(matched) + len(unmatched),
        "league_team_id": league_team_id,
    }


@router.post("/upload-csv/confirm")
async def confirm_csv_upload(
    players: list[dict],
    league_team_id: int = Query(1, ge=1, le=10),
):
    """Confirm and save matched players from CSV upload."""
    db = await get_db()
    added = 0
    for p in players:
        await add_to_roster(
            db, league_team_id, p["player_id"], p["matched_name"],
            p.get("team"), p.get("positions"), p.get("roster_slot", "BN")
        )
        added += 1
    await db.commit()
    return {"success": True, "added": added}


# --- Drop Candidates ---

@router.get("/drop-candidates")
async def get_drop_candidates(
    window: str = Query("14d", regex="^(3d|7d|14d|30d|season)$"),
    league_team_id: int = Query(1, ge=1, le=10),
):
    """Identify weakest players on roster with replacement comparisons."""
    db = await get_db()
    ref_date = await get_reference_date(db)
    roster = await get_roster(db, league_team_id)
    all_rostered = set(await get_all_rostered_player_ids(db))

    if window == "season":
        start_date = f"{CURRENT_SEASON}-01-01"
    else:
        days = WINDOW_DAYS[window]
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        start_date = (ref_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = ref_date

    rs_cursor = await db.execute("SELECT * FROM team_run_support")
    rs_rows = await rs_cursor.fetchall()
    team_rs = {r["team_abbrev"]: dict(r) for r in rs_rows} if rs_rows else {}

    candidates = []
    for row in roster:
        pid = row["player_id"]
        logs = await get_player_game_logs(db, pid, start_date, end_date)
        gp = len(logs) if logs else 0
        total_pts = sum(r["fantasy_points"] for r in logs) if logs else 0
        ppg = total_pts / gp if gp > 0 else 0

        all_logs = await get_player_game_logs(db, pid)
        season_gp = len(all_logs) if all_logs else 0
        season_pts = sum(r["fantasy_points"] for r in all_logs) if all_logs else 0
        season_ppg = season_pts / season_gp if season_gp > 0 else 0
        trend = ppg - season_ppg

        pos = row["positions"] or row.get("primary_position", "")
        replacement = await _find_best_replacement(db, pos, all_rostered, start_date, end_date)
        upgrade_potential = (replacement["ppg"] - ppg) if replacement else 0

        recommendation = "hold"
        reason = None
        if upgrade_potential > 2:
            recommendation = "drop"
            reason = f"Replacement ({replacement['player_name']}) averages {replacement['ppg']:.1f} ppg vs your {ppg:.1f} ppg"
        elif upgrade_potential > 0.5:
            recommendation = "consider"
            reason = f"Marginal upgrade available: {replacement['player_name']} at {replacement['ppg']:.1f} ppg"

        is_pitcher = bool(row["is_pitcher"]) if "is_pitcher" in row.keys() else False
        if is_pitcher and row["team"] in team_rs:
            rs = team_rs[row["team"]]
            tier = rs.get("tier", "B")
            if tier in ("S", "A") and recommendation != "hold":
                recommendation = "hold"
                reason = f"Hold: {tier}-tier run support ({rs.get('runs_per_game', 0):.1f} R/G) — pitcher Win value is high"
            elif tier in ("D",) and recommendation == "hold" and ppg < 3:
                recommendation = "consider"
                reason = f"D-tier run support ({rs.get('runs_per_game', 0):.1f} R/G, rank #{rs.get('run_support_rank', 0)}) — limited Win upside"

        candidates.append({
            "player_id": pid,
            "player_name": row["player_name"],
            "team": row["team"],
            "positions": row["positions"],
            "roster_slot": row["roster_slot"],
            "is_pitcher": is_pitcher,
            "games_played": gp,
            "fantasy_points": round(total_pts, 2),
            "pts_per_game": round(ppg, 2),
            "season_ppg": round(season_ppg, 2),
            "trend": round(trend, 2),
            "replacement": replacement,
            "upgrade_potential": round(upgrade_potential, 2),
            "recommendation": recommendation,
            "reason": reason,
            "run_support_tier": team_rs.get(row["team"], {}).get("tier") if is_pitcher else None,
        })

    candidates.sort(key=lambda x: x["upgrade_potential"], reverse=True)
    return {"candidates": candidates, "window": window}


async def _find_best_replacement(db, position: str, rostered_ids: set,
                                  start_date: str, end_date: str) -> dict | None:
    """Find the best available free agent at a position."""
    all_players = await get_all_players(db)

    best = None
    best_ppg = -999

    for p in all_players:
        if p["player_id"] in rostered_ids:
            continue
        player_pos = p["primary_position"] or ""
        pos_match = False
        if position in ("OF", "LF", "CF", "RF") and player_pos in ("OF", "LF", "CF", "RF"):
            pos_match = True
        elif position in ("SP", "RP", "P") and player_pos in ("SP", "RP"):
            pos_match = True
        elif player_pos == position:
            pos_match = True

        if not pos_match:
            continue

        logs = await get_player_game_logs(db, p["player_id"], start_date, end_date)
        if not logs or len(logs) < 2:
            continue

        gp = len(logs)
        total = sum(r["fantasy_points"] for r in logs)
        ppg = total / gp

        if ppg > best_ppg:
            best_ppg = ppg
            best = {
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "team": p["team"],
                "position": player_pos,
                "games_played": gp,
                "ppg": round(ppg, 2),
            }

    return best


def _get_week_start() -> str:
    """Get the Monday of the current week."""
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()
