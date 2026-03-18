"""Debug API endpoints for manual pipeline triggering."""

import logging

from fastapi import APIRouter

from backend.services.ingestion_service import run_ingestion_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ingestion")
async def debug_ingestion():
    """Manually trigger the ingestion pipeline for debugging."""
    logger.info("Manual ingestion triggered via /debug/ingestion")
    try:
        stats = await run_ingestion_pipeline()
        return {"status": "pipeline executed", "stats": stats}
    except Exception as e:
        logger.error("Debug ingestion failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
