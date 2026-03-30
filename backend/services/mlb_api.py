"""MLB Stats API client with retry logic and rate limiting."""

import httpx
import asyncio
import logging
from config import MLB_API_BASE, REQUEST_DELAY_MS, CURRENT_SEASON

logger = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds — exponential backoff


async def _request(path: str, params: dict = None) -> dict | None:
    """Make a GET request to the MLB Stats API with retries."""
    url = f"{MLB_API_BASE}{path}"
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning(f"MLB API request failed (attempt {attempt+1}/{MAX_RETRIES}): {url} — {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[attempt])
            else:
                logger.error(f"MLB API request exhausted retries: {url}")
                return None


async def _delay():
    """Rate limiting delay between requests."""
    await asyncio.sleep(REQUEST_DELAY_MS / 1000)


async def get_all_teams() -> list[dict]:
    """Get all MLB teams."""
    data = await _request("/teams", {"sportId": 1, "season": CURRENT_SEASON})
    if not data:
        return []
    return data.get("teams", [])


async def get_team_roster(team_id: int) -> list[dict]:
    """Get active roster for a team."""
    data = await _request(f"/teams/{team_id}/roster", {"rosterType": "active"})
    await _delay()
    if not data:
        return []
    return data.get("roster", [])


async def get_player_info(player_id: int) -> dict | None:
    """Get player details."""
    data = await _request(f"/people/{player_id}")
    await _delay()
    if not data or not data.get("people"):
        return None
    return data["people"][0]


async def get_player_season_stats(player_id: int, group: str = "hitting") -> dict | None:
    """Get player season stats. group = 'hitting' or 'pitching'."""
    data = await _request(f"/people/{player_id}/stats", {
        "stats": "season",
        "season": CURRENT_SEASON,
        "group": group,
    })
    await _delay()
    if not data:
        return None
    stats_list = data.get("stats", [])
    if not stats_list:
        return None
    splits = stats_list[0].get("splits", [])
    if not splits:
        return None
    return splits[0].get("stat", {})


async def get_player_game_logs(player_id: int, group: str = "hitting") -> list[dict]:
    """Get player game logs for current season."""
    data = await _request(f"/people/{player_id}/stats", {
        "stats": "gameLog",
        "season": CURRENT_SEASON,
        "group": group,
    })
    await _delay()
    if not data:
        return []
    stats_list = data.get("stats", [])
    if not stats_list:
        return []
    splits = stats_list[0].get("splits", [])
    return splits


async def get_standings() -> list[dict]:
    """Get standings for all divisions (includes run data)."""
    data = await _request("/standings", {
        "leagueId": "103,104",
        "season": CURRENT_SEASON,
    })
    if not data:
        return []
    records = data.get("records", [])
    teams = []
    for division in records:
        for team_record in division.get("teamRecords", []):
            teams.append(team_record)
    return teams


async def get_schedule(start_date: str, end_date: str) -> list[dict]:
    """Get game schedule for a date range."""
    data = await _request("/schedule", {
        "sportId": 1,
        "startDate": start_date,
        "endDate": end_date,
        "hydrate": "team",
    })
    if not data:
        return []
    games = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            games.append(game)
    return games


async def search_player(name: str) -> list[dict]:
    """Search for a player by name."""
    data = await _request("/people/search", {"names": name})
    if not data:
        return []
    return data.get("people", [])


async def get_team_stats(team_id: int, group: str = "hitting") -> dict | None:
    """Get team season stats."""
    data = await _request(f"/teams/{team_id}/stats", {
        "stats": "season",
        "season": CURRENT_SEASON,
        "group": group,
    })
    await _delay()
    if not data:
        return None
    stats_list = data.get("stats", [])
    if not stats_list:
        return None
    splits = stats_list[0].get("splits", [])
    if not splits:
        return None
    return splits[0].get("stat", {})
