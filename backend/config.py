"""League settings, scoring rules, and configuration."""

# --- League Settings ---
LEAGUE_TEAMS = 10
SCORING_TYPE = "Head-to-Head Points"
LINEUP_LOCK = "Monday"
MAX_ACQUISITIONS_PER_WEEK = 6
WAIVER_TIME_DAYS = 1
WAIVER_TYPE = "Continual rolling list"
TRADE_DEADLINE = "2026-08-20"
PLAYOFF_TEAMS = 6
PLAYOFF_WEEKS = [24, 25, 26]

# Default league team names (team_id 1 = "My Team", 2-10 = opponents)
DEFAULT_LEAGUE_TEAMS = [
    {"team_id": 1, "name": "My Team", "is_mine": True},
    {"team_id": 2, "name": "Team 2", "is_mine": False},
    {"team_id": 3, "name": "Team 3", "is_mine": False},
    {"team_id": 4, "name": "Team 4", "is_mine": False},
    {"team_id": 5, "name": "Team 5", "is_mine": False},
    {"team_id": 6, "name": "Team 6", "is_mine": False},
    {"team_id": 7, "name": "Team 7", "is_mine": False},
    {"team_id": 8, "name": "Team 8", "is_mine": False},
    {"team_id": 9, "name": "Team 9", "is_mine": False},
    {"team_id": 10, "name": "Team 10", "is_mine": False},
]

# --- Two-Way Player Splitting ---
# Players who bat AND pitch — split into virtual batter/pitcher entries
# Virtual IDs: base_id * 10 + 0 = batter, base_id * 10 + 1 = pitcher
TWO_WAY_PLAYERS = {
    660271: {
        "name": "Shohei Ohtani",
        "batter_id": 6602710,
        "pitcher_id": 6602711,
        "batter_name": "Shohei Ohtani (B)",
        "pitcher_name": "Shohei Ohtani (P)",
    },
}

ROSTER_POSITIONS = [
    "C", "1B", "2B", "3B", "SS",
    "OF", "OF", "OF",
    "Util",
    "SP", "RP", "P", "P", "P",
    "BN", "BN", "BN", "BN", "BN",
    "IL",
]

# --- Batter Scoring ---
BATTER_SCORING = {
    "R": 1,
    "1B": 1,
    "2B": 2,
    "3B": 3,
    "HR": 4,
    "RBI": 1,
    "SH": 0.25,
    "SB": 1,
    "CS": -0.5,
    "BB": 1,
    "HBP": 1,
    "K": -0.5,
    "GIDP": -1,
    "CYC": 2,
    "SLAM": 1,
}

# --- Pitcher Scoring ---
PITCHER_SCORING = {
    "APP": 0.5,
    "IP": 1.3,
    "W": 10,
    "L": -5,
    "CG": 2,
    "SV": 8,
    "H": -0.25,
    "ER": -1,
    "HR": -0.25,
    "BB": -0.25,
    "HBP": -0.25,
    "K": 1.4,
    "GIDP": 0.5,
    "HLD": 6,
    "BSV": -3,
}

# --- MLB Stats API ---
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
CURRENT_SEASON = 2026
SEASON_START_DATE = "2026-03-25"  # Wednesday, opening day
REQUEST_DELAY_MS = 100  # ms between bulk API requests
CACHE_TTL_HOURS = 1  # Don't re-fetch data less than 1 hour old
REFRESH_INTERVAL_HOURS = 6  # APScheduler refresh interval

# --- Run Support ---
# Base SP win rate per start (league average)
BASE_SP_WIN_RATE = 0.25
# RP win probability multiplier (reduced weight vs SP)
RP_WIN_MULTIPLIER = 0.5
# Cap on pitcher quality factor to prevent outlier distortion
PITCHER_QUALITY_CAP = 1.5
# Run support composite weights
RUN_SUPPORT_RPG_WEIGHT = 0.70
RUN_SUPPORT_DIFF_WEIGHT = 0.30

# --- Prior Season (2024) Run Support Fallback ---
# Used for early-season blending when current-year sample is small
PRIOR_SEASON_RUN_SUPPORT = {
    "LAD": 5.27, "ARI": 4.99, "MIL": 4.68, "NYY": 4.88, "CLE": 4.23,
    "PHI": 4.69, "SD": 4.63, "ATL": 4.54, "BAL": 4.52, "HOU": 4.51,
    "SEA": 3.93, "MIN": 4.66, "KC": 4.41, "DET": 3.98, "TEX": 4.17,
    "BOS": 4.73, "NYM": 4.36, "TB": 3.90, "SF": 4.12, "CIN": 4.64,
    "STL": 4.08, "CHC": 4.39, "TOR": 4.08, "PIT": 3.97, "LAA": 4.02,
    "WSH": 3.86, "COL": 4.26, "OAK": 3.52, "MIA": 3.60, "CWS": 3.17,
}
PRIOR_SEASON = 2024

# Early season blending: weeks until 100% current data
EARLY_SEASON_BLEND_WEEKS = 6
# Min team games before trusting current-year data fully
MIN_TEAM_GAMES_FULL_TRUST = 30
