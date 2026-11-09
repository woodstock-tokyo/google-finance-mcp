"""Semantic access to live page RPCs, without assuming stable ds:* positions.

Dataset keys, method IDs and security tuples belong to the fetched page. Never
replace those tuples with a colon-delimited ticker or copy home-page positions.
Unsupported features fail explicitly rather than guessing an RPC or payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import ApiMapping, DataServiceRequest, GoogleFinanceClient


QUOTE_ENDPOINTS: dict[str, tuple[str, ...]] = {
    "quote_summary": ("Quote summary",),
    "company_profile": ("Company profile",),
    "key_statistics": ("Key statistics / ratios", "Market statistics"),
    "related_securities": ("Related securities",),
    "analyst_ratings": ("Analyst ratings and price targets",),
    "earnings_history_alts": ("Earnings history and estimates alternate",),
    "security_overview_alt": ("Security overview card alternate",),
    "security_news_feed": ("Security news feed",),
    "financials": ("Financials / estimates",),
}

HOME_ENDPOINTS: dict[str, tuple[str, ...]] = {
    "earnings_calendar": ("Earnings calendar",),
    "featured_stocks": ("Featured stocks",),
    "market_news_feed": ("Market news", "Market news feed"),
    "category_news": ("Category news",),
}

# Range names are selectors, not permission to manufacture requests. A mode must
# actually appear on this security's page before any corresponding tool can call it.
CHART_MODES = {"1d": 1, "5d": 2, "1m": 3, "6m": 4, "1y": 6, "5y": 7, "max": 8}


class QuoteDatasetUnavailable(ValueError):
    """The current page does not advertise an identifiable requested feature."""


def quote_page_path(symbol: str, exchange: str, *, beta: bool = True) -> str:
    symbol, exchange = symbol.strip().upper(), exchange.strip().upper()
    if not symbol or not exchange or any(char in symbol + exchange for char in "/:?#"):
        raise ValueError("symbol and exchange must be nonempty ticker components, not paths or URLs")
    return f"/finance/{'beta/' if beta else ''}quote/{symbol}:{exchange}"


def chart_datasets(mapping: ApiMapping) -> list[dict[str, Any]]:
    charts = []
    for entry in mapping.requests.values():
        request = entry.request
        if not ("chart" in entry.metadata.purpose.lower() and isinstance(request, list)
                and len(request) >= 2 and type(request[1]) is int):
            continue
        if len(request) == 2:
            kind = "points"
        elif len(request) == 8 and request[2:7] == [None] * 5 and request[7] == 1:
            kind = "ohlcv"
        else:
            continue
        charts.append({
            "dataset_key": entry.key,
            "rpc_id": entry.rpc_id,
            "mode": request[1],
            "interval": next((name for name, mode in CHART_MODES.items() if mode == request[1]), None),
            "kind": kind,
            "request": request,
        })
    return charts


def select_dataset(mapping: ApiMapping, endpoint: str, *, interval: str = "1d", kind: str = "points") -> DataServiceRequest:
    if endpoint == "chart":
        if interval not in CHART_MODES:
            raise ValueError(f"Unknown chart interval: {interval}")
        if kind not in {"points", "ohlcv"}:
            raise ValueError(f"Unknown chart kind: {kind}")
        for chart in chart_datasets(mapping):
            if chart["interval"] == interval and chart["kind"] == kind:
                return mapping.requests[chart["dataset_key"]]
    else:
        purposes = {**QUOTE_ENDPOINTS, **HOME_ENDPOINTS}.get(endpoint)
        if purposes is None:
            raise ValueError(f"Unknown semantic endpoint: {endpoint}")
        for purpose in purposes:
            for entry in mapping.requests.values():
                if entry.metadata.purpose == purpose:
                    return entry
    raise QuoteDatasetUnavailable(
        f"No advertised dataset for {endpoint}"
        f"{f' ({interval}, {kind})' if endpoint == 'chart' else ''} on {mapping.source_path}. "
        "Use google_finance_list_page_rpcs or google_finance_enumerate_chart_intervals "
        "to inspect the live mapping; explicit experiments can use google_finance_test_rpc."
    )


async def call_page_endpoint(
    client: GoogleFinanceClient,
    endpoint: str,
    *,
    page_path: str,
    request_override: Any = None,
    interval: str = "1d",
    kind: str = "points",
    hl: str = "en",
    gl: str = "us",
) -> dict[str, Any]:
    for force_refresh in (False, True):
        mapping = await client.get_mapping(page_path=page_path, force_refresh=force_refresh)
        try:
            entry = select_dataset(mapping, endpoint, interval=interval, kind=kind)
            break
        except QuoteDatasetUnavailable:
            if force_refresh:
                raise
    # Reuse mapping-based transport, refresh behavior, and provenance-gated labels.
    return await client.call_dataset(
        entry.key, request_override, page_path=page_path, hl=hl, gl=gl,
    )


async def detect_quote_rpcs_for_symbol(
    client: GoogleFinanceClient, symbol: str, exchange: str, *, beta: bool = True,
) -> dict[str, Any]:
    mapping = await client.get_mapping(page_path=quote_page_path(symbol, exchange, beta=beta))
    endpoints = {}
    for endpoint in QUOTE_ENDPOINTS:
        try:
            endpoints[endpoint] = select_dataset(mapping, endpoint).as_dict()
        except QuoteDatasetUnavailable:
            endpoints[endpoint] = None
    return {**mapping.as_dict(), "endpoints": endpoints, "chart_intervals": chart_datasets(mapping)}
