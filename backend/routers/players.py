"""Player stats & rankings endpoints."""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from db import (
    get_db, get_all_players, get_player_season_stats, get_player_game_logs,
    get_all_rostered_player_ids, get_all_team_run_support, get_reference_date,
)
from services.scoring import calc_batter_points, calc_pitcher_points, calc_game_batter_points, calc_game_pitcher_points
from services.run_support import calculate_wpps
from services.mlb_api import search_player
from config import CURRENT_SEASON

router = APIRouter(prefix="/api/players", tags=["players"])

WINDOW_DAYS = {"3d": 3, "7d": 7, "14d": 14, "30d": 30, "season": 365}


@router.get("/available")
async def get_available_players(
    window: str = Query("7d", pattern="^(3d|7d|14d|30d|season)$"),
    position: str = Query("ALL"),
    limit: int = Query(50, ge=1, le=200),
    sort: str = Query("pts_per_game"),
):
    """Waiver wire: best available free agents ranked by fantasy points."""
    db = await get_db()
    # Exclude ALL rostered players across all 10 league teams
    rostered_ids = set(await get_all_rostered_player_ids(db))

    all_players = await get_all_players(db)

    # Get reference date (latest game date in DB)
    ref_date = await get_reference_date(db)
    ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")

    # Get run support data for pitcher adjustments
    run_support_rows = await get_all_team_run_support(db)
    team_rs = {}
    league_avg_rpg = 0
    league_avg_era = 4.20
    if run_support_rows:
        for rs in run_support_rows:
            team_rs[rs["team_abbrev"] if "team_abbrev" in rs.keys() else rs["team_name"]] = dict(rs)
        total_rpg = sum(r.get("runs_per_game", 0) for r in team_rs.values())
        if team_rs:
            league_avg_rpg = total_rpg / len(team_rs)

    # Calculate window date range using reference date
    if window == "season":
        start_date = f"{CURRENT_SEASON}-01-01"
    else:
        days = WINDOW_DAYS[window]
        start_date = (ref_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = ref_date

    results = []
    for player in all_players:
        pid = player["player_id"]
        if pid in rostered_ids:
            continue

        player_pos = player["primary_position"] or ""
        is_pitcher = bool(player["is_pitcher"])

        if position != "ALL":
            if position == "batter" and is_pitcher:
                continue
            elif position == "pitcher" and not is_pitcher:
                continue
            elif position == "OF" and player_pos not in ("OF", "LF", "CF", "RF"):
                continue
            elif position not in ("batter", "pitcher", "OF") and player_pos != position:
                continue

        logs = await get_player_game_logs(db, pid, start_date, end_date)
        if not logs:
            continue

        games = len(logs)
        total_pts = sum(row["fantasy_points"] for row in logs)
        pts_per_game = total_pts / games if games > 0 else 0

        season = await get_player_season_stats(db, pid)
        # Compute season PPG from game logs within current season only
        season_start = f"{CURRENT_SEASON}-01-01"
        all_logs = await get_player_game_logs(db, pid, start_date=season_start)
        season_gp = len(all_logs)
        season_pts = sum(row["fantasy_points"] for row in all_logs)
        season_ppg = season_pts / season_gp if season_gp > 0 else 0

        trend = pts_per_game - season_ppg if season_ppg > 0 else 0

        entry = {
            "player_id": pid,
            "player_name": player["player_name"],
            "team": player["team"],
            "positions": player["positions"],
            "primary_position": player_pos,
            "is_pitcher": is_pitcher,
            "games_played": games,
            "fantasy_points": round(total_pts, 2),
            "pts_per_game": round(pts_per_game, 2),
            "season_pts": round(season_pts, 2),
            "season_ppg": round(season_ppg, 2),
            "trend": round(trend, 2),
        }

        if is_pitcher and player["team"] in team_rs:
            rs = team_rs[player["team"]]
            entry["team_rpg"] = rs.get("runs_per_game", 0)
            entry["run_support_rank"] = rs.get("run_support_rank", 0)
            entry["run_support_tier"] = rs.get("tier", "B")

            era = season["era"] if season and season["era"] else 4.50
            wpps = calculate_wpps(
                era, rs.get("runs_per_game", league_avg_rpg),
                league_avg_rpg, league_avg_era,
                is_starter=(player_pos == "SP")
            )
            gs = season["games_started"] if season else 0
            gp = season["games_played"] if season else 0
            starts_per_game = gs / gp if gp > 0 else (1.0 if player_pos == "SP" else 0.0)
            win_adj = wpps * starts_per_game * 10
            entry["win_adjusted_ppg"] = round(pts_per_game + win_adj, 2)
        else:
            entry["win_adjusted_ppg"] = round(pts_per_game, 2)

        results.append(entry)

    if sort == "total_pts":
        results.sort(key=lambda x: x["fantasy_points"], reverse=True)
    elif sort == "trend":
        results.sort(key=lambda x: x["trend"], reverse=True)
    elif sort == "pts_per_game":
        results.sort(key=lambda x: x.get("win_adjusted_ppg", x["pts_per_game"]), reverse=True)
    else:
        results.sort(key=lambda x: x["pts_per_game"], reverse=True)

    return {"players": results[:limit], "total": len(results), "window": window, "ref_date": ref_date}


@router.get("/search")
async def search_players(q: str = Query(..., min_length=2)):
    """Search for a player by name. Returns virtual split entries for two-way players."""
    from config import TWO_WAY_PLAYERS

    results = await search_player(q)
    players = []
    two_way_base_ids = set(TWO_WAY_PLAYERS.keys())

    for p in results[:20]:
        pid = p.get("id")
        if pid in two_way_base_ids:
            # Replace base player with the two virtual entries
            twp = TWO_WAY_PLAYERS[pid]
            team_abbrev = p.get("currentTeam", {}).get("abbreviation", "")
            players.append({
                "player_id": twp["batter_id"],
                "player_name": twp["batter_name"],
                "team": team_abbrev,
                "position": "DH",
            })
            players.append({
                "player_id": twp["pitcher_id"],
                "player_name": twp["pitcher_name"],
                "team": team_abbrev,
                "position": "SP",
            })
        else:
            players.append({
                "player_id": pid,
                "player_name": p.get("fullName"),
                "team": p.get("currentTeam", {}).get("abbreviation", ""),
                "position": p.get("primaryPosition", {}).get("abbreviation", ""),
            })

    # Also search local DB for virtual players (in case MLB API doesn't return them)
    db = await get_db()
    q_lower = q.lower()
    cursor = await db.execute(
        "SELECT player_id, player_name, team, primary_position FROM players WHERE LOWER(player_name) LIKE ?",
        (f"%{q_lower}%",)
    )
    local_rows = await cursor.fetchall()
    existing_ids = {p["player_id"] for p in players}
    for row in local_rows:
        if row["player_id"] not in existing_ids:
            players.append({
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "team": row["team"],
                "position": row["primary_position"],
            })

    return {"players": players[:30]}


@router.get("/{player_id}")
async def get_player_detail(player_id: int):
    """Get detailed player info with stats and game logs."""
    db = await get_db()
    ref_date = await get_reference_date(db)
    ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")

    cursor = await db.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    player = await cursor.fetchone()
    if not player:
        return {"error": "Player not found"}

    season = await get_player_season_stats(db, player_id)
    logs = await get_player_game_logs(db, player_id)

    cutoff = (ref_dt - timedelta(days=14)).strftime("%Y-%m-%d")
    recent_logs = [dict(row) for row in logs if row["game_date"] >= cutoff]

    return {
        "player": dict(player),
        "season_stats": dict(season) if season else None,
        "recent_game_logs": recent_logs,
        "total_game_logs": len(logs),
    }


@router.get("/run-support/rankings")
async def get_run_support_rankings():
    """Get all 30 MLB teams ranked by run support."""
    db = await get_db()
    rows = await get_all_team_run_support(db)
    return {"teams": [dict(row) for row in rows]}
