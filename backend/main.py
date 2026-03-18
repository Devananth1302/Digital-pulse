import sys
import logging
from pathlib import Path

# Add project root to path so config/ and services/ are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configure logging BEFORE any other imports so all modules use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.posts import router as posts_router
from backend.api.narratives import router as narratives_router
from backend.api.emerging import router as emerging_router
from backend.api.pulse import router as pulse_router
from backend.api.forecast import router as forecast_router
from backend.api.upload import router as upload_router
from backend.services.scheduler import start_scheduler, stop_scheduler, run_full_cycle
from backend.services.ingestion_service import run_ingestion_pipeline
from config.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Digital Pulse API",
    description="Contextual Cultural Intelligence Engine",
    version="2.0.0",
)

# Allow frontend on any localhost port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(posts_router,      prefix="/posts",       tags=["Posts"])
app.include_router(narratives_router, prefix="/narratives",  tags=["Narratives"])
app.include_router(emerging_router,   prefix="/emerging",    tags=["Emerging Signals"])
app.include_router(pulse_router,      prefix="/pulse-score", tags=["Pulse Score"])
app.include_router(forecast_router,   prefix="/forecast",    tags=["Forecast"])
app.include_router(upload_router,     prefix="/upload-csv",  tags=["Upload"])


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("=== Digital Pulse API starting up ===")
    start_scheduler()
    logger.info("Running full pipeline immediately (no waiting for 15-min interval)...")
    # run_full_cycle = ingest + process + cluster + signals + forecast
    try:
        await run_full_cycle()
    except Exception as exc:
        logger.error("Initial pipeline run failed: %s", exc, exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    logger.info("Scheduler stopped.")


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "Digital Pulse API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "sources": ["google_news_rss", "newsapi", "csv_upload"],
    }


# ── Debug ─────────────────────────────────────────────────────────────────────

@app.get("/debug/ingestion", tags=["Debug"])
async def debug_ingestion():
    """Manually trigger the FULL pipeline (ingest + cluster + signals + forecast)."""
    logger.info("Manual full pipeline trigger via /debug/ingestion")
    try:
        await run_full_cycle()
        status_r = await debug_status()
        return {"status": "ok", "table_counts": status_r["table_counts"]}
    except Exception as exc:
        logger.error("Debug pipeline error: %s", exc, exc_info=True)
        return {"status": "error", "detail": str(exc)}


@app.get("/debug/status", tags=["Debug"])
async def debug_status():
    """Quick health check – counts rows in each table."""
    from backend.core.database import get_supabase
    db = get_supabase()
    counts = {}
    for tbl in ("posts", "narrative_clusters", "emerging_signals", "forecasts"):
        try:
            r = db.table(tbl).select("*", count="exact").limit(1).execute()
            counts[tbl] = r.count
        except Exception as exc:
            counts[tbl] = f"error: {exc}"
    return {"status": "ok", "table_counts": counts}
