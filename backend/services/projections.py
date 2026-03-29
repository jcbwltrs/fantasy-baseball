"""Matchup projection engine."""

import math
from models import PlayerStats, MatchupProjection


def project_matchup(my_lineup: dict, opp_lineup: dict) -> MatchupProjection:
    """Project matchup result between two lineups.

    Each lineup is a dict of slot -> PlayerStats with projected_pts.
    """
    my_total = sum(p.fantasy_points for p in my_lineup.values() if p)
    opp_total = sum(p.fantasy_points for p in opp_lineup.values() if p)

    # Position breakdown
    breakdown = {}
    all_slots = set(list(my_lineup.keys()) + list(opp_lineup.keys()))
    for slot in all_slots:
        mine = my_lineup.get(slot)
        theirs = opp_lineup.get(slot)
        breakdown[slot] = {
            "mine": round(mine.fantasy_points, 1) if mine else 0,
            "theirs": round(theirs.fantasy_points, 1) if theirs else 0,
        }

    # Win probability using normal distribution approximation
    # Estimate variance: ~15-20% of projected points as standard deviation
    my_std = max(my_total * 0.18, 10)
    opp_std = max(opp_total * 0.18, 10)
    diff = my_total - opp_total
    combined_std = math.sqrt(my_std**2 + opp_std**2)

    if combined_std == 0:
        win_prob = 0.5
    else:
        # P(my_score > opp_score) using normal CDF approximation
        z = diff / combined_std
        win_prob = _normal_cdf(z)

    return MatchupProjection(
        my_projected_pts=round(my_total, 1),
        opponent_projected_pts=round(opp_total, 1),
        win_probability=round(win_prob, 3),
        position_breakdown=breakdown,
    )


def _normal_cdf(z: float) -> float:
    """Approximate the standard normal CDF."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))
