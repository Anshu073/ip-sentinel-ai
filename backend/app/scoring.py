"""Weighted 0–100% infringement risk score.

Weights (must sum to 100):
  - Price deviation     40%  — listing price < 50% of official MSRP → full 40
  - Seller credibility  20%  — seller rating < 3.0 (5-star scale) → full 20
  - Visual brand match  20%  — reverse-image exact/near match → full 20
  - Domain risk         20%  — WHOIS registration age < 6 months → full 20
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

PRICE_WEIGHT = 40.0
SELLER_WEIGHT = 20.0
VISUAL_WEIGHT = 20.0
DOMAIN_WEIGHT = 20.0
SIX_MONTHS_DAYS = 182  # ~6 months

# Listings at or above this per-item score are returned in flagged_listings
FLAG_THRESHOLD = 20.0


def normalize_seller_rating(raw: Optional[float]) -> Optional[float]:
    """Map marketplace ratings onto a 0–5 star scale.

    Google Shopping sometimes returns 1–5, sometimes a 0–100 percentage.
    """
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 5.0:
        return max(0.0, min(5.0, value / 20.0 if value <= 100 else 5.0))
    return max(0.0, min(5.0, value))


def price_deviation_score(listing_price: Optional[float], official_price: float) -> Tuple[float, str, bool]:
    if listing_price is None or official_price <= 0:
        return 0.0, "No listing price available — price factor not applied", False

    ratio = listing_price / official_price
    if listing_price < 0.5 * official_price:
        return (
            PRICE_WEIGHT,
            f"Listing price {listing_price:.2f} is {ratio:.0%} of official {official_price:.2f} (< 50%)",
            True,
        )

    # Partial credit between 50% and 100% of MSRP (linear decay 40 → 0)
    if listing_price >= official_price:
        return 0.0, f"Listing price {listing_price:.2f} is at or above official {official_price:.2f}", False

    span = 0.5
    over = ratio - 0.5
    points = PRICE_WEIGHT * (1.0 - over / span)
    return (
        round(points, 2),
        f"Listing price {listing_price:.2f} is {ratio:.0%} of official {official_price:.2f}",
        points >= PRICE_WEIGHT * 0.5,
    )


def seller_credibility_score(rating_5: Optional[float]) -> Tuple[float, str, bool]:
    if rating_5 is None:
        return (
            SELLER_WEIGHT * 0.5,
            "Seller rating missing — treated as moderate credibility risk",
            False,
        )
    if rating_5 < 3.0:
        return SELLER_WEIGHT, f"Seller rating {rating_5:.1f}/5.0 is below 3.0", True
    if rating_5 >= 4.5:
        return 0.0, f"Seller rating {rating_5:.1f}/5.0 is high", False
    # 3.0 → 20, 4.5 → 0
    points = SELLER_WEIGHT * (4.5 - rating_5) / 1.5
    return round(max(0.0, points), 2), f"Seller rating {rating_5:.1f}/5.0", False


def visual_match_score(similarity: float, exact_or_near: bool) -> Tuple[float, str, bool]:
    similarity = max(0.0, min(1.0, similarity))
    if exact_or_near:
        return VISUAL_WEIGHT, "Reverse-image search reported an exact/near visual match", True
    points = round(VISUAL_WEIGHT * similarity, 2)
    return (
        points,
        f"Visual similarity {similarity:.0%} against the official product image",
        similarity >= 0.85,
    )


def domain_risk_score(
    created_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> Tuple[float, str, bool]:
    if created_at is None:
        return 5.0, "WHOIS creation date unavailable — slight domain-risk penalty", False

    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0, (now - created_at).days)
    if age_days < SIX_MONTHS_DAYS:
        return (
            DOMAIN_WEIGHT,
            f"Domain registered {age_days} day(s) ago (< 6 months)",
            True,
        )
    years = age_days / 365.25
    return 0.0, f"Domain age {age_days} days (~{years:.1f} years)", False


def combine_listing_score(
    price_pts: float,
    seller_pts: float,
    visual_pts: float,
    domain_pts: float,
) -> float:
    return round(min(100.0, price_pts + seller_pts + visual_pts + domain_pts), 2)
