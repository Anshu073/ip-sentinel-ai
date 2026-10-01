"""WHOIS lookups with timeout + SQLite cache. Used for the domain-risk factor."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urlparse

import whois
from dateutil import parser as date_parser

from app.config import get_settings
from app.db import whois_cache_get, whois_cache_set

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="whois")


def extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    raw = url if "://" in url else f"https://{url}"
    try:
        host = urlparse(raw).hostname or ""
    except ValueError:
        return None
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _first_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, list):
        dates = [_first_datetime(item) for item in value]
        dates = [d for d in dates if d is not None]
        return min(dates) if dates else None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = date_parser.parse(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _lookup_uncached(domain: str) -> dict:
    record = whois.whois(domain)
    created = _first_datetime(getattr(record, "creation_date", None))
    registrar = getattr(record, "registrar", None)
    if isinstance(registrar, list):
        registrar = registrar[0] if registrar else None
    return {
        "domain": domain,
        "created_at": created.isoformat() if created else None,
        "registrar": registrar,
        "raw_ok": True,
    }


def lookup_domain(domain: str) -> dict:
    """Return {domain, created_at (iso|None), registrar, error?}."""
    cached = whois_cache_get(domain)
    if cached:
        return cached

    settings = get_settings()
    payload = {"domain": domain, "created_at": None, "registrar": None, "raw_ok": False}
    try:
        future = _executor.submit(_lookup_uncached, domain)
        payload = future.result(timeout=settings.whois_timeout_seconds)
    except FuturesTimeout:
        logger.warning("WHOIS timed out for %s", domain)
        payload["error"] = "timeout"
    except Exception as exc:  # python-whois raises a variety of errors
        logger.warning("WHOIS failed for %s: %s", domain, exc)
        payload["error"] = str(exc)

    whois_cache_set(domain, payload)
    return payload


def created_at_from_payload(payload: dict) -> Optional[datetime]:
    iso = payload.get("created_at")
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def format_age(created_at: Optional[datetime], now: Optional[datetime] = None) -> str:
    if created_at is None:
        return "unknown"
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = max(0, (now - created_at).days)
    if days < 30:
        return f"{days} days"
    if days < 365:
        return f"{days // 30} months ({days} days)"
    return f"{days / 365.25:.1f} years ({days} days)"


def lookup_many(domains: List[str]) -> dict:
    """Deduped parallel WHOIS for a list of registrable domains."""
    unique = []
    seen = set()
    for domain in domains:
        if domain and domain not in seen:
            seen.add(domain)
            unique.append(domain)

    results = {}
    # Thread pool already exists; submit all unique domains
    futures = {domain: _executor.submit(lookup_domain, domain) for domain in unique}
    for domain, future in futures.items():
        try:
            results[domain] = future.result(timeout=get_settings().whois_timeout_seconds + 2)
        except Exception as exc:
            results[domain] = {
                "domain": domain,
                "created_at": None,
                "registrar": None,
                "raw_ok": False,
                "error": str(exc),
            }
    return results
