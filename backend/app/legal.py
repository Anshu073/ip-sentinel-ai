"""Legal notice draft — Groq when configured, otherwise a deterministic template."""

from __future__ import annotations

import logging
from typing import List

from app.config import get_settings
from app.models.schemas import FlaggedListing, LegalNoticeDraft

logger = logging.getLogger(__name__)

DISCLAIMER = "AI-generated draft for brand/legal team review — not legal advice"


def _template(product_name: str, listings: List[FlaggedListing]) -> LegalNoticeDraft:
    lines = []
    for item in listings[:8]:
        price = f"{item.listing_price:.2f}" if item.listing_price is not None else "unknown"
        lines.append(f"- {item.evidence.listing_url} (listed at {price}; seller={item.seller_name or 'unknown'})")
    cited = "\n".join(lines) if lines else "- (no flagged listings in this scan)"
    body = (
        f"Re: Unauthorized listing(s) of “{product_name}”\n\n"
        "We represent the brand owner of the product identified above. Automated brand-protection "
        "monitoring has identified the following marketplace or web listings that appear to offer "
        "the product (or a confusingly similar product) without authorization, including listings "
        "priced well below official channels and/or hosted on recently registered domains:\n\n"
        f"{cited}\n\n"
        "We request that you preserve records, disable the listings pending review, and contact "
        "our brand-protection team within 5 business days. This message is a draft for internal "
        "legal review and is not itself a formal demand.\n"
    )
    return LegalNoticeDraft(
        subject=f"Draft notice: suspected infringement — {product_name}",
        body=body,
        listings_cited=len(listings),
        disclaimer=DISCLAIMER,
    )


def draft_legal_notice(product_name: str, listings: List[FlaggedListing]) -> LegalNoticeDraft:
    fallback = _template(product_name, listings)
    settings = get_settings()
    if not settings.groq_api_key:
        return fallback

    try:
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        evidence = "\n".join(
            f"- url={item.evidence.listing_url} price={item.listing_price} seller={item.seller_name} "
            f"risk={item.risk_score} domain_age={item.evidence.whois_domain_age}"
            for item in listings[:10]
        ) or "(none)"
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You draft short cease-and-desist style emails for a brand-protection team. "
                        "Do not claim to be a lawyer. Do not invent statutes or case law. "
                        "Keep the tone professional. Return only the email body."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Product: {product_name}\nEvidence listings:\n{evidence}\n"
                        "Write a concise draft notice citing those URLs."
                    ),
                },
            ],
        )
        body = (completion.choices[0].message.content or "").strip() or fallback.body
        return LegalNoticeDraft(
            subject=f"Draft notice: suspected infringement — {product_name}",
            body=body,
            listings_cited=len(listings),
            disclaimer=DISCLAIMER,
        )
    except Exception:
        logger.exception("Groq legal-notice draft failed; using template")
        return fallback
