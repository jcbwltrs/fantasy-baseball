"""Scheduled stat refresh job — fetches all player data and team run support."""

import asyncio
import logging
from datetime import datetime

from db import (
    get_db, upsert_player, upsert_season_stats, upsert_game_log,
    upsert_team_run_support, get_all_team_run_support,
)
from services.mlb_api import (
    get_all_teams, get_team_roster, get_player_season_stats,
    get_player_game_logs, get_standings,
)
from services.scoring import calc_batter_points, calc_pitcher_points, calc_game_batter_points, calc_game_pitcher_points
from services.run_support import calculate_run_support_tier, blend_run_support
from config import CURRENT_SEASON, TWO_WAY_PLAYERS

logger = logging.getLogger(__name__)

# Position mappings from MLB API
PITCHER_POSITIONS = {"P", "SP", "RP", "TWP"}  # TWP = two-way player


async def refresh_all_data():
    """Full data refresh: teams, rosters, stats, run support."""
    logger.info("Starting full data refresh...")
    start = datetime.utcnow()

    db = await get_db()
    try:
        # Step 1: Fetch all teams
        teams = await get_all_teams()
        logger.info(f"Fetched {len(teams)} teams")

        team_id_to_abbrev = {}
        for team in teams:
            team_id_to_abbrev[team["id"]] = team.get("abbreviation", "")

        # Step 2: Fetch and store team run support data from standings
        await _refresh_run_support(db, teams)

        # Step 3: Fetch all rosters first (sequential — one per team)
        all_player_entries = []
        for team in teams:
            team_id = team["id"]
            team_abbrev = team.get("abbreviation", "")
            roster = await get_team_roster(team_id)
            logger.info(f"  {team_abbrev}: {len(roster)} players")

            for entry in roster:
                person = entry.get("person", {})
                player_id = person.get("id")
                if not player_id:
                    continue
                player_name = person.get("fullName", "Unknown")
                position = entry.get("position", {})
                pos_abbrev = position.get("abbreviation", "")
                pos_type = position.get("type", "")
                is_pitcher = pos_abbrev in PITCHER_POSITIONS or pos_type == "Pitcher"

                await upsert_player(
                    db, player_id, player_name, team_abbrev, team_id,
                    pos_abbrev, pos_abbrev, is_pitcher
                )
                all_player_entries.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "is_pitcher": is_pitcher,
                })

        # Step 3b: Split two-way players into separate batter/pitcher entries
        for base_id, twp in TWO_WAY_PLAYERS.items():
            # Find the original player entry
            original = None
            for entry in all_player_entries:
                if entry["player_id"] == base_id:
                    original = entry
                    break
            if not original:
                continue

            # Look up the original player's team
            cursor = await db.execute("SELECT team, team_id FROM players WHERE player_id = ?", (base_id,))
            orig_row = await cursor.fetchone()
            team_abbrev = orig_row["team"] if orig_row else ""
            orig_team_id = orig_row["team_id"] if orig_row else 0

            # Create batter virtual player
            await upsert_player(
                db, twp["batter_id"], twp["batter_name"], team_abbrev, orig_team_id,
                "DH", "DH", False
            )
            # Create pitcher virtual player
            await upsert_player(
                db, twp["pitcher_id"], twp["pitcher_name"], team_abbrev, orig_team_id,
                "SP", "SP", True
            )
            # Add virtual entries to the fetch list
            all_player_entries.append({
                "player_id": twp["batter_id"],
                "player_name": twp["batter_name"],
                "is_pitcher": False,
                "virtual_base_id": base_id,
            })
            all_player_entries.append({
                "player_id": twp["pitcher_id"],
                "player_name": twp["pitcher_name"],
                "is_pitcher": True,
                "virtual_base_id": base_id,
            })
            logger.info(f"  Split two-way player {original['player_name']} into batter ({twp['batter_id']}) and pitcher ({twp['pitcher_id']})")

        await db.commit()
        logger.info(f"Stored {len(all_player_entries)} player records. Fetching stats in parallel...")

        # Step 4: Fetch stats in parallel batches (10 concurrent requests)
        sem = asyncio.Semaphore(10)
        total_players = 0
        errors = 0

        async def fetch_player_stats(entry):
            nonlocal total_players, errors
            pid = entry["player_id"]
            is_pitcher = entry["is_pitcher"]
            group = "pitching" if is_pitcher else "hitting"

            # For virtual two-way players, fetch using the real MLB ID
            api_pid = entry.get("virtual_base_id", pid)

            async with sem:
                try:
                    season_stats = await get_player_season_stats(api_pid, group)
                    if season_stats:
                        stats_dict = _map_season_stats(season_stats, is_pitcher)
                        if is_pitcher:
                            stats_dict["fantasy_points"] = calc_pitcher_points(season_stats)
                        else:
                            stats_dict["fantasy_points"] = calc_batter_points(season_stats)
                        await upsert_season_stats(db, pid, CURRENT_SEASON, stats_dict)

                    game_logs = await get_player_game_logs(api_pid, group)
                    for gl in game_logs:
                        game_date = gl.get("date", "")
                        game_info = gl.get("game", {})
                        game_id = game_info.get("gamePk", 0)
                        opponent = gl.get("opponent", {}).get("abbreviation", "")
                        stat = gl.get("stat", {})

                        if is_pitcher:
                            fpts = calc_game_pitcher_points(stat)
                        else:
                            fpts = calc_game_batter_points(stat)

                        game_stats = _map_game_stats(stat, is_pitcher)
                        await upsert_game_log(
                            db, pid, game_date, game_id, opponent,
                            is_pitcher, game_stats, fpts
                        )
                    total_players += 1
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error fetching stats for {entry['player_name']} ({pid}): {e}")

        # Process in batches of 30
        batch_size = 30
        for i in range(0, len(all_player_entries), batch_size):
            batch = all_player_entries[i:i + batch_size]
            await asyncio.gather(*[fetch_player_stats(e) for e in batch])
            await db.commit()
            logger.info(f"  Progress: {min(i + batch_size, len(all_player_entries))}/{len(all_player_entries)} players")

        if errors:
            logger.warning(f"{errors} players had errors during stat fetch")

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(f"Data refresh complete: {total_players} players in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Data refresh failed: {e}", exc_info=True)
        raise
    finally:
        pass  # shared connection


