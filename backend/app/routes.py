"""HTTP routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import httpx

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.db import get_watch, list_watches
from app.legal import draft_legal_notice
from app.models.schemas import (
    FlaggedListing,
    HealthResponse,
    NewInfringementsResponse,
    ScanRequest,
    ScanResponse,
    WatchSummary,
)
from app.scanner import execute_scan
from app.serpapi_client import SerpApiError

router = APIRouter()
UTC = timezone.utc


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        serpapi_configured=bool(settings.serpapi_key),
        groq_configured=bool(settings.groq_api_key),
        rescan_interval_hours=settings.rescan_interval_hours,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )


@router.get("/api/credits")
def credits() -> dict:
    """Live SerpApi balance. The Account API is free and does not use up search credits."""
    settings = get_settings()
    if not settings.serpapi_key:
        raise HTTPException(status_code=503, detail="SERPAPI_KEY is not configured")
    try:
        resp = httpx.get(
            "https://serpapi.com/account.json",
            params={"api_key": settings.serpapi_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach SerpApi account API: {exc}")
    # Return only what the dashboard needs, never echo the API key back.
    return {
        "plan_name": data.get("plan_name"),
        "searches_per_month": data.get("searches_per_month"),
        "total_searches_left": data.get("total_searches_left"),
        "this_month_usage": data.get("this_month_usage"),
    }

@router.post("/api/scan", response_model=ScanResponse)
def create_scan(payload: ScanRequest) -> ScanResponse:
    settings = get_settings()
    if not settings.serpapi_key:
        raise HTTPException(
            status_code=503,
            detail="SERPAPI_KEY is not configured. Copy backend/.env.example to backend/.env.",
        )
    try:
        return execute_scan(
            payload.product_name.strip(),
            payload.official_price,
            str(payload.image_url),
            use_cache=True,
            rescan_interval_hours=payload.rescan_interval_hours,
            currency=payload.currency,
        )
    except SerpApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/watches", response_model=list[WatchSummary])
def watches() -> list[WatchSummary]:
    rows = list_watches()
    summaries: list[WatchSummary] = []
    for row in rows:
        new_count = 0
        if row.last_new_json:
            try:
                new_count = len(json.loads(row.last_new_json))
            except json.JSONDecodeError:
                new_count = 0
        summaries.append(
            WatchSummary(
                watch_id=row.id,
                product_name=row.product_name,
                official_price=row.official_price,
                image_url=row.image_url,
                interval_hours=row.interval_hours,
                last_run_at=row.last_run_at,
                last_risk_score=row.last_risk_score,
                last_new_count=new_count,
                created_at=row.created_at,
            )
        )
    return summaries


@router.get("/api/watches/{watch_id}/new-infringements", response_model=NewInfringementsResponse)
def watch_new_infringements(watch_id: str) -> NewInfringementsResponse:
    row = get_watch(watch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Watch not found")

    listings: list[FlaggedListing] = []
    if row.last_new_json:
        try:
            listings = [FlaggedListing.model_validate(item) for item in json.loads(row.last_new_json)]
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=f"Stored watch payload is invalid: {exc}") from exc

    return NewInfringementsResponse(
        watch_id=row.id,
        product_name=row.product_name,
        compared_at=row.last_run_at or datetime.now(UTC),
        previous_scan_at=row.previous_scan_at,
        new_infringements=listings,
        legal_notice_draft=draft_legal_notice(row.product_name, listings),
    )
