from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.db import UploadSession


def create_session(db: Session, filename: str, file_type: str) -> UploadSession:
    now = datetime.now(timezone.utc)
    session = UploadSession(
        id=str(uuid.uuid4()),
        filename=filename,
        file_type=file_type,
        status="pending",
        uploaded_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_status(db: Session, session_id: str, status: str, **kwargs) -> None:
    db.query(UploadSession).filter(UploadSession.id == session_id).update(
        {"status": status, **kwargs}
    )
    db.commit()


def get_session(db: Session, session_id: str) -> Optional[UploadSession]:
    return db.query(UploadSession).filter(UploadSession.id == session_id).first()
