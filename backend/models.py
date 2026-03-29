"""Pydantic models for API requests and responses."""

from pydantic import BaseModel
from typing import Optional


class PlayerBase(BaseModel):
    player_id: int
    player_name: str
    team: Optional[str] = None
    team_id: Optional[int] = None
    positions: Optional[str] = None  # comma-separated
    primary_position: Optional[str] = None
    is_pitcher: bool = False


class PlayerStats(PlayerBase):
    games_played: int = 0
    # Batter stats
    runs: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbi: int = 0
    sac_hits: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    walks: int = 0
    hit_by_pitch: int = 0
    strikeouts: int = 0
    gidp: int = 0
    # Pitcher stats
    appearances: int = 0
    innings_pitched: float = 0.0
    wins: int = 0
    losses: int = 0
    complete_games: int = 0
    saves: int = 0
    hits_allowed: int = 0
    earned_runs: int = 0
    home_runs_allowed: int = 0
    walks_allowed: int = 0
    hit_batters: int = 0
    pitcher_strikeouts: int = 0
    pitcher_gidp: int = 0
    holds: int = 0
    blown_saves: int = 0
    games_started: int = 0
    era: float = 0.0
    # Calculated
    fantasy_points: float = 0.0
    fantasy_pts_per_game: float = 0.0
    # Run support (pitchers)
    run_support_tier: Optional[str] = None
    team_rpg: Optional[float] = None
    run_support_rank: Optional[int] = None
    win_adjusted_pts_per_game: Optional[float] = None


class PlayerGameLog(BaseModel):
    player_id: int
    game_date: str
    opponent: Optional[str] = None
    # Raw stats per game (same fields as above but per-game)
    stats: dict = {}
    fantasy_points: float = 0.0


class RosterPlayer(BaseModel):
    player_id: int
    player_name: str
    team: Optional[str] = None
    positions: Optional[str] = None
    roster_slot: str
    added_date: Optional[str] = None
    is_active: bool = True


class RosterAddRequest(BaseModel):
    player_id: int
    player_name: str
    team: Optional[str] = None
    positions: Optional[str] = None
    roster_slot: str = "BN"
    league_team_id: int = 1


class RosterDropRequest(BaseModel):
    player_id: int
    league_team_id: int = 1


class RosterMoveRequest(BaseModel):
    player_id: int
    league_team_id: int = 1
    new_slot: str


class BulkRosterAddRequest(BaseModel):
    league_team_id: int = 1
    players: list[dict]  # [{player_id, player_name, team, positions, roster_slot}]


class LeagueTeamUpdateRequest(BaseModel):
    team_name: str


class LineupOptimizeRequest(BaseModel):
    window: str = "14d"
    week_start: str
    week_end: str


class MatchupProjectRequest(BaseModel):
    opponent_roster: list[int]  # player IDs
    window: str = "14d"
    week_start: str
    week_end: str


class TeamRunSupport(BaseModel):
    team_id: int
    team_name: str
    team_abbrev: str
    games_played: int = 0
    runs_scored: int = 0
    runs_allowed: int = 0
    run_differential: int = 0
    runs_per_game: float = 0.0
    runs_allowed_per_game: float = 0.0
    run_support_rank: int = 0
    run_diff_rank: int = 0
    tier: str = "B"  # S, A, B, C, D
    win_pct: float = 0.0
    last_updated: Optional[str] = None


class DropCandidate(BaseModel):
    player: PlayerStats
    replacement: Optional[PlayerStats] = None
    upgrade_potential: float = 0.0
    recommendation: str = "hold"  # "drop", "consider", "hold"
    reason: Optional[str] = None


class LineupSlot(BaseModel):
    slot: str
    player: Optional[PlayerStats] = None
    projected_pts: float = 0.0
    games_this_week: int = 0


class OptimizedLineup(BaseModel):
    optimal_lineup: dict[str, LineupSlot] = {}
    bench: list[PlayerStats] = []
    total_projected_pts: float = 0.0
    notes: list[str] = []


class MatchupProjection(BaseModel):
    my_projected_pts: float = 0.0
    opponent_projected_pts: float = 0.0
    win_probability: float = 0.0
    position_breakdown: dict = {}
