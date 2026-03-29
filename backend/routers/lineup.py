"""Start/sit lineup optimizer endpoints."""

from fastapi import APIRouter
from datetime import datetime, timedelta

from db import (
    get_db, get_roster, get_player_game_logs, get_player_season_stats,
    get_all_team_run_support, get_reference_date,
)
from services.optimizer import optimize_lineup
from services.run_support import calculate_wpps
from services.mlb_api import get_schedule
from models import LineupOptimizeRequest
from config import CURRENT_SEASON

router = APIRouter(prefix="/api/lineup", tags=["lineup"])

WINDOW_DAYS = {"3d": 3, "7d": 7, "14d": 14, "30d": 30, "season": 365}


@router.post("/optimize")
async def optimize(req: LineupOptimizeRequest):
    """Optimize lineup for a given week."""
    db = await get_db()
    try:
        roster = await get_roster(db)
        if not roster:
            return {"error": "No roster loaded. Add players first."}

        # Get schedule for the week to count games per team
        schedule = await get_schedule(req.week_start, req.week_end)
        team_games = _count_team_games(schedule)

        # Get run support data
        rs_rows = await get_all_team_run_support(db)
        team_rs = {}
        league_avg_rpg = 4.3
        if rs_rows:
            for rs in rs_rows:
                team_rs[rs["team_abbrev"]] = dict(rs)
            total = sum(r.get("runs_per_game", 0) for r in team_rs.values())
            if team_rs:
                league_avg_rpg = total / len(team_rs)

        # Window for recent performance (use reference date, not utcnow)
        ref_date = await get_reference_date(db)
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        if req.window == "season":
            start_date = f"{CURRENT_SEASON}-01-01"
        else:
            days = WINDOW_DAYS.get(req.window, 14)
            start_date = (ref_dt - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = ref_date

        # Build player projection data
        players = []
        for row in roster:
            pid = row["player_id"]
            team = row["team"] or ""
            is_pitcher = bool(row["is_pitcher"]) if "is_pitcher" in row.keys() else False

            logs = await get_player_game_logs(db, pid, start_date, end_date)
            gp = len(logs) if logs else 0
            total_pts = sum(r["fantasy_points"] for r in logs) if logs else 0
            ppg = total_pts / gp if gp > 0 else 0

            # Games this week
            games_this_week = team_games.get(team, 0)

            # Pitcher-specific: use win-adjusted projections
            projected_total = ppg * games_this_week

            if is_pitcher and team in team_rs:
                rs = team_rs[team]
                season = await get_player_season_stats(db, pid)
                era = season["era"] if season and season["era"] else 4.50
                gs = season["games_started"] if season else 0
                games = season["games_played"] if season else 0

                wpps = calculate_wpps(
                    era, rs.get("runs_per_game", league_avg_rpg),
                    league_avg_rpg, 4.20,
                    is_starter=(row.get("primary_position") == "SP")
                )

                # Estimate starts this week
                if row.get("primary_position") == "SP":
                    # SP: typically 1 start per week, maybe 2
                    starts_per_week = gs / (games / 5) if games > 0 else 1
                    starts_this_week = min(round(starts_per_week), 2)
                else:
                    starts_this_week = 0

                win_bonus = wpps * starts_this_week * 10
                loss_penalty = min(0.30, max(0.05, 0.25 - wpps * 0.3)) * starts_this_week * -5
                projected_total += win_bonus + loss_penalty

            positions = row["positions"] or row.get("primary_position", "")

            players.append({
                "player_id": pid,
                "player_name": row["player_name"],
                "team": team,
                "positions": positions,
                "is_pitcher": is_pitcher,
                "projected_pts_per_game": round(ppg, 2),
                "games_this_week": games_this_week,
                "projected_total": round(projected_total, 2),
                "run_support_tier": team_rs.get(team, {}).get("tier") if is_pitcher else None,
            })

        # Run optimizer
        result = optimize_lineup(players, team_games)

        return {
            "optimal_lineup": result["lineup"],
            "bench": result["bench"],
            "total_projected_pts": result["total_projected_pts"],
            "notes": result["notes"],
            "week": {"start": req.week_start, "end": req.week_end},
        }
    finally:
        pass  # shared connection


def _count_team_games(schedule: list[dict]) -> dict[str, int]:
    """Count games per team from a schedule response."""
    counts = {}
    for game in schedule:
        away = game.get("teams", {}).get("away", {}).get("team", {}).get("abbreviation", "")
        home = game.get("teams", {}).get("home", {}).get("team", {}).get("abbreviation", "")
        if away:
            counts[away] = counts.get(away, 0) + 1
        if home:
            counts[home] = counts.get(home, 0) + 1
    return counts
