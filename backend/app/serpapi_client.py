"""SerpApi client — three engines queried in parallel via ThreadPoolExecutor."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from serpapi import GoogleSearch

from app.config import get_settings

logger = logging.getLogger(__name__)

SHOPPING_ENGINE = "google_shopping"
REVERSE_IMAGE_ENGINE = "google_reverse_image"
WEB_ENGINE = "google"

# Keep result sets small to control latency and SerpApi credit use
SHOPPING_NUM = 12
WEB_NUM = 10
IMAGE_NUM = 10

# Region/currency presets. INR routes the search through Google India so
# results skew toward Indian sellers/marketplaces and prices are quoted in INR.
CURRENCY_GEO: Dict[str, Dict[str, str]] = {
    "USD": {"gl": "us", "hl": "en"},
    "INR": {"gl": "in", "hl": "en", "currency": "INR"},
}


class SerpApiError(RuntimeError):
    pass


def _client_search(params: Dict[str, Any], currency: str = "USD") -> Dict[str, Any]:
    settings = get_settings()
    if not settings.serpapi_key:
        raise SerpApiError("SERPAPI_KEY is not configured")
    geo = CURRENCY_GEO.get(currency, CURRENCY_GEO["USD"])
    payload = {**params, "api_key": settings.serpapi_key, **geo}
    try:
        return GoogleSearch(payload).get_dict()
    except Exception as exc:
        logger.exception("SerpApi request failed (%s)", params.get("engine"))
        raise SerpApiError(f"SerpApi {params.get('engine')} request failed: {exc}") from exc


def _error_from(result: Dict[str, Any]) -> Optional[str]:
    err = result.get("error")
    return str(err) if err else None


def search_google_shopping(product_name: str, currency: str = "USD") -> Dict[str, Any]:
    return _client_search(
        {
            "engine": SHOPPING_ENGINE,
            "q": product_name,
            "num": SHOPPING_NUM,
        },
        currency=currency,
    )


def search_google_reverse_image(image_url: str, currency: str = "USD") -> Dict[str, Any]:
    return _client_search(
        {
            "engine": REVERSE_IMAGE_ENGINE,
            "image_url": image_url,
        },
        currency=currency,
    )


def search_google_web(product_name: str, currency: str = "USD") -> Dict[str, Any]:
    # Bias toward unofficial / reseller storefronts without restricting results to one marketplace
    query = f'{product_name} buy OR "for sale" OR reseller OR unofficial OR replica -site:wikipedia.org'
    return _client_search(
        {
            "engine": WEB_ENGINE,
            "q": query,
            "num": WEB_NUM,
        },
        currency=currency,
    )


def run_parallel_searches(
    product_name: str, image_url: str, currency: str = "USD"
) -> Tuple[Dict[str, Any], List[str]]:
    """Fire all three engines at once. Returns ({engine: result_or_error}, warnings)."""
    jobs = {
        SHOPPING_ENGINE: lambda: search_google_shopping(product_name, currency),
        REVERSE_IMAGE_ENGINE: lambda: search_google_reverse_image(image_url, currency),
        WEB_ENGINE: lambda: search_google_web(product_name, currency),
    }
    results: Dict[str, Any] = {}
    warnings: List[str] = []

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="serpapi") as pool:
        future_map = {pool.submit(fn): engine for engine, fn in jobs.items()}
        for future in as_completed(future_map):
            engine = future_map[future]
            try:
                payload = future.result()
                api_error = _error_from(payload)
                if api_error:
                    warnings.append(f"{engine}: {api_error}")
                    results[engine] = {"error": api_error}
                else:
                    results[engine] = payload
            except SerpApiError as exc:
                warnings.append(str(exc))
                results[engine] = {"error": str(exc)}
            except Exception as exc:
                warnings.append(f"{engine}: {exc}")
                results[engine] = {"error": str(exc)}

    return results, warnings
