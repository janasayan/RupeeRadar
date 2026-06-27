from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, upload, sessions, transactions, recommendations, report
from app.config.settings import settings
from app.services.database import init_db, SessionLocal
from app.services.ttl import purge_expired_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        purge_expired_sessions(db)
    yield


app = FastAPI(
    title="RupeeRadar API",
    description="AI-powered personal finance assistant for bank statement analysis",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {"message": "RupeeRadar API", "docs": "/docs", "health": "/api/v1/health"}
