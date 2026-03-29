"""Team run support & pitcher win probability model."""

import logging
from datetime import datetime, timedelta
from config import (
    BASE_SP_WIN_RATE, RP_WIN_MULTIPLIER, PITCHER_QUALITY_CAP,
    RUN_SUPPORT_RPG_WEIGHT, RUN_SUPPORT_DIFF_WEIGHT,
    PRIOR_SEASON_RUN_SUPPORT, MIN_TEAM_GAMES_FULL_TRUST, EARLY_SEASON_BLEND_WEEKS,
)

logger = logging.getLogger(__name__)


def calculate_run_support_tier(runs_per_game: float, run_differential: int,
                                rpg_rank: int, diff_rank: int,
                                total_teams: int = 30) -> str:
    """Classify team into run support tier S/A/B/C/D.

    Tier S: Top 5 in R/G AND positive run diff
    Tier A: Top 10 in R/G OR top 10 run diff
    Tier B: Middle 10
    Tier C: Bottom 10 in R/G
    Tier D: Bottom 5 in R/G AND negative run diff
    """
    if rpg_rank <= 5 and run_differential > 0:
        return "S"
    if rpg_rank <= 10 or diff_rank <= 10:
        return "A"
    if rpg_rank > total_teams - 5 and run_differential < 0:
        return "D"
    if rpg_rank > total_teams - 10:
        return "C"
    return "B"


def blend_run_support(current_rpg: float, team_abbrev: str,
                       games_played: int, season_start_date: str = None) -> float:
    """Blend current-year and prior-year run support for early season.

    Early season (< MIN_TEAM_GAMES_FULL_TRUST games):
        70% prior-season + 30% current-season, shifting gradually
    After enough games: 100% current-season.
    """
    if games_played >= MIN_TEAM_GAMES_FULL_TRUST:
        return current_rpg

    prior_rpg = PRIOR_SEASON_RUN_SUPPORT.get(team_abbrev, 4.3)  # fallback to ~league avg

    if games_played == 0:
        return prior_rpg

    # Linear blend: at 0 games → 100% prior, at MIN_TEAM_GAMES → 100% current
    current_weight = games_played / MIN_TEAM_GAMES_FULL_TRUST
    blended = (current_weight * current_rpg) + ((1 - current_weight) * prior_rpg)
    return round(blended, 3)


def calculate_wpps(pitcher_era: float, team_rpg: float, league_avg_rpg: float,
                    league_avg_era: float, is_starter: bool = True) -> float:
    """Calculate Win Probability Per Start (WPPS).

    WPPS = base_win_rate × run_support_multiplier × pitcher_quality_factor
    """
    if league_avg_rpg == 0:
        league_avg_rpg = 4.3  # fallback

    # Run support multiplier
    run_support_multiplier = team_rpg / league_avg_rpg

    # Pitcher quality factor: league_avg_ERA / pitcher_ERA (capped)
    if pitcher_era <= 0:
        pitcher_quality_factor = PITCHER_QUALITY_CAP
    else:
        pitcher_quality_factor = min(league_avg_era / pitcher_era, PITCHER_QUALITY_CAP)

    base_rate = BASE_SP_WIN_RATE
    if not is_starter:
        # Relief pitchers get reduced weight
        run_support_multiplier = 1 + (run_support_multiplier - 1) * RP_WIN_MULTIPLIER
        base_rate = 0.05  # RP win rate is much lower

    wpps = base_rate * run_support_multiplier * pitcher_quality_factor
    return round(wpps, 4)


def calculate_composite_run_support_score(rpg: float, run_diff_per_game: float,
                                           league_avg_rpg: float) -> float:
    """Composite score using 70% RPG + 30% run differential.

    Both normalized relative to league average.
    """
    if league_avg_rpg == 0:
        league_avg_rpg = 4.3

    rpg_factor = rpg / league_avg_rpg
    # Normalize run diff: +1 run diff/game ~= +25% score
    diff_factor = 1.0 + (run_diff_per_game / league_avg_rpg)

    composite = (RUN_SUPPORT_RPG_WEIGHT * rpg_factor) + (RUN_SUPPORT_DIFF_WEIGHT * diff_factor)
    return round(composite, 4)


def project_pitcher_win_points(wpps: float, num_starts: int) -> dict:
    """Project Win/Loss fantasy points for a pitcher over N starts.

    Returns dict with projected win pts, loss pts, and net W/L pts.
    """
    # Loss probability ≈ roughly correlated inversely
    # Simple model: loss rate ≈ base_loss_rate × inverse of quality
    # For simplicity: loss_prob ≈ (1 - wpps) * 0.25 (not every non-win is a loss)
    loss_prob_per_start = min(0.30, max(0.05, 0.25 - wpps * 0.3))

    win_pts = wpps * num_starts * 10  # 10 pts per W
    loss_pts = loss_prob_per_start * num_starts * -5  # -5 pts per L
    net = win_pts + loss_pts

    return {
        "wpps": wpps,
        "projected_win_pts": round(win_pts, 2),
        "projected_loss_pts": round(loss_pts, 2),
        "net_wl_pts": round(net, 2),
        "loss_prob_per_start": round(loss_prob_per_start, 4),
    }
