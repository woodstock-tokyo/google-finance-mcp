from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

JSONValue = Any


@dataclass(frozen=True)
class EndpointMetadata:
    dataset_key: str
    current_rpc_id: str
    purpose: str
    request_shape: str
    slug: str
    source: str
    description: str = ""
    reference_rpc_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, JSONValue]:
        return {
            "dataset_key": self.dataset_key,
            "current_rpc_id": self.current_rpc_id,
            "purpose": self.purpose,
            "request_shape": self.request_shape,
            "slug": self.slug,
            "source": self.source,
            "description": self.description,
            "reference_rpc_ids": list(self.reference_rpc_ids),
        }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


# Reference-only table from:
# https://scraper.run/blog/reverse-engineering-google-finance
#
# These short method IDs are not treated as stable. The live id/hash used for a
# call always comes from the current page's AF_dataServiceRequests entry.
ARTICLE_REFERENCE_RPC_PURPOSES: dict[str, dict[str, str]] = {
    "xh8wxf": {"purpose": "Quote", "request_shape": "[[tuple], 1] or [[tuple]]"},
    "HqGpWd": {"purpose": "Company info", "request_shape": "[[tuple]]"},
    "uwlMvd": {"purpose": "Classification", "request_shape": "[[tuple]]"},
    "Pr8h2e": {"purpose": "Financials / Estimates", "request_shape": "[[tuple]] or [[tuple], 1]"},
    "AiCwsd": {"purpose": "Chart", "request_shape": "[[tuple], mode]"},
    "nBEQBc": {"purpose": "News", "request_shape": "[type, limit, [tuple]]"},
    "o6pODe": {"purpose": "Analyst articles", "request_shape": "[tuple]"},
    "SICF5d": {"purpose": "Related stocks", "request_shape": "[tuple, 18] or [tuple]"},
    "mKsvE": {"purpose": "Stock context", "request_shape": '["GOOGL:NASDAQ"]'},
    "Xhdx2e": {"purpose": "Market indices", "request_shape": "[null, 1]"},
    "YtbmEe": {"purpose": "Market movers", "request_shape": "[[categories], count, offset]"},
    "lvVhof": {"purpose": "Trending stocks", "request_shape": "[18]"},
    "JFUMjd": {"purpose": "Earnings calendar", "request_shape": "[]"},
    "XqaYg": {"purpose": "Category stocks", "request_shape": "[category, offset]"},
    "QKZUzd": {"purpose": "Top headline", "request_shape": "[1]"},
    "mysBRb": {"purpose": "Featured stocks", "request_shape": "[]"},
    "qt5Q2d": {"purpose": "Top stocks by metric", "request_shape": "[6, 1]"},
    "sy8gqe": {"purpose": "Category news", "request_shape": "[category, offset]"},
    "yYvDpf": {"purpose": "Unknown (empty)", "request_shape": "[tuple]"},
}


BETA_DATASET_PURPOSES: dict[str, tuple[str, str, str]] = {
    "ds:0": ("Market overview quotes", "[1]", "Symbol-independent market quote groups for the beta home page."),
    "ds:1": ("Equity sectors", "[null, [null, 1]]", "Sector performance list."),
    "ds:2": ("Earnings calendar", "[1, 0, 2]", "Upcoming and recent earnings calendar entries."),
    "ds:3": ("Earnings calendar secondary", "[3, 1]", "Secondary earnings calendar request; currently returns little or no data."),
    "ds:4": ("Market overview charts", "[0]", "Market overview chart data with SVG sparklines."),
    "ds:5": ("Market summary news clusters", '["market_summary", 1]', "Clustered market summary news cards."),
    "ds:6": ("Top finance articles", "[8]", "Top finance article list."),
    "ds:7": ("Market news", "[2, 20]", "Market news feed."),
    "ds:8": ("Market movers", "[[categories], count, offset]", "Market mover lists by category, count, and offset."),
    "ds:9": ("Empty initialization endpoint", "[]", "Initialization request that returns an empty payload."),
    "ds:10": ("Empty initialization endpoint", "[]", "Initialization request that returns an empty payload."),
    "ds:11": ("Equity sectors metadata", "[]", "Empty request that returns sector metadata."),
}


