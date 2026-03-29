"""FastAPI app entry point."""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import init_db, get_db, get_last_refresh_time, close_db
from tasks.refresh import refresh_all_data
from routers import players, roster, lineup, matchup
from config import REFRESH_INTERVAL_HOURS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Path to built frontend (relative to backend dir)
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Schedule periodic refresh
    scheduler.add_job(
        refresh_all_data,
        "interval",
        hours=REFRESH_INTERVAL_HOURS,
        id="refresh_stats",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — refreshing every {REFRESH_INTERVAL_HOURS} hours")

    yield

    # Shutdown
    scheduler.shutdown()
    await close_db()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Fantasy Baseball Optimizer",
    description="10-team H2H Points league optimizer with MLB Stats API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow dev server + any production origin
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Add production URL from env if set
prod_url = os.environ.get("PRODUCTION_URL")
if prod_url:
    allowed_origins.append(prod_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(players.router)
app.include_router(roster.router)
app.include_router(lineup.router)
app.include_router(matchup.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/status")
async def status():
    """Get data freshness status."""
    db = await get_db()
    try:
        last_refresh = await get_last_refresh_time(db)
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM players")
        player_count = (await cursor.fetchone())["cnt"]
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM team_run_support")
        team_count = (await cursor.fetchone())["cnt"]
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM league_rosters WHERE is_active = 1")
        roster_count = (await cursor.fetchone())["cnt"]

        return {
            "last_refresh": last_refresh,
            "player_count": player_count,
            "team_run_support_count": team_count,
            "roster_count": roster_count,
        }
    finally:
        pass  # shared connection


@app.post("/api/refresh")
async def manual_refresh():
    """Trigger a manual data refresh."""
    try:
        await refresh_all_data()
        return {"success": True, "message": "Data refresh complete"}
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        return {"success": False, "error": str(e)}


# --- Serve built React frontend (production) ---
if STATIC_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    # Serve any other static files at root level (favicon, etc.)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React app — all non-API routes return index.html for client-side routing."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
else:
    logger.info("No frontend build found — API-only mode (run 'npm run build' in frontend/)")
