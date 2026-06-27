from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.schemas import UploadResponse
from app.pipeline.orchestrator import run
from app.services.database import get_db
from app.services import session as session_svc

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    # Validate file presence
    if not file.filename:
        raise HTTPException(status_code=422, detail="No file provided")

    # Validate extension
    name = file.filename.lower()
    if not (name.endswith(".csv") or name.endswith(".xlsx")):
        raise HTTPException(
            status_code=422,
            detail="Unsupported file type. Please upload a CSV file exported from your bank.",
        )

    # Read & size check
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )

    # Create session
    db_session = session_svc.create_session(db, file.filename, name.rsplit(".", 1)[-1])
    session_svc.update_status(db, db_session.id, "processing")

    # Run pipeline
    try:
        row_count, warnings, llm_count = run(db, db_session.id, file.filename, content)
    except Exception as exc:
        session_svc.update_status(db, db_session.id, "failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    if row_count == 0:
        s = session_svc.get_session(db, db_session.id)
        raise HTTPException(status_code=422, detail=s.error_message or "No transactions found")

    return UploadResponse(
        session_id=db_session.id,
        status="ready",
        row_count=row_count,
        warnings=warnings,
        llm_categorized=llm_count,
    )
