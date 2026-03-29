"""Matchup projection and schedule endpoints."""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

from db import (
    get_db, get_roster, get_player_game_logs, get_player_season_stats,
    get_all_team_run_support, get_reference_date,
    get_matchup_schedule, get_week_matchup, upsert_matchup, set_full_schedule,
    get_league_teams,
)
from services.run_support import calculate_wpps
from services.mlb_api import get_schedule
from models import MatchupProjectRequest
from config import CURRENT_SEASON
import math

router = APIRouter(prefix="/api/matchup", tags=["matchup"])

WINDOW_DAYS = {"3d": 3, "7d": 7, "14d": 14, "30d": 30, "season": 365}


# --- Schedule models ---

class MatchupEntry(BaseModel):
    week_number: int
    week_label: Optional[str] = ""
    week_start: str
    week_end: str
    team_a_id: int
    team_b_id: int


class FullScheduleRequest(BaseModel):
    matchups: list[MatchupEntry]


# --- Schedule endpoints ---

@router.get("/schedule")
async def get_season_schedule():
    """Get the full season matchup schedule."""
    db = await get_db()
    rows = await get_matchup_schedule(db)
    teams = await get_league_teams(db)
    team_map = {t["team_id"]: t["team_name"] for t in teams}

    # Group by week
    weeks = {}
    for row in rows:
        wn = row["week_number"]
        if wn not in weeks:
            weeks[wn] = {
                "week_number": wn,
                "week_label": row["week_label"],
                "week_start": row["week_start"],
                "week_end": row["week_end"],
                "matchups": [],
            }
        weeks[wn]["matchups"].append({
            "team_a_id": row["team_a_id"],
            "team_a_name": team_map.get(row["team_a_id"], f"Team {row['team_a_id']}"),
            "team_b_id": row["team_b_id"],
            "team_b_name": team_map.get(row["team_b_id"], f"Team {row['team_b_id']}"),
        })

    return {"weeks": list(weeks.values()), "teams": [dict(t) for t in teams]}


@router.post("/schedule")
async def save_schedule(req: FullScheduleRequest):
    """Save the full season matchup schedule."""
    db = await get_db()
    await set_full_schedule(db, [m.model_dump() for m in req.matchups])
    await db.commit()
    return {"success": True, "matchups_saved": len(req.matchups)}


@router.put("/schedule/week/{week_number}")
async def update_week_matchup(week_number: int, entry: MatchupEntry):
    """Update a single matchup for a specific week."""
    db = await get_db()
    await upsert_matchup(
        db, week_number, entry.week_label, entry.week_start, entry.week_end,
        entry.team_a_id, entry.team_b_id
    )
    await db.commit()
    return {"success": True}


@router.get("/schedule/my-week")
async def get_my_matchup(week_number: int = Query(...)):
    """Get my team's matchup for a specific week."""
    db = await get_db()
    row = await get_week_matchup(db, week_number, 1)
    if not row:
        return {"matchup": None}
    teams = await get_league_teams(db)
    team_map = {t["team_id"]: t["team_name"] for t in teams}
    opponent_id = row["team_b_id"] if row["team_a_id"] == 1 else row["team_a_id"]
    return {
        "matchup": {
            "week_number": row["week_number"],
            "week_label": row["week_label"],
            "week_start": row["week_start"],
            "week_end": row["week_end"],
            "opponent_id": opponent_id,
            "opponent_name": team_map.get(opponent_id, f"Team {opponent_id}"),
        }
    }


# --- Projection endpoint ---

