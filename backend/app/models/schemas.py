"""Pydantic request / response models for the scanner API."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ScanRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=300)
    official_price: float = Field(..., gt=0, description="Brand MSRP / official list price")
    image_url: HttpUrl = Field(..., description="Public URL of the official product image")
    currency: Literal["USD", "INR"] = Field(default="USD", description="Currency of official_price — also selects the SerpApi search region")

    # Optional: persist this query and re-run every N hours (overrides env default)
    # Omit to use RESCAN_INTERVAL_HOURS. Send 0 to skip scheduling a watch.
    rescan_interval_hours: Optional[int] = Field(default=None, ge=0, le=168)


class FactorBreakdown(BaseModel):
    weight: float
    score: float = Field(..., ge=0, le=100, description="Points contributed toward the 0–100 risk score")
    triggered: bool
    detail: str


class RiskBreakdown(BaseModel):
    price_deviation: FactorBreakdown
    seller_credibility: FactorBreakdown
    visual_brand_match: FactorBreakdown
    domain_risk: FactorBreakdown


class ListingEvidence(BaseModel):
    matched_image: Optional[str] = None
    listing_url: str
    price: Optional[float] = None
    timestamp: datetime
    whois_domain_age: Optional[str] = Field(
        default=None,
        description="Human-readable domain age, e.g. '42 days' or 'unknown'",
    )


class FlaggedListing(BaseModel):
    id: str
    title: Optional[str] = None
    source_engine: str
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None
    listing_price: Optional[float] = None
    official_price: float
    risk_score: float
    domain: Optional[str] = None
    domain_created_at: Optional[datetime] = None
    evidence: ListingEvidence
    factor_scores: Dict[str, Any]


class LegalNoticeDraft(BaseModel):
    subject: str
    body: str
    listings_cited: int
    disclaimer: str = "AI-generated draft for brand/legal team review — not legal advice"


class ScanResponse(BaseModel):
    scan_id: str
    product_name: str
    official_price: float
    image_url: str
    scanned_at: datetime
    cached: bool
    currency: Literal["USD", "INR"] = "USD"
    watch_id: Optional[str] = None
    rescan_interval_hours: Optional[int] = None
    risk_score: float = Field(..., ge=0, le=100)
    risk_breakdown: RiskBreakdown
    flagged_listings: List[FlaggedListing]
    new_infringements: List[FlaggedListing] = Field(
        default_factory=list,
        description="Listings not seen on the previous scan for this watch (full set on first run)",
    )
    engines_used: List[str]
    legal_notice_draft: LegalNoticeDraft
    warnings: List[str] = Field(default_factory=list)


class WatchSummary(BaseModel):
    watch_id: str
    product_name: str
    official_price: float
    image_url: str
    interval_hours: int
    last_run_at: Optional[datetime] = None
    last_risk_score: Optional[float] = None
    last_new_count: int = 0
    created_at: datetime


class NewInfringementsResponse(BaseModel):
    watch_id: str
    product_name: str
    compared_at: datetime
    previous_scan_at: Optional[datetime] = None
    new_infringements: List[FlaggedListing]
    legal_notice_draft: LegalNoticeDraft


class HealthResponse(BaseModel):
    status: str
    serpapi_configured: bool
    groq_configured: bool
    rescan_interval_hours: int
    cache_ttl_seconds: int
    extra: Dict[str, Any] = Field(default_factory=dict)
