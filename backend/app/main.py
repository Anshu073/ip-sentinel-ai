"""
IP Brand Infringement Scanner API.

Run from the backend/ directory:

    python -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    copy .env.example .env   # then fill in SERPAPI_KEY (and optionally GROQ_API_KEY)
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.db import init_db
from app.jobs import shutdown_scheduler, start_scheduler
from app.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    start_scheduler()
    logger.info("Backend ready — POST /api/scan")
    try:
        yield
    finally:
        shutdown_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="IP Brand Infringement Scanner",
        version=__version__,
        description=(
            "FastAPI service that fans out to SerpApi (google_shopping, "
            "google_reverse_image, google), scores listings, caches results, "
            "and diffs new infringements on a scheduled re-scan."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)
    return application


app = create_app()
