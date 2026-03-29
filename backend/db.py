"""SQLite database setup and queries."""

import asyncio
import aiosqlite
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "fantasy_baseball.db"))

# Shared connection + lock to prevent "database is locked" errors
_db_lock = asyncio.Lock()
_shared_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _shared_db
    if _shared_db is None:
        _shared_db = await aiosqlite.connect(DB_PATH, timeout=60)
        _shared_db.row_factory = aiosqlite.Row
        await _shared_db.execute("PRAGMA journal_mode=WAL")
        await _shared_db.execute("PRAGMA busy_timeout=60000")
    return _shared_db


async def close_db():
    global _shared_db
    if _shared_db:
        await _shared_db.close()
        _shared_db = None


async def init_db():
    """Create all tables on first run."""
    db = await get_db()
    await db.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                team TEXT,
                team_id INTEGER,
                positions TEXT,
                primary_position TEXT,
                is_pitcher INTEGER DEFAULT 0,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS player_season_stats (
                player_id INTEGER PRIMARY KEY,
                season INTEGER NOT NULL,
                games_played INTEGER DEFAULT 0,
                -- Batter stats
                runs INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                doubles INTEGER DEFAULT 0,
                triples INTEGER DEFAULT 0,
                home_runs INTEGER DEFAULT 0,
                rbi INTEGER DEFAULT 0,
                sac_hits INTEGER DEFAULT 0,
                stolen_bases INTEGER DEFAULT 0,
                caught_stealing INTEGER DEFAULT 0,
                walks INTEGER DEFAULT 0,
                hit_by_pitch INTEGER DEFAULT 0,
                strikeouts INTEGER DEFAULT 0,
                gidp INTEGER DEFAULT 0,
                -- Pitcher stats
                appearances INTEGER DEFAULT 0,
                innings_pitched REAL DEFAULT 0.0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                complete_games INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                hits_allowed INTEGER DEFAULT 0,
                earned_runs INTEGER DEFAULT 0,
                home_runs_allowed INTEGER DEFAULT 0,
                walks_allowed INTEGER DEFAULT 0,
                hit_batters INTEGER DEFAULT 0,
                pitcher_strikeouts INTEGER DEFAULT 0,
                pitcher_gidp INTEGER DEFAULT 0,
                holds INTEGER DEFAULT 0,
                blown_saves INTEGER DEFAULT 0,
                games_started INTEGER DEFAULT 0,
                era REAL DEFAULT 0.0,
                fantasy_points REAL DEFAULT 0.0,
                last_updated TEXT,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );

            CREATE TABLE IF NOT EXISTS player_game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                game_date TEXT NOT NULL,
                game_id INTEGER,
                opponent TEXT,
                is_pitcher INTEGER DEFAULT 0,
                -- Batter game stats
                runs INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                doubles INTEGER DEFAULT 0,
                triples INTEGER DEFAULT 0,
                home_runs INTEGER DEFAULT 0,
                rbi INTEGER DEFAULT 0,
                sac_hits INTEGER DEFAULT 0,
                stolen_bases INTEGER DEFAULT 0,
                caught_stealing INTEGER DEFAULT 0,
                walks INTEGER DEFAULT 0,
                hit_by_pitch INTEGER DEFAULT 0,
                strikeouts INTEGER DEFAULT 0,
                gidp INTEGER DEFAULT 0,
                -- Pitcher game stats
                innings_pitched REAL DEFAULT 0.0,
                pitcher_wins INTEGER DEFAULT 0,
                pitcher_losses INTEGER DEFAULT 0,
                complete_games INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                hits_allowed INTEGER DEFAULT 0,
                earned_runs INTEGER DEFAULT 0,
                home_runs_allowed INTEGER DEFAULT 0,
                walks_allowed INTEGER DEFAULT 0,
                hit_batters INTEGER DEFAULT 0,
                pitcher_strikeouts INTEGER DEFAULT 0,
                pitcher_gidp INTEGER DEFAULT 0,
                holds INTEGER DEFAULT 0,
                blown_saves INTEGER DEFAULT 0,
                fantasy_points REAL DEFAULT 0.0,
                last_updated TEXT,
                UNIQUE(player_id, game_date, game_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );

            CREATE TABLE IF NOT EXISTS team_run_support (
                team_id INTEGER PRIMARY KEY,
                team_name TEXT NOT NULL,
                team_abbrev TEXT NOT NULL,
                games_played INTEGER DEFAULT 0,
                runs_scored INTEGER DEFAULT 0,
                runs_allowed INTEGER DEFAULT 0,
                run_differential INTEGER DEFAULT 0,
                runs_per_game REAL DEFAULT 0.0,
                runs_allowed_per_game REAL DEFAULT 0.0,
                run_support_rank INTEGER DEFAULT 0,
                run_diff_rank INTEGER DEFAULT 0,
                win_pct REAL DEFAULT 0.0,
                tier TEXT DEFAULT 'B',
                last_updated TEXT
            );

            -- League teams (10 teams in the fantasy league)
            CREATE TABLE IF NOT EXISTS league_teams (
                team_id INTEGER PRIMARY KEY,
                team_name TEXT NOT NULL,
                is_mine INTEGER DEFAULT 0
            );

            -- League rosters (replaces old my_roster table)
            CREATE TABLE IF NOT EXISTS league_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT,
                positions TEXT,
                roster_slot TEXT DEFAULT 'BN',
                added_date TEXT,
                is_active INTEGER DEFAULT 1,
                UNIQUE(league_team_id, player_id),
                FOREIGN KEY (league_team_id) REFERENCES league_teams(team_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );

            CREATE TABLE IF NOT EXISTS weekly_acquisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_team_id INTEGER NOT NULL DEFAULT 1,
                player_id INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                action TEXT NOT NULL,
                action_date TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_game_logs_player_date
                ON player_game_logs(player_id, game_date);

            CREATE INDEX IF NOT EXISTS idx_game_logs_date
                ON player_game_logs(game_date);

            CREATE INDEX IF NOT EXISTS idx_players_team
                ON players(team_id);

            CREATE INDEX IF NOT EXISTS idx_league_rosters_team
                ON league_rosters(league_team_id);

            CREATE INDEX IF NOT EXISTS idx_league_rosters_player
                ON league_rosters(player_id);

            -- Matchup schedule (who plays who each week)
            CREATE TABLE IF NOT EXISTS matchup_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                week_label TEXT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                team_a_id INTEGER NOT NULL,
                team_b_id INTEGER NOT NULL,
                UNIQUE(week_number, team_a_id),
                FOREIGN KEY (team_a_id) REFERENCES league_teams(team_id),
                FOREIGN KEY (team_b_id) REFERENCES league_teams(team_id)
            );
    """)
    await db.commit()

    # Seed league teams if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM league_teams")
    row = await cursor.fetchone()
    if row["cnt"] == 0:
        from config import DEFAULT_LEAGUE_TEAMS
        for t in DEFAULT_LEAGUE_TEAMS:
            await db.execute(
                "INSERT INTO league_teams (team_id, team_name, is_mine) VALUES (?, ?, ?)",
                (t["team_id"], t["name"], int(t["is_mine"]))
            )
        await db.commit()

    # Migrate old my_roster data if it exists
    try:
        cursor = await db.execute("SELECT * FROM my_roster WHERE is_active = 1")
        old_roster = await cursor.fetchall()
        if old_roster:
            for row in old_roster:
                await db.execute("""
                    INSERT OR IGNORE INTO league_rosters
                    (league_team_id, player_id, player_name, team, positions, roster_slot, added_date, is_active)
                    VALUES (1, ?, ?, ?, ?, ?, ?, 1)
                """, (row["player_id"], row["player_name"], row["team"],
                      row["positions"], row["roster_slot"], row["added_date"]))
            await db.commit()
    except Exception:
        pass  # my_roster table may not exist


# --- Reference date (for window calculations) ---

async def get_reference_date(db) -> str:
    """Get the most recent game_date from game logs (handles data from past seasons)."""
    cursor = await db.execute("SELECT MAX(game_date) as max_date FROM player_game_logs")
    row = await cursor.fetchone()
    if row and row["max_date"]:
        return row["max_date"]
    return datetime.utcnow().strftime("%Y-%m-%d")


# --- Player queries ---

async def upsert_player(db, player_id, name, team, team_id, positions, primary_pos, is_pitcher):
    await db.execute("""
        INSERT INTO players (player_id, player_name, team, team_id, positions, primary_position, is_pitcher, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            player_name=excluded.player_name, team=excluded.team, team_id=excluded.team_id,
            positions=excluded.positions, primary_position=excluded.primary_position,
            is_pitcher=excluded.is_pitcher, last_updated=excluded.last_updated
    """, (player_id, name, team, team_id, positions, primary_pos, int(is_pitcher), datetime.utcnow().isoformat()))


async def upsert_season_stats(db, player_id, season, stats: dict):
    cols = ", ".join(stats.keys())
    placeholders = ", ".join(["?"] * len(stats))
    update_clause = ", ".join([f"{k}=excluded.{k}" for k in stats.keys()])
    await db.execute(f"""
        INSERT INTO player_season_stats (player_id, season, {cols}, last_updated)
        VALUES (?, ?, {placeholders}, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            season=excluded.season, {update_clause}, last_updated=excluded.last_updated
    """, (player_id, season, *stats.values(), datetime.utcnow().isoformat()))


async def upsert_game_log(db, player_id, game_date, game_id, opponent, is_pitcher, stats: dict, fantasy_pts):
    cols = list(stats.keys())
    col_str = ", ".join(cols)
    placeholders = ", ".join(["?"] * len(cols))
    update_clause = ", ".join([f"{k}=excluded.{k}" for k in cols])
    await db.execute(f"""
        INSERT INTO player_game_logs (player_id, game_date, game_id, opponent, is_pitcher, {col_str}, fantasy_points, last_updated)
        VALUES (?, ?, ?, ?, ?, {placeholders}, ?, ?)
        ON CONFLICT(player_id, game_date, game_id) DO UPDATE SET
            opponent=excluded.opponent, {update_clause}, fantasy_points=excluded.fantasy_points, last_updated=excluded.last_updated
    """, (player_id, game_date, game_id, opponent, int(is_pitcher), *stats.values(), fantasy_pts, datetime.utcnow().isoformat()))


async def get_all_players(db, is_pitcher=None):
    query = "SELECT * FROM players"
    params = []
    if is_pitcher is not None:
        query += " WHERE is_pitcher = ?"
        params.append(int(is_pitcher))
    cursor = await db.execute(query, params)
    return await cursor.fetchall()


async def get_player_season_stats(db, player_id):
    cursor = await db.execute("SELECT * FROM player_season_stats WHERE player_id = ?", (player_id,))
    return await cursor.fetchone()


async def get_player_game_logs(db, player_id, start_date=None, end_date=None):
    query = "SELECT * FROM player_game_logs WHERE player_id = ?"
    params = [player_id]
    if start_date:
        query += " AND game_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND game_date <= ?"
        params.append(end_date)
    query += " ORDER BY game_date DESC"
    cursor = await db.execute(query, params)
    return await cursor.fetchall()


# --- League team queries ---

async def get_league_teams(db):
    cursor = await db.execute("SELECT * FROM league_teams ORDER BY team_id")
    return await cursor.fetchall()


async def update_league_team(db, team_id, team_name):
    await db.execute("UPDATE league_teams SET team_name = ? WHERE team_id = ?", (team_name, team_id))


# --- League roster queries ---

async def get_all_rostered_player_ids(db):
    """Get ALL player IDs rostered across all 10 league teams."""
    cursor = await db.execute("SELECT player_id FROM league_rosters WHERE is_active = 1")
    rows = await cursor.fetchall()
    return [row["player_id"] for row in rows]


async def get_roster_player_ids(db, league_team_id=1):
    """Get player IDs for a specific league team."""
    cursor = await db.execute(
        "SELECT player_id FROM league_rosters WHERE league_team_id = ? AND is_active = 1",
        (league_team_id,)
    )
    rows = await cursor.fetchall()
    return [row["player_id"] for row in rows]


async def get_roster(db, league_team_id=1):
    cursor = await db.execute("""
        SELECT r.*, p.primary_position, p.is_pitcher, p.team_id
        FROM league_rosters r
        LEFT JOIN players p ON r.player_id = p.player_id
        WHERE r.league_team_id = ? AND r.is_active = 1
        ORDER BY
            CASE r.roster_slot
                WHEN 'C' THEN 1 WHEN '1B' THEN 2 WHEN '2B' THEN 3
                WHEN '3B' THEN 4 WHEN 'SS' THEN 5 WHEN 'OF' THEN 6
                WHEN 'Util' THEN 7 WHEN 'SP' THEN 8 WHEN 'RP' THEN 9
                WHEN 'P' THEN 10 WHEN 'BN' THEN 11 WHEN 'IL' THEN 12
                ELSE 13
            END, r.player_name
    """, (league_team_id,))
    return await cursor.fetchall()


async def add_to_roster(db, league_team_id, player_id, player_name, team, positions, roster_slot):
    await db.execute("""
        INSERT INTO league_rosters (league_team_id, player_id, player_name, team, positions, roster_slot, added_date, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(league_team_id, player_id) DO UPDATE SET
            roster_slot=excluded.roster_slot, is_active=1, added_date=excluded.added_date
    """, (league_team_id, player_id, player_name, team, positions, roster_slot, datetime.utcnow().isoformat()))


async def drop_from_roster(db, league_team_id, player_id):
    await db.execute(
        "UPDATE league_rosters SET is_active = 0 WHERE league_team_id = ? AND player_id = ?",
        (league_team_id, player_id)
    )


async def move_roster_slot(db, league_team_id, player_id, new_slot):
    """Move a player to a different roster slot."""
    await db.execute(
        "UPDATE league_rosters SET roster_slot = ? WHERE league_team_id = ? AND player_id = ? AND is_active = 1",
        (new_slot, league_team_id, player_id)
    )


async def get_roster_slot_counts(db, league_team_id):
    """Get count of players in each slot for a team."""
    cursor = await db.execute("""
        SELECT roster_slot, COUNT(*) as cnt
        FROM league_rosters
        WHERE league_team_id = ? AND is_active = 1
        GROUP BY roster_slot
    """, (league_team_id,))
    rows = await cursor.fetchall()
    return {row["roster_slot"]: row["cnt"] for row in rows}


# --- Team run support queries ---

async def upsert_team_run_support(db, team_id, team_name, team_abbrev, data: dict):
    await db.execute("""
        INSERT INTO team_run_support (team_id, team_name, team_abbrev,
            games_played, runs_scored, runs_allowed, run_differential,
            runs_per_game, runs_allowed_per_game, run_support_rank, run_diff_rank,
            win_pct, tier, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(team_id) DO UPDATE SET
            team_name=excluded.team_name, team_abbrev=excluded.team_abbrev,
            games_played=excluded.games_played, runs_scored=excluded.runs_scored,
            runs_allowed=excluded.runs_allowed, run_differential=excluded.run_differential,
            runs_per_game=excluded.runs_per_game, runs_allowed_per_game=excluded.runs_allowed_per_game,
            run_support_rank=excluded.run_support_rank, run_diff_rank=excluded.run_diff_rank,
            win_pct=excluded.win_pct, tier=excluded.tier, last_updated=excluded.last_updated
    """, (
        team_id, team_name, team_abbrev,
        data.get("games_played", 0), data.get("runs_scored", 0),
        data.get("runs_allowed", 0), data.get("run_differential", 0),
        data.get("runs_per_game", 0.0), data.get("runs_allowed_per_game", 0.0),
        data.get("run_support_rank", 0), data.get("run_diff_rank", 0),
        data.get("win_pct", 0.0), data.get("tier", "B"),
        datetime.utcnow().isoformat()
    ))


async def get_all_team_run_support(db):
    cursor = await db.execute("SELECT * FROM team_run_support ORDER BY run_support_rank ASC")
    return await cursor.fetchall()


async def get_team_run_support(db, team_id):
    cursor = await db.execute("SELECT * FROM team_run_support WHERE team_id = ?", (team_id,))
    return await cursor.fetchone()


# --- Matchup schedule queries ---

async def get_matchup_schedule(db):
    """Get the full season matchup schedule."""
    cursor = await db.execute("""
        SELECT * FROM matchup_schedule ORDER BY week_number, team_a_id
    """)
    return await cursor.fetchall()


async def get_week_matchup(db, week_number, team_id):
    """Get a specific team's matchup for a given week."""
    cursor = await db.execute("""
        SELECT * FROM matchup_schedule
        WHERE week_number = ? AND (team_a_id = ? OR team_b_id = ?)
    """, (week_number, team_id, team_id))
    return await cursor.fetchone()


async def upsert_matchup(db, week_number, week_label, week_start, week_end, team_a_id, team_b_id):
    """Set a matchup for a given week. Replaces any existing matchup for team_a in that week."""
    await db.execute("""
        INSERT INTO matchup_schedule (week_number, week_label, week_start, week_end, team_a_id, team_b_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(week_number, team_a_id) DO UPDATE SET
            week_label=excluded.week_label, week_start=excluded.week_start,
            week_end=excluded.week_end, team_b_id=excluded.team_b_id
    """, (week_number, week_label, week_start, week_end, team_a_id, team_b_id))


async def set_full_schedule(db, schedule):
    """Replace the entire matchup schedule."""
    await db.execute("DELETE FROM matchup_schedule")
    for m in schedule:
        await db.execute("""
            INSERT INTO matchup_schedule (week_number, week_label, week_start, week_end, team_a_id, team_b_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (m["week_number"], m.get("week_label", ""), m["week_start"], m["week_end"], m["team_a_id"], m["team_b_id"]))


async def get_last_refresh_time(db):
    cursor = await db.execute("SELECT MAX(last_updated) as last_updated FROM players")
    row = await cursor.fetchone()
    return row["last_updated"] if row else None