async def _refresh_run_support(db, teams: list[dict]):
    """Fetch standings and calculate run support for all teams."""
    standings = await get_standings()
    if not standings:
        logger.warning("No standings data available — skipping run support refresh")
        return

    # Collect team data
    team_data = []
    for record in standings:
        team_info = record.get("team", {})
        team_id = team_info.get("id")
        if not team_id:
            continue

        wins = int(record.get("wins", 0))
        losses = int(record.get("losses", 0))
        games = wins + losses
        rs = int(record.get("runsScored", 0))
        ra = int(record.get("runsAllowed", 0))

        # Find team abbreviation
        team_abbrev = ""
        team_name = team_info.get("name", "")
        for t in teams:
            if t["id"] == team_id:
                team_abbrev = t.get("abbreviation", "")
                team_name = t.get("name", team_name)
                break

        rpg = rs / games if games > 0 else 0
        rapg = ra / games if games > 0 else 0
        win_pct = wins / games if games > 0 else 0

        # Apply early-season blending
        blended_rpg = blend_run_support(rpg, team_abbrev, games)

        team_data.append({
            "team_id": team_id,
            "team_name": team_name,
            "team_abbrev": team_abbrev,
            "games_played": games,
            "runs_scored": rs,
            "runs_allowed": ra,
            "run_differential": rs - ra,
            "runs_per_game": round(blended_rpg, 3),
            "runs_allowed_per_game": round(rapg, 3),
            "win_pct": round(win_pct, 3),
        })

    # Calculate ranks
    team_data.sort(key=lambda t: t["runs_per_game"], reverse=True)
    for i, t in enumerate(team_data):
        t["run_support_rank"] = i + 1

    team_data.sort(key=lambda t: t["run_differential"], reverse=True)
    for i, t in enumerate(team_data):
        t["run_diff_rank"] = i + 1

    # Calculate tiers
    for t in team_data:
        t["tier"] = calculate_run_support_tier(
            t["runs_per_game"], t["run_differential"],
            t["run_support_rank"], t["run_diff_rank"],
            total_teams=len(team_data)
        )

    # Store in DB
    for t in team_data:
        await upsert_team_run_support(
            db, t["team_id"], t["team_name"], t["team_abbrev"], t
        )

    await db.commit()
    logger.info(f"Run support data refreshed for {len(team_data)} teams")


