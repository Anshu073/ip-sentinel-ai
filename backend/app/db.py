"""SQLite persistence: 1-hour scan cache, WHOIS cache, watch jobs, listing history."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings

UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ScanCacheRow(Base):
    __tablename__ = "scan_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WhoisCacheRow(Base):
    __tablename__ = "whois_cache"

    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WatchRow(Base):
    __tablename__ = "watches"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(300), index=True)
    official_price: Mapped[float] = mapped_column(Float)
    image_url: Mapped[str] = mapped_column(String(2000))
    interval_hours: Mapped[int] = mapped_column(Integer)
    query_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_new_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ListingSightingRow(Base):
    """Every flagged listing ever observed for a watch — used for new-vs-previous diffs."""

    __tablename__ = "listing_sightings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watch_id: Mapped[str] = mapped_column(String(40), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    listing_json: Mapped[str] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scan_id: Mapped[str] = mapped_column(String(40))


_engine = None
SessionLocal = None


def _ensure_data_dir(url: str) -> None:
    if url.startswith("sqlite:///./"):
        Path("./data").mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    global _engine, SessionLocal
    settings = get_settings()
    _ensure_data_dir(settings.database_url)
    _engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
        future=True,
    )
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(_engine)


def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()


# ---------------------------------------------------------------------------
# Scan result cache (TTL = 1 hour by default)
# ---------------------------------------------------------------------------


def cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    now = _utcnow()
    with get_session() as session:
        row = session.get(ScanCacheRow, cache_key)
        if not row:
            return None
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
        if expires <= now:
            session.delete(row)
            session.commit()
            return None
        return json.loads(row.payload_json)


def cache_set(cache_key: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
    now = _utcnow()
    with get_session() as session:
        existing = session.get(ScanCacheRow, cache_key)
        if existing:
            session.delete(existing)
            session.flush()
        session.add(
            ScanCacheRow(
                cache_key=cache_key,
                payload_json=json.dumps(payload, default=str),
                created_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
        )
        session.commit()


def cache_purge_expired() -> int:
    now = _utcnow()
    with get_session() as session:
        rows = session.scalars(select(ScanCacheRow).where(ScanCacheRow.expires_at <= now)).all()
        count = len(rows)
        for row in rows:
            session.delete(row)
        session.commit()
        return count


# ---------------------------------------------------------------------------
# WHOIS cache (7 days — registration dates rarely change)
# ---------------------------------------------------------------------------


def whois_cache_get(domain: str) -> Optional[Dict[str, Any]]:
    now = _utcnow()
    with get_session() as session:
        row = session.get(WhoisCacheRow, domain)
        if not row:
            return None
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
        if expires <= now:
            session.delete(row)
            session.commit()
            return None
        return json.loads(row.payload_json)


def whois_cache_set(domain: str, payload: Dict[str, Any], ttl_days: int = 7) -> None:
    now = _utcnow()
    with get_session() as session:
        existing = session.get(WhoisCacheRow, domain)
        if existing:
            session.delete(existing)
            session.flush()
        session.add(
            WhoisCacheRow(
                domain=domain,
                payload_json=json.dumps(payload, default=str),
                created_at=now,
                expires_at=now + timedelta(days=ttl_days),
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Watches + listing history
# ---------------------------------------------------------------------------


def upsert_watch(
    watch_id: str,
    query_hash: str,
    product_name: str,
    official_price: float,
    image_url: str,
    interval_hours: int,
) -> WatchRow:
    now = _utcnow()
    with get_session() as session:
        existing = session.scalars(select(WatchRow).where(WatchRow.query_hash == query_hash)).first()
        if existing:
            existing.interval_hours = interval_hours
            existing.product_name = product_name
            existing.official_price = official_price
            existing.image_url = image_url
            session.commit()
            session.refresh(existing)
            return existing
        row = WatchRow(
            id=watch_id,
            product_name=product_name,
            official_price=official_price,
            image_url=image_url,
            interval_hours=interval_hours,
            query_hash=query_hash,
            created_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_watch(watch_id: str) -> Optional[WatchRow]:
    with get_session() as session:
        return session.get(WatchRow, watch_id)


def get_watch_by_hash(query_hash: str) -> Optional[WatchRow]:
    with get_session() as session:
        return session.scalars(select(WatchRow).where(WatchRow.query_hash == query_hash)).first()


def list_watches() -> List[WatchRow]:
    with get_session() as session:
        return list(session.scalars(select(WatchRow).order_by(WatchRow.created_at.desc())).all())


def due_watches(now: Optional[datetime] = None) -> List[WatchRow]:
    now = now or _utcnow()
    due: List[WatchRow] = []
    for watch in list_watches():
        if watch.interval_hours <= 0:
            continue
        if watch.last_run_at is None:
            due.append(watch)
            continue
        last = watch.last_run_at if watch.last_run_at.tzinfo else watch.last_run_at.replace(tzinfo=UTC)
        if now >= last + timedelta(hours=watch.interval_hours):
            due.append(watch)
    return due


def known_fingerprints(watch_id: str) -> set[str]:
    with get_session() as session:
        rows = session.scalars(
            select(ListingSightingRow.fingerprint).where(ListingSightingRow.watch_id == watch_id)
        ).all()
        return set(rows)


def record_sightings(
    watch_id: str,
    scan_id: str,
    listings: Sequence[Tuple[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Persist listings and return those whose fingerprint was not previously known
    (i.e. NEW infringements since the last scan of this watch).
    """
    now = _utcnow()
    new_payloads: List[Dict[str, Any]] = []
    with get_session() as session:
        existing = {
            fp
            for fp in session.scalars(
                select(ListingSightingRow.fingerprint).where(ListingSightingRow.watch_id == watch_id)
            ).all()
        }
        for fingerprint, payload in listings:
            if fingerprint in existing:
                row = session.scalars(
                    select(ListingSightingRow).where(
                        ListingSightingRow.watch_id == watch_id,
                        ListingSightingRow.fingerprint == fingerprint,
                    )
                ).first()
                if row:
                    row.last_seen_at = now
                    row.listing_json = json.dumps(payload, default=str)
                    row.scan_id = scan_id
            else:
                session.add(
                    ListingSightingRow(
                        watch_id=watch_id,
                        fingerprint=fingerprint,
                        listing_json=json.dumps(payload, default=str),
                        first_seen_at=now,
                        last_seen_at=now,
                        scan_id=scan_id,
                    )
                )
                new_payloads.append(payload)
                existing.add(fingerprint)
        session.commit()
    return new_payloads


def update_watch_run(
    watch_id: str,
    risk_score: float,
    result_payload: Dict[str, Any],
    new_payloads: List[Dict[str, Any]],
) -> None:
    now = _utcnow()
    with get_session() as session:
        watch = session.get(WatchRow, watch_id)
        if not watch:
            return
        watch.previous_scan_at = watch.last_run_at
        watch.last_run_at = now
        watch.last_risk_score = risk_score
        watch.last_result_json = json.dumps(result_payload, default=str)
        watch.last_new_json = json.dumps(new_payloads, default=str)
        session.commit()