QUOTE_PAGE_DATASET_PURPOSES: dict[str, tuple[str, str, str]] = {
    "ds:0": ("Market overview quotes", "[1]", "Symbol-independent market quote groups."),
    "ds:1": ("Equity sectors", "[null, [null, 1]]", "Sector performance list."),
    "ds:2": ("Quote summary", "[[tuple], 1]", "Main quote payload for the requested security."),
    "ds:3": ("Company profile", "[[tuple]]", "Long company/security profile and descriptive fields."),
    "ds:4": ("Related securities", "[tuple, 4]", "Peer and related quote cards for comparison."),
    "ds:5": (
        "Earnings history and estimates",
        "[[tuple], 1]",
        "Quarterly rows with actual and estimated revenue/EPS fields.",
    ),
    "ds:6": (
        "Security overview card",
        "[[tuple], 1, 1, 1]",
        "Price, market cap, industry, logo, and summary quote fields.",
    ),
    "ds:7": ("Intraday chart points", "[[tuple], 1]", "Minute-level price points."),
    "ds:8": (
        "Intraday OHLCV chart",
        "[[tuple], 1, null, null, null, null, null, 1]",
        "Intraday candle rows with open, close, high, low, timestamp, and volume.",
    ),
    "ds:9": ("One-month chart points", "[[tuple], 3]", "Daily price points."),
    "ds:10": (
        "One-month OHLCV chart",
        "[[tuple], 3, null, null, null, null, null, 1]",
        "Daily candle rows with open, close, high, low, timestamp, and volume.",
    ),
    "ds:11": (
        "Key statistics / ratios",
        '[["SYMBOL", "EXCHANGE"]]',
        "Compact numeric ratio vector; individual field labels still need mapping.",
    ),
    "ds:12": ("Quote summary alternate", "[[tuple]]", "Quote payload without the trailing mode flag."),
    "ds:13": ("Financials / estimates", "[[tuple], null, 1]", "Financial statement and estimate arrays."),
    "ds:14": ("Market news feed", "[2, 12, [tuple]]", "General market or related news list."),
    "ds:15": ("Security news feed", "[5, 12, [tuple]]", "Company/security-specific article list."),
    "ds:16": (
        "Empty initialization endpoint",
        "[]",
        "Quote-page initialization request observed across equity, ETF, index, crypto, and FX pages; returns an empty payload.",
    ),
    "ds:17": (
        "Empty initialization endpoint",
        "[]",
        "Quote-page initialization request observed across equity, ETF, index, crypto, and FX pages; returns an empty payload.",
    ),
    "ds:18": ("Equity sectors metadata", "[]", "Empty request that returns sector metadata."),
}


def metadata_for_dataset(
    dataset_key: str,
    current_rpc_id: str,
    request: JSONValue,
    *,
    source_path: str = "/finance/beta",
) -> EndpointMetadata:
    if "/quote/" in source_path:
        quote_purpose = QUOTE_PAGE_DATASET_PURPOSES.get(dataset_key)
        if quote_purpose:
            purpose, request_shape, description = quote_purpose
            return EndpointMetadata(
                dataset_key=dataset_key,
                current_rpc_id=current_rpc_id,
                purpose=purpose,
                request_shape=request_shape,
                slug=_slug(purpose),
                source="google-finance-quote-dataset-key",
                description=description,
                reference_rpc_ids=tuple(
                    rpc_id
                    for rpc_id, metadata in ARTICLE_REFERENCE_RPC_PURPOSES.items()
                    if metadata["purpose"] == purpose
                ),
            )

        if current_rpc_id == "gCvqoe" and _is_quote_request(request):
            return EndpointMetadata(
                dataset_key=dataset_key,
                current_rpc_id=current_rpc_id,
                purpose="Quote",
                request_shape="[[tuple], 1] or [[tuple]]",
                slug="quote",
                source="google-finance-quote-request-shape",
                description="Main quote payload for the requested security.",
                reference_rpc_ids=("xh8wxf",),
            )

        if _is_company_info_like_request(request):
            return EndpointMetadata(
                dataset_key=dataset_key,
                current_rpc_id=current_rpc_id,
                purpose="Security tuple endpoint",
                request_shape="[[tuple]]",
                slug="security_tuple_endpoint",
                source="google-finance-quote-request-shape",
                description="Company/security tuple endpoint inferred from the request shape.",
                reference_rpc_ids=("HqGpWd", "uwlMvd", "o6pODe", "yYvDpf"),
            )

        inferred = _infer_from_request(request)
        if inferred:
            purpose, request_shape, reference_rpc_ids = inferred
            return EndpointMetadata(
                dataset_key=dataset_key,
                current_rpc_id=current_rpc_id,
                purpose=purpose,
                request_shape=request_shape,
                slug=_slug(purpose),
                source="google-finance-quote-request-shape",
                description="Purpose inferred from the live quote-page request shape.",
                reference_rpc_ids=reference_rpc_ids,
            )

        return EndpointMetadata(
            dataset_key=dataset_key,
            current_rpc_id=current_rpc_id,
            purpose=f"Quote page dataset {dataset_key}",
            request_shape=_request_shape(request),
            slug=f"quote_page_{dataset_key.replace(':', '_')}",
            source="google-finance-quote-dataset-key",
            description="Quote-page dataset discovered from AF_dataServiceRequests; purpose is not mapped yet.",
        )

    beta_purpose = BETA_DATASET_PURPOSES.get(dataset_key)
    if beta_purpose:
        purpose, request_shape, description = beta_purpose
        return EndpointMetadata(
            dataset_key=dataset_key,
            current_rpc_id=current_rpc_id,
            purpose=purpose,
            request_shape=request_shape,
            slug=_slug(purpose),
            source="google-finance-beta-dataset-key",
            description=description,
            reference_rpc_ids=tuple(
                rpc_id for rpc_id, metadata in ARTICLE_REFERENCE_RPC_PURPOSES.items() if metadata["purpose"] == purpose
            ),
        )

    inferred = _infer_from_request(request)
    if inferred:
        purpose, request_shape, reference_rpc_ids = inferred
        return EndpointMetadata(
            dataset_key=dataset_key,
            current_rpc_id=current_rpc_id,
            purpose=purpose,
            request_shape=request_shape,
            slug=_slug(purpose),
            source="live-af_dataServiceRequests-request-shape",
            description="Purpose inferred from the live request shape.",
            reference_rpc_ids=reference_rpc_ids,
        )

    return EndpointMetadata(
        dataset_key=dataset_key,
        current_rpc_id=current_rpc_id,
        purpose=f"Dataset {dataset_key}",
        request_shape="Discovered from AF_dataServiceRequests; purpose not inferred from request shape.",
        slug=dataset_key.replace(":", "_"),
        source="live-af_dataServiceRequests",
        description="Dataset discovered from AF_dataServiceRequests; purpose is not mapped yet.",
    )


