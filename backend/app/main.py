from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    applications,
    assistant,
    cover_letters,
    health,
    jobs,
    profile,
    resume_versions,
)
from app.core.config import settings
from app.db.init_db import init_db


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Human-in-the-loop job search intelligence and application workflow API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(assistant.router)
app.include_router(profile.router)
app.include_router(resume_versions.router)
app.include_router(cover_letters.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }
