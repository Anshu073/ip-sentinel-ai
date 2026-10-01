"""Scan orchestration: SerpApi → WHOIS → scoring → cache → watch history."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.config import get_settings
from app.db import (
    cache_get,
    cache_set,
    get_watch_by_hash,
    record_sightings,
    update_watch_run,
    upsert_watch,
)
from app.legal import draft_legal_notice
from app.models.schemas import (
    FactorBreakdown,
    FlaggedListing,
    LegalNoticeDraft,
    ListingEvidence,
    RiskBreakdown,
    ScanResponse,
)
from app.scoring import (
    DOMAIN_WEIGHT,
    FLAG_THRESHOLD,
    PRICE_WEIGHT,
    SELLER_WEIGHT,
    VISUAL_WEIGHT,
    combine_listing_score,
    domain_risk_score,
    normalize_seller_rating,
    price_deviation_score,
    seller_credibility_score,
    visual_match_score,
)
from app.serpapi_client import (
    REVERSE_IMAGE_ENGINE,
    SHOPPING_ENGINE,
    WEB_ENGINE,
    run_parallel_searches,
)
from app.whois_lookup import created_at_from_payload, extract_domain, format_age, lookup_many

logger = logging.getLogger(__name__)
UTC = timezone.utc

TRUSTED_HOST_FRAGMENTS = (
    "amazon.",
    "walmart.",
    "target.",
    "bestbuy.",
    "ebay.",
    "apple.com",
    "microsoft.com",
    "google.",
    "wikipedia.org",
    "youtube.com",
)


def query_hash(product_name: str, official_price: float, image_url: str, currency: str = "USD") -> str:
    raw = f"{product_name.strip().lower()}|{official_price:.2f}|{str(image_url).strip()}|{currency}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def listing_fingerprint(url: str, title: Optional[str], price: Optional[float]) -> str:
    host_path = url
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host_path = f"{(parsed.hostname or '').lower()}{parsed.path}"
    except ValueError:
        pass
    raw = f"{host_path}|{(title or '').strip().lower()}|{price}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_price(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", text.replace("\xa0", " "))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _is_trusted_host(domain: Optional[str]) -> bool:
    if not domain:
        return False
    return any(frag in domain for frag in TRUSTED_HOST_FRAGMENTS)


def _as_rating(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return parse_price(value)


def _shopping_listings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("shopping_results") or payload.get("organic_results") or []
    listings = []
    for row in rows:
        url = row.get("product_link") or row.get("link") or ""
        seller = row.get("source") if isinstance(row.get("source"), str) else None
        rating: Any = row.get("rating")
        seller_obj = row.get("seller")
        if isinstance(seller_obj, dict):
            seller = seller_obj.get("name") or seller
            rating = rating if rating is not None else seller_obj.get("rating")
        elif isinstance(seller_obj, str):
            seller = seller_obj
        listings.append(
            {
                "title": row.get("title"),
                "url": url,
                "price": parse_price(row.get("extracted_price") or row.get("price") or row.get("old_price")),
                "seller_name": seller,
                "seller_rating": _as_rating(rating),
                "thumbnail": row.get("thumbnail") or row.get("image"),
                "engine": SHOPPING_ENGINE,
            }
        )
    return listings


def _web_listings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    listings = []
    for row in payload.get("organic_results") or []:
        url = row.get("link") or ""
        listings.append(
            {
                "title": row.get("title"),
                "url": url,
                "price": parse_price(row.get("rich_snippet") if isinstance(row.get("rich_snippet"), str) else None),
                "seller_name": urlparse(url).hostname if url else None,
                "seller_rating": None,
                "thumbnail": (row.get("thumbnail") or (row.get("about_this_result") or {}).get("source", {}).get("icon")),
                "engine": WEB_ENGINE,
            }
        )
    return listings


def _reverse_image_index(payload: Dict[str, Any], product_name: str) -> Dict[str, Any]:
    """Build a host → best match map from google_reverse_image results."""
    buckets: List[Dict[str, Any]] = []
    for key in ("image_results", "inline_images", "visual_matches", "exact_matches"):
        items = payload.get(key) or []
        if isinstance(items, dict):
            items = items.get("results") or items.get("images") or []
        for row in items:
            if not isinstance(row, dict):
                continue
            url = row.get("link") or row.get("source") or row.get("original") or ""
            image = row.get("original") or row.get("thumbnail") or row.get("image")
            title = row.get("title") or row.get("source") or ""
            sim = row.get("similarity") or row.get("position")
            similarity = 0.0
            if isinstance(sim, (int, float)) and float(sim) <= 1:
                similarity = float(sim)
            elif isinstance(sim, (int, float)) and float(sim) <= 100:
                similarity = float(sim) / 100.0
            else:
                similarity = _title_similarity(product_name, str(title))
            exact = key == "exact_matches" or similarity >= 0.9 or "exact" in str(row.get("tag", "")).lower()
            buckets.append(
                {
                    "url": url,
                    "image": image,
                    "title": title,
                    "domain": extract_domain(url) if url else None,
                    "similarity": similarity,
                    "exact_or_near": exact or similarity >= 0.85,
                    "section": key,
                }
            )

    by_domain: Dict[str, Dict[str, Any]] = {}
    best_global = {"similarity": 0.0, "exact_or_near": False, "image": None}
    for item in buckets:
        if item["similarity"] > best_global["similarity"]:
            best_global = item
        domain = item.get("domain")
        if domain and (domain not in by_domain or item["similarity"] > by_domain[domain]["similarity"]):
            by_domain[domain] = item
    return {"by_domain": by_domain, "best": best_global, "count": len(buckets)}


def _empty_breakdown() -> RiskBreakdown:
    def factor(weight: float, detail: str) -> FactorBreakdown:
        return FactorBreakdown(weight=weight, score=0.0, triggered=False, detail=detail)

    return RiskBreakdown(
        price_deviation=factor(PRICE_WEIGHT, "No listings to evaluate"),
        seller_credibility=factor(SELLER_WEIGHT, "No listings to evaluate"),
        visual_brand_match=factor(VISUAL_WEIGHT, "No reverse-image matches evaluated"),
        domain_risk=factor(DOMAIN_WEIGHT, "No domains to evaluate"),
    )


def _serialize_listing(item: FlaggedListing) -> Dict[str, Any]:
    return item.model_dump(mode="json")


def _listing_from_dict(data: Dict[str, Any]) -> FlaggedListing:
    return FlaggedListing.model_validate(data)


def score_candidates(
    product_name: str,
    official_price: float,
    official_image_url: str,
    engine_results: Dict[str, Any],
    scanned_at: datetime,
) -> Tuple[List[FlaggedListing], RiskBreakdown, List[str]]:
    warnings: List[str] = []
    shopping = engine_results.get(SHOPPING_ENGINE) or {}
    web = engine_results.get(WEB_ENGINE) or {}
    reverse = engine_results.get(REVERSE_IMAGE_ENGINE) or {}

    if shopping.get("error"):
        warnings.append(f"google_shopping: {shopping['error']}")
    if web.get("error"):
        warnings.append(f"google: {web['error']}")
    if reverse.get("error"):
        warnings.append(f"google_reverse_image: {reverse['error']}")

    visual_index = _reverse_image_index(reverse if not reverse.get("error") else {}, product_name)
    visual_best = visual_index.get("best") or {}

    raw_listings: List[Dict[str, Any]] = []
    if not shopping.get("error"):
        raw_listings.extend(_shopping_listings(shopping))
    if not web.get("error"):
        raw_listings.extend(_web_listings(web))

    # Deduplicate by URL first
    seen_urls = set()
    by_url: List[Dict[str, Any]] = []
    for row in raw_listings:
        url = (row.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        by_url.append(row)

    # Some regions/queries return many near-duplicate cards that only differ
    # by tracking params in the URL but show identical title/price/seller —
    # collapse those down to a single listing.
    seen_content = set()
    unique: List[Dict[str, Any]] = []
    for row in by_url:
        content_key = (
            (row.get("title") or "").strip().lower(),
            row.get("seller_name") or "",
            row.get("price"),
        )
        if content_key in seen_content:
            continue
        seen_content.add(content_key)
        unique.append(row)

    # Drop listings whose title has essentially nothing in common with the
    # official product name (keeps genuinely relevant matches, filters out
    # unrelated products that only fuzzy-matched on a shared brand/word).
    MIN_TITLE_SIMILARITY = 0.28
    unique = [
        row
        for row in unique
        if _title_similarity(product_name, str(row.get("title") or "")) >= MIN_TITLE_SIMILARITY
        or not row.get("title")
    ]

    domains = [extract_domain(row["url"]) for row in unique]
    whois_map = lookup_many([d for d in domains if d])

    flagged: List[FlaggedListing] = []
    for row in unique:
        url = row["url"]
        domain = extract_domain(url)
        whois_payload = whois_map.get(domain or "", {})
        created_at = created_at_from_payload(whois_payload) if whois_payload else None

        listing_price = row.get("price")
        rating_5 = normalize_seller_rating(row.get("seller_rating"))

        visual = visual_index["by_domain"].get(domain or "")
        similarity = 0.0
        exact = False
        matched_image = row.get("thumbnail") or official_image_url
        if visual:
            similarity = float(visual.get("similarity") or 0.0)
            exact = bool(visual.get("exact_or_near"))
            matched_image = visual.get("image") or matched_image
        else:
            # Fall back to title similarity vs official product name + global reverse-image strength
            similarity = max(
                _title_similarity(product_name, str(row.get("title") or "")),
                float(visual_best.get("similarity") or 0.0) * 0.4,
            )
            exact = similarity >= 0.85

        # Official/trusted retailers with near-MSRP pricing are unlikely infringements
        price_pts, price_detail, price_hit = price_deviation_score(listing_price, official_price)
        seller_pts, seller_detail, seller_hit = seller_credibility_score(rating_5)
        visual_pts, visual_detail, visual_hit = visual_match_score(similarity, exact)
        domain_pts, domain_detail, domain_hit = domain_risk_score(created_at, scanned_at)

        if _is_trusted_host(domain) and not price_hit and not domain_hit:
            domain_pts = min(domain_pts, 0.0)
            domain_hit = False
            domain_detail = f"{domain_detail} (trusted marketplace host — domain factor waived)"

        # Web-search hits with no price are just articles/mentions (reviews,
        # forum posts, videos) — not actual storefronts selling the product —
        # so don't flag them purely on "seller/domain unknown" defaults.
        if row.get("engine") == WEB_ENGINE and listing_price is None:
            continue

        # A listing priced at/above the official price is not price-slashing;
        # keep it only if the visual match is strong.
        if listing_price is not None and listing_price >= official_price and not visual_hit:
            continue

        total = combine_listing_score(price_pts, seller_pts, visual_pts, domain_pts)
        if total < FLAG_THRESHOLD and not (price_hit or domain_hit):
            continue

        item_id = f"INF-{uuid.uuid4().hex[:8].upper()}"
        flagged.append(
            FlaggedListing(
                id=item_id,
                title=row.get("title"),
                source_engine=row.get("engine") or "unknown",
                seller_name=row.get("seller_name"),
                seller_rating=rating_5,
                listing_price=listing_price,
                official_price=official_price,
                risk_score=total,
                domain=domain,
                domain_created_at=created_at,
                evidence=ListingEvidence(
                    matched_image=matched_image,
                    listing_url=url,
                    price=listing_price,
                    timestamp=scanned_at,
                    whois_domain_age=format_age(created_at, scanned_at),
                ),
                factor_scores={
                    "price_deviation": price_pts,
                    "seller_credibility": seller_pts,
                    "visual_brand_match": visual_pts,
                    "domain_risk": domain_pts,
                    "price_detail": price_detail,
                    "seller_detail": seller_detail,
                    "visual_detail": visual_detail,
                    "domain_detail": domain_detail,
                },
            )
        )

    flagged.sort(key=lambda item: item.risk_score, reverse=True)

    if not flagged:
        breakdown = _empty_breakdown()
        if visual_best.get("exact_or_near"):
            breakdown.visual_brand_match = FactorBreakdown(
                weight=VISUAL_WEIGHT,
                score=VISUAL_WEIGHT,
                triggered=True,
                detail="Official image produced exact/near reverse-image matches, but no listing crossed the flag threshold",
            )
        return flagged, breakdown, warnings

    def max_factor(key: str, weight: float, default_detail: str) -> FactorBreakdown:
        best = max(flagged, key=lambda item: float(item.factor_scores.get(key, 0) or 0))
        score = float(best.factor_scores.get(key, 0) or 0)
        detail_key = {
            "price_deviation": "price_detail",
            "seller_credibility": "seller_detail",
            "visual_brand_match": "visual_detail",
            "domain_risk": "domain_detail",
        }[key]
        return FactorBreakdown(
            weight=weight,
            score=score,
            triggered=score >= weight * 0.99,
            detail=str(best.factor_scores.get(detail_key) or default_detail),
        )

    breakdown = RiskBreakdown(
        price_deviation=max_factor("price_deviation", PRICE_WEIGHT, "Price factor"),
        seller_credibility=max_factor("seller_credibility", SELLER_WEIGHT, "Seller factor"),
        visual_brand_match=max_factor("visual_brand_match", VISUAL_WEIGHT, "Visual factor"),
        domain_risk=max_factor("domain_risk", DOMAIN_WEIGHT, "Domain factor"),
    )
    return flagged, breakdown, warnings


def overall_risk(breakdown: RiskBreakdown) -> float:
    return round(
        min(
            100.0,
            breakdown.price_deviation.score
            + breakdown.seller_credibility.score
            + breakdown.visual_brand_match.score
            + breakdown.domain_risk.score,
        ),
        2,
    )


def execute_scan(
    product_name: str,
    official_price: float,
    image_url: str,
    *,
    use_cache: bool = True,
    rescan_interval_hours: Optional[int] = None,
    currency: str = "USD",
) -> ScanResponse:
    settings = get_settings()
    scanned_at = datetime.now(UTC)
    cache_key = query_hash(product_name, official_price, image_url, currency)
    image_url_str = str(image_url)

    interval = settings.rescan_interval_hours if rescan_interval_hours is None else rescan_interval_hours

    if use_cache:
        cached = cache_get(cache_key)
        if cached:
            response = ScanResponse.model_validate(cached)
            response.cached = True
            return response

    engine_results, serp_warnings = run_parallel_searches(product_name, image_url_str, currency)
    flagged, breakdown, score_warnings = score_candidates(
        product_name, official_price, image_url_str, engine_results, scanned_at
    )
    warnings = serp_warnings + score_warnings
    risk = overall_risk(breakdown)
    notice: LegalNoticeDraft = draft_legal_notice(product_name, flagged)

    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    watch_id: Optional[str] = None
    new_items: List[FlaggedListing] = flagged

    if interval and interval > 0:
        existing = get_watch_by_hash(cache_key)
        watch_id = existing.id if existing else f"watch_{uuid.uuid4().hex[:12]}"
        upsert_watch(
            watch_id=watch_id,
            query_hash=cache_key,
            product_name=product_name,
            official_price=official_price,
            image_url=image_url_str,
            interval_hours=interval,
        )
        pairs = [
            (listing_fingerprint(item.evidence.listing_url, item.title, item.listing_price), _serialize_listing(item))
            for item in flagged
        ]
        new_payloads = record_sightings(watch_id, scan_id, pairs)
        new_items = [_listing_from_dict(p) for p in new_payloads] if existing else flagged
        result_preview = {
            "scan_id": scan_id,
            "risk_score": risk,
            "flagged_count": len(flagged),
        }
        update_watch_run(watch_id, risk, result_preview, [_serialize_listing(i) for i in new_items])

    response = ScanResponse(
        scan_id=scan_id,
        product_name=product_name,
        official_price=official_price,
        image_url=image_url_str,
        scanned_at=scanned_at,
        cached=False,
        currency=currency,
        watch_id=watch_id,
        rescan_interval_hours=interval if interval and interval > 0 else None,
        risk_score=risk,
        risk_breakdown=breakdown,
        flagged_listings=flagged,
        new_infringements=new_items,
        engines_used=[SHOPPING_ENGINE, REVERSE_IMAGE_ENGINE, WEB_ENGINE],
        legal_notice_draft=notice,
        warnings=warnings,
    )

    if use_cache:
        cache_set(cache_key, response.model_dump(mode="json"), settings.cache_ttl_seconds)

    return response