def _map_season_stats(stats: dict, is_pitcher: bool) -> dict:
    """Map MLB API stat fields to our database columns."""
    if is_pitcher:
        return {
            "games_played": _safe_int(stats, "gamesPlayed"),
            "appearances": _safe_int(stats, "gamesPitched"),
            "innings_pitched": _safe_float(stats, "inningsPitched"),
            "wins": _safe_int(stats, "wins"),
            "losses": _safe_int(stats, "losses"),
            "complete_games": _safe_int(stats, "completeGames"),
            "saves": _safe_int(stats, "saves"),
            "hits_allowed": _safe_int(stats, "hits"),
            "earned_runs": _safe_int(stats, "earnedRuns"),
            "home_runs_allowed": _safe_int(stats, "homeRuns"),
            "walks_allowed": _safe_int(stats, "baseOnBalls"),
            "hit_batters": _safe_int(stats, "hitBatsmen"),
            "pitcher_strikeouts": _safe_int(stats, "strikeOuts"),
            "pitcher_gidp": _safe_int(stats, "groundIntoDoublePlay"),
            "holds": _safe_int(stats, "holds"),
            "blown_saves": _safe_int(stats, "blownSaves"),
            "games_started": _safe_int(stats, "gamesStarted"),
            "era": _safe_float(stats, "era"),
        }
    else:
        return {
            "games_played": _safe_int(stats, "gamesPlayed"),
            "runs": _safe_int(stats, "runs"),
            "hits": _safe_int(stats, "hits"),
            "doubles": _safe_int(stats, "doubles"),
            "triples": _safe_int(stats, "triples"),
            "home_runs": _safe_int(stats, "homeRuns"),
            "rbi": _safe_int(stats, "rbi"),
            "sac_hits": _safe_int(stats, "sacBunts"),
            "stolen_bases": _safe_int(stats, "stolenBases"),
            "caught_stealing": _safe_int(stats, "caughtStealing"),
            "walks": _safe_int(stats, "baseOnBalls"),
            "hit_by_pitch": _safe_int(stats, "hitByPitch"),
            "strikeouts": _safe_int(stats, "strikeOuts"),
            "gidp": _safe_int(stats, "groundIntoDoublePlay"),
        }


def _map_game_stats(stats: dict, is_pitcher: bool) -> dict:
    """Map MLB API game log stat fields to our game_logs columns."""
    if is_pitcher:
        return {
            "innings_pitched": _safe_float(stats, "inningsPitched"),
            "pitcher_wins": _safe_int(stats, "wins"),
            "pitcher_losses": _safe_int(stats, "losses"),
            "complete_games": _safe_int(stats, "completeGames"),
            "saves": _safe_int(stats, "saves"),
            "hits_allowed": _safe_int(stats, "hits"),
            "earned_runs": _safe_int(stats, "earnedRuns"),
            "home_runs_allowed": _safe_int(stats, "homeRuns"),
            "walks_allowed": _safe_int(stats, "baseOnBalls"),
            "hit_batters": _safe_int(stats, "hitBatsmen"),
            "pitcher_strikeouts": _safe_int(stats, "strikeOuts"),
            "pitcher_gidp": _safe_int(stats, "groundIntoDoublePlay"),
            "holds": _safe_int(stats, "holds"),
            "blown_saves": _safe_int(stats, "blownSaves"),
        }
    else:
        return {
            "runs": _safe_int(stats, "runs"),
            "hits": _safe_int(stats, "hits"),
            "doubles": _safe_int(stats, "doubles"),
            "triples": _safe_int(stats, "triples"),
            "home_runs": _safe_int(stats, "homeRuns"),
            "rbi": _safe_int(stats, "rbi"),
            "sac_hits": _safe_int(stats, "sacBunts"),
            "stolen_bases": _safe_int(stats, "stolenBases"),
            "caught_stealing": _safe_int(stats, "caughtStealing"),
            "walks": _safe_int(stats, "baseOnBalls"),
            "hit_by_pitch": _safe_int(stats, "hitByPitch"),
            "strikeouts": _safe_int(stats, "strikeOuts"),
            "gidp": _safe_int(stats, "groundIntoDoublePlay"),
        }


def _safe_int(d, key):
    try:
        return int(d.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0


def _safe_float(d, key):
    try:
        return float(d.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0.0
