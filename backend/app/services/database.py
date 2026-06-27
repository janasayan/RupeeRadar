from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config.settings import settings
from app.models.db import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_existing()


def _migrate_existing() -> None:
    """Add columns introduced in Phase 2 / 2.5 to an existing database without dropping data."""
    with engine.connect() as conn:
        existing_txn = {row[1] for row in conn.execute(text("PRAGMA table_info(transactions)"))}
        new_txn_cols = {
            "category_source": "TEXT NOT NULL DEFAULT 'rule'",
            "recurring_group_id": "TEXT REFERENCES recurring_groups(id)",
            "needs_wants": "TEXT",
        }
        for col, definition in new_txn_cols.items():
            if col not in existing_txn:
                conn.execute(text(f"ALTER TABLE transactions ADD COLUMN {col} {definition}"))

        # savings_recommendations table is created by create_all above, but guard anyway
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "savings_recommendations" not in tables:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS savings_recommendations ("
                "id TEXT PRIMARY KEY, "
                "session_id TEXT UNIQUE REFERENCES upload_sessions(id), "
                "salary_monthly REAL, "
                "wants_budget_pct REAL NOT NULL DEFAULT 30.0, "
                "wants_budget REAL, "
                "wants_actual REAL NOT NULL DEFAULT 0.0, "
                "needs_actual REAL NOT NULL DEFAULT 0.0, "
                "is_over_budget INTEGER NOT NULL DEFAULT 0, "
                "recommendations TEXT NOT NULL DEFAULT '[]', "
                "summary TEXT NOT NULL DEFAULT '', "
                "generated_at TEXT NOT NULL"
                ")"
            ))
        conn.commit()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
