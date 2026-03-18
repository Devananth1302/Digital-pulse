"""CSV upload endpoint for manual data ingestion."""

import csv
import hashlib
import io
import logging

from fastapi import APIRouter, UploadFile, File

from backend.services.ingestion_service import run_ingestion_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV containing title, content, timestamp, likes, shares, comments.

    Processes through the same ingestion pipeline as RSS/NewsAPI data.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        return {"error": "File must be a .csv file"}

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    raw_posts = []
    row_count = 0
    for row in reader:
        row_count += 1
        # Generate post_id if missing
        if "post_id" not in row or not row["post_id"]:
            raw_id = f"csv:{row.get('title', '')}:{row.get('timestamp', row_count)}"
            row["post_id"] = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        if "source" not in row or not row["source"]:
            row["source"] = "csv_upload"

        raw_posts.append(row)

    # Run through the unified ingestion pipeline
    stats = await run_ingestion_pipeline(raw_posts)

    return {
        "message": f"Uploaded {file.filename}",
        "rows_read": row_count,
        "posts_stored": stats["stored"],
        "normalized": stats["normalized"],
        "status": "processing_complete",
    }