def _request_shape(request: JSONValue) -> str:
    try:
        return json.dumps(request, separators=(",", ":"))
    except TypeError:
        return "Discovered from AF_dataServiceRequests; request shape is not JSON serializable."


def _infer_from_request(request: JSONValue) -> tuple[str, str, tuple[str, ...]] | None:
    if request == [1]:
        return "Top headline", "[1]", ("QKZUzd",)
    if request == [18]:
        return "Trending stocks", "[18]", ("lvVhof",)
    if request == [None, 1]:
        return "Market indices", "[null, 1]", ("Xhdx2e",)
    if request == [6, 1]:
        return "Top stocks by metric", "[6, 1]", ("qt5Q2d",)
    if request == [None, [None, 1]]:
        return "Equity sectors", "[null, [null, 1]]", ()
    if request == []:
        return "Empty request endpoint", "[]", ("JFUMjd", "mysBRb")
    if _is_market_movers_request(request):
        return "Market movers", "[[categories], count, offset]", ("YtbmEe",)
    if _is_market_summary_request(request):
        return "Market summary", '["market_summary", mode]', ()
    if _is_ticker_context_request(request):
        return "Stock context", '["SYMBOL:EXCHANGE"]', ("mKsvE",)
    if _is_quote_request(request):
        return "Quote", "[[tuple], 1] or [[tuple]]", ("xh8wxf",)
    if _is_chart_request(request):
        return "Chart", "[[tuple], mode]", ("AiCwsd",)
    if _is_company_info_like_request(request):
        return "Security tuple endpoint", "[[tuple]]", ("HqGpWd", "uwlMvd", "o6pODe", "yYvDpf")
    if _is_related_stocks_request(request):
        return "Related stocks", "[tuple, 18] or [tuple]", ("SICF5d",)
    if _is_news_request(request):
        return "News", "[type, limit, [tuple]]", ("nBEQBc",)
    return None


def _is_market_movers_request(request: JSONValue) -> bool:
    return (
        isinstance(request, list)
        and len(request) == 3
        and isinstance(request[0], list)
        and all(isinstance(item, int) for item in request[0])
        and isinstance(request[1], int)
        and isinstance(request[2], int)
    )


def _is_market_summary_request(request: JSONValue) -> bool:
    return (
        isinstance(request, list)
        and len(request) == 2
        and request[0] == "market_summary"
        and isinstance(request[1], int)
    )


def _is_ticker_context_request(request: JSONValue) -> bool:
    return (
        isinstance(request, list)
        and len(request) == 1
        and isinstance(request[0], str)
        and ":" in request[0]
    )


def _is_chart_request(request: JSONValue) -> bool:
    return isinstance(request, list) and len(request) == 2 and _looks_like_tuple_group(request[0]) and isinstance(request[1], int)


def _is_quote_request(request: JSONValue) -> bool:
    return (
        isinstance(request, list)
        and _looks_like_tuple_group(request[0] if request else None)
        and (len(request) == 1 or (len(request) == 2 and request[1] == 1))
    )


def _is_company_info_like_request(request: JSONValue) -> bool:
    return isinstance(request, list) and len(request) == 1 and _looks_like_tuple_group(request[0])


def _is_related_stocks_request(request: JSONValue) -> bool:
    return isinstance(request, list) and len(request) in (1, 2) and _looks_like_tuple(request[0]) and (
        len(request) == 1 or request[1] == 18
    )


def _is_news_request(request: JSONValue) -> bool:
    return (
        isinstance(request, list)
        and len(request) in (2, 3)
        and isinstance(request[0], int)
        and isinstance(request[1], int)
    )


def _looks_like_tuple_group(value: JSONValue) -> bool:
    return isinstance(value, list) and len(value) == 1 and _looks_like_tuple(value[0])


def _looks_like_tuple(value: JSONValue) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 2
        and value[0] is None
        and isinstance(value[1], list)
    )