@router.post("/project")
async def project_matchup(req: MatchupProjectRequest):
    """Project weekly matchup vs opponent."""
    db = await get_db()
    try:
        # Get schedule for game counts
        schedule = await get_schedule(req.week_start, req.week_end)
        team_games = _count_team_games(schedule)

        # Run support
        rs_rows = await get_all_team_run_support(db)
        team_rs = {}
        league_avg_rpg = 4.3
        if rs_rows:
            for rs in rs_rows:
                team_rs[rs["team_abbrev"]] = dict(rs)
            total = sum(r.get("runs_per_game", 0) for r in team_rs.values())
            if team_rs:
                league_avg_rpg = total / len(team_rs)

        # Window (use reference date, not utcnow)
        ref_date = await get_reference_date(db)
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        if req.window == "season":
            start_date = f"{CURRENT_SEASON}-01-01"
        else:
            days = WINDOW_DAYS.get(req.window, 14)
            start_date = (ref_dt - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = ref_date

        # Project my roster
        roster = await get_roster(db)
        my_total = await _project_roster(db, roster, start_date, end_date, team_games, team_rs, league_avg_rpg)

        # Project opponent
        opp_players = []
        for pid in req.opponent_roster:
            cursor = await db.execute(
                "SELECT p.*, ps.era, ps.games_started, ps.games_played as season_gp "
                "FROM players p LEFT JOIN player_season_stats ps ON p.player_id = ps.player_id "
                "WHERE p.player_id = ?", (pid,)
            )
            row = await cursor.fetchone()
            if row:
                opp_players.append(row)

        opp_total = 0
        for row in opp_players:
            pid = row["player_id"]
            team = row["team"] or ""
            is_pitcher = bool(row["is_pitcher"])

            logs = await get_player_game_logs(db, pid, start_date, end_date)
            gp = len(logs) if logs else 0
            total_pts = sum(r["fantasy_points"] for r in logs) if logs else 0
            ppg = total_pts / gp if gp > 0 else 0

            games = team_games.get(team, 0)
            proj = ppg * games

            if is_pitcher and team in team_rs:
                rs = team_rs[team]
                era = row["era"] if row["era"] else 4.50
                wpps = calculate_wpps(
                    era, rs.get("runs_per_game", league_avg_rpg),
                    league_avg_rpg, 4.20,
                    is_starter=(row["primary_position"] == "SP")
                )
                if row["primary_position"] == "SP":
                    proj += wpps * 1 * 10 + 0.20 * 1 * -5

            opp_total += proj

        # Win probability
        my_std = max(my_total * 0.18, 10)
        opp_std = max(opp_total * 0.18, 10)
        diff = my_total - opp_total
        combined_std = math.sqrt(my_std**2 + opp_std**2)
        win_prob = 0.5 * (1 + math.erf(diff / (combined_std * math.sqrt(2)))) if combined_std > 0 else 0.5

        return {
            "my_projected_pts": round(my_total, 1),
            "opponent_projected_pts": round(opp_total, 1),
            "win_probability": round(win_prob, 3),
            "week": {"start": req.week_start, "end": req.week_end},
        }
    finally:
        pass  # shared connection


async def _project_roster(db, roster, start_date, end_date, team_games, team_rs, league_avg_rpg):
    """Project total points for a roster."""
    total = 0
    for row in roster:
        pid = row["player_id"]
        team = row["team"] or ""
        is_pitcher = bool(row["is_pitcher"]) if "is_pitcher" in row.keys() else False

        logs = await get_player_game_logs(db, pid, start_date, end_date)
        gp = len(logs) if logs else 0
        total_pts = sum(r["fantasy_points"] for r in logs) if logs else 0
        ppg = total_pts / gp if gp > 0 else 0

        games = team_games.get(team, 0)
        proj = ppg * games

        if is_pitcher and team in team_rs:
            rs = team_rs[team]
            season = await get_player_season_stats(db, pid)
            era = season["era"] if season and season["era"] else 4.50
            wpps = calculate_wpps(
                era, rs.get("runs_per_game", league_avg_rpg),
                league_avg_rpg, 4.20,
                is_starter=(row.get("primary_position") == "SP")
            )
            if row.get("primary_position") == "SP":
                proj += wpps * 1 * 10 + 0.20 * 1 * -5

        total += proj
    return total


def _count_team_games(schedule):
    counts = {}
    for game in schedule:
        away = game.get("teams", {}).get("away", {}).get("team", {}).get("abbreviation", "")
        home = game.get("teams", {}).get("home", {}).get("team", {}).get("abbreviation", "")
        if away:
            counts[away] = counts.get(away, 0) + 1
        if home:
            counts[home] = counts.get(home, 0) + 1
    return counts
