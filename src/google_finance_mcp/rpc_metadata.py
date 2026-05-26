from __future__ import annotations

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
    reference_rpc_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, JSONValue]:
        return {
            "dataset_key": self.dataset_key,
            "current_rpc_id": self.current_rpc_id,
            "purpose": self.purpose,
            "request_shape": self.request_shape,
            "slug": self.slug,
            "source": self.source,
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


BETA_DATASET_PURPOSES: dict[str, tuple[str, str]] = {
    "ds:0": ("Market overview quotes", "[1]"),
    "ds:1": ("Equity sectors", "[null, [null, 1]]"),
    "ds:2": ("Earnings calendar", "[1, 0, 2]"),
    "ds:3": ("Earnings calendar secondary", "[3, 1]"),
    "ds:4": ("Market overview charts", "[0]"),
    "ds:5": ("Market summary news clusters", '["market_summary", 1]'),
    "ds:6": ("Top finance articles", "[8]"),
    "ds:7": ("Market news", "[2, 20]"),
    "ds:8": ("Market movers", "[[categories], count, offset]"),
    "ds:9": ("Empty initialization endpoint", "[]"),
    "ds:10": ("Empty initialization endpoint", "[]"),
    "ds:11": ("Equity sectors metadata", "[]"),
}


def metadata_for_dataset(dataset_key: str, current_rpc_id: str, request: JSONValue) -> EndpointMetadata:
    beta_purpose = BETA_DATASET_PURPOSES.get(dataset_key)
    if beta_purpose:
        purpose, request_shape = beta_purpose
        return EndpointMetadata(
            dataset_key=dataset_key,
            current_rpc_id=current_rpc_id,
            purpose=purpose,
            request_shape=request_shape,
            slug=_slug(purpose),
            source="google-finance-beta-dataset-key",
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
            reference_rpc_ids=reference_rpc_ids,
        )

    return EndpointMetadata(
        dataset_key=dataset_key,
        current_rpc_id=current_rpc_id,
        purpose=f"Dataset {dataset_key}",
        request_shape="Discovered from AF_dataServiceRequests; purpose not inferred from request shape.",
        slug=dataset_key.replace(":", "_"),
        source="live-af_dataServiceRequests",
    )


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
    if _is_chart_request(request):
        return "Chart", "[[tuple], mode]", ("AiCwsd",)
    if _is_quote_request(request):
        return "Quote", "[[tuple], 1] or [[tuple]]", ("xh8wxf",)
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
