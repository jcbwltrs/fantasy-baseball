"""Fantasy scoring engine — applies exact point values from league settings."""

import math
from config import BATTER_SCORING, PITCHER_SCORING


def convert_ip(ip_raw: float) -> float:
    """Convert baseball IP notation to actual innings.

    MLB API returns IP as e.g. 6.2 meaning 6⅔ innings.
    .1 = 1/3, .2 = 2/3
    """
    whole = math.floor(ip_raw)
    fraction = round(ip_raw - whole, 1)
    # fraction is .0, .1, or .2 in baseball notation
    return whole + (fraction * 10 / 3)


def calc_batter_points(stats: dict) -> float:
    """Calculate fantasy points for a batter from a stat line.

    Args:
        stats: dict with keys matching MLB API stat names.
              Must include 'hits' (H), 'doubles', 'triples', 'homeRuns'
              so we can derive singles.
    """
    # Derive singles: 1B = H - 2B - 3B - HR
    hits = _int(stats, "hits")
    doubles = _int(stats, "doubles")
    triples = _int(stats, "triples")
    home_runs = _int(stats, "homeRuns")
    singles = hits - doubles - triples - home_runs

    pts = 0.0
    pts += singles * BATTER_SCORING["1B"]
    pts += doubles * BATTER_SCORING["2B"]
    pts += triples * BATTER_SCORING["3B"]
    pts += home_runs * BATTER_SCORING["HR"]
    pts += _int(stats, "runs") * BATTER_SCORING["R"]
    pts += _int(stats, "rbi") * BATTER_SCORING["RBI"]
    pts += _int(stats, "sacBunts") * BATTER_SCORING["SH"]
    pts += _int(stats, "stolenBases") * BATTER_SCORING["SB"]
    pts += _int(stats, "caughtStealing") * BATTER_SCORING["CS"]
    pts += _int(stats, "baseOnBalls") * BATTER_SCORING["BB"]
    pts += _int(stats, "hitByPitch") * BATTER_SCORING["HBP"]
    pts += _int(stats, "strikeOuts") * BATTER_SCORING["K"]
    pts += _int(stats, "groundIntoDoublePlay") * BATTER_SCORING["GIDP"]

    # CYC and SLAM are game-level checks — handled separately in game log processing
    return round(pts, 2)


def calc_pitcher_points(stats: dict) -> float:
    """Calculate fantasy points for a pitcher from a stat line."""
    ip_raw = _float(stats, "inningsPitched")
    ip_actual = convert_ip(ip_raw)

    pts = 0.0
    # Appearances: use gamesPlayed if available, else 1 for a game log entry
    appearances = _int(stats, "gamesPlayed") or _int(stats, "gamesPitched")
    if appearances == 0 and ip_raw > 0:
        appearances = 1
    pts += appearances * PITCHER_SCORING["APP"]
    pts += ip_actual * PITCHER_SCORING["IP"]
    pts += _int(stats, "wins") * PITCHER_SCORING["W"]
    pts += _int(stats, "losses") * PITCHER_SCORING["L"]
    pts += _int(stats, "completeGames") * PITCHER_SCORING["CG"]
    pts += _int(stats, "saves") * PITCHER_SCORING["SV"]
    pts += _int(stats, "hits") * PITCHER_SCORING["H"]  # hits allowed
    pts += _int(stats, "earnedRuns") * PITCHER_SCORING["ER"]
    pts += _int(stats, "homeRuns") * PITCHER_SCORING["HR"]  # HR allowed
    pts += _int(stats, "baseOnBalls") * PITCHER_SCORING["BB"]
    pts += _int(stats, "hitBatsmen") * PITCHER_SCORING["HBP"]
    pts += _int(stats, "strikeOuts") * PITCHER_SCORING["K"]
    pts += _int(stats, "groundIntoDoublePlay") * PITCHER_SCORING["GIDP"]
    pts += _int(stats, "holds") * PITCHER_SCORING["HLD"]
    pts += _int(stats, "blownSaves") * PITCHER_SCORING["BSV"]

    return round(pts, 2)


def calc_game_batter_points(game_stats: dict) -> float:
    """Calculate fantasy points for a single game batter line.
    Also checks for cycle and grand slam bonuses."""
    base_pts = calc_batter_points(game_stats)

    # Check for hitting for the cycle
    hits = _int(game_stats, "hits")
    doubles = _int(game_stats, "doubles")
    triples = _int(game_stats, "triples")
    home_runs = _int(game_stats, "homeRuns")
    singles = hits - doubles - triples - home_runs

    if singles >= 1 and doubles >= 1 and triples >= 1 and home_runs >= 1:
        base_pts += BATTER_SCORING["CYC"]

    # Grand Slam approximation: HR with 4+ RBI in a game is likely a grand slam
    # This is an approximation — the spec acknowledges this limitation
    rbi = _int(game_stats, "rbi")
    if home_runs >= 1 and rbi >= 4:
        # Estimate: if RBI >= HR*4, likely at least one grand slam
        possible_slams = min(home_runs, rbi // 4)
        if possible_slams > 0:
            base_pts += possible_slams * BATTER_SCORING["SLAM"]

    return round(base_pts, 2)


def calc_game_pitcher_points(game_stats: dict) -> float:
    """Calculate fantasy points for a single game pitcher line."""
    return calc_pitcher_points(game_stats)


def _int(d: dict, key: str) -> int:
    """Safely get an int from a dict."""
    val = d.get(key, 0)
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _float(d: dict, key: str) -> float:
    """Safely get a float from a dict."""
    val = d.get(key, 0.0)
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0
