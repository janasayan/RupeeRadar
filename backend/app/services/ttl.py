"""Session TTL cleanup — purge sessions whose expires_at has passed."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.db import UploadSession

logger = logging.getLogger(__name__)


def purge_expired_sessions(db: Session) -> int:
    now = datetime.now(timezone.utc)
    expired = (
        db.query(UploadSession)
        .filter(
            UploadSession.expires_at.is_not(None),
            UploadSession.expires_at < now,
        )
        .all()
    )
    for s in expired:
        db.delete(s)
    if expired:
        db.commit()
        logger.info("Purged %d expired session(s)", len(expired))
    return len(expired)
