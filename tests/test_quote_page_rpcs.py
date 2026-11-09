from __future__ import annotations

import json

import pytest

from google_finance_mcp import server
from google_finance_mcp.client import (
    GoogleFinanceClient,
    MappingParseError,
    parse_mapping_from_html,
)
from google_finance_mcp.quote_page_rpcs import (
    CHART_MODES,
    HOME_ENDPOINTS,
    QUOTE_ENDPOINTS,
    QuoteDatasetUnavailable,
    call_page_endpoint,
    chart_datasets,
    detect_quote_rpcs_for_symbol,
    quote_page_path,
    select_dataset,
)

TUPLE = [None, ["AAPL", "NASDAQ"]]
PAGE = "/finance/beta/quote/AAPL:NASDAQ"


def mapping_for(entries, page_path=PAGE):
    html = (f"var AF_initDataKeys = {json.dumps(list(entries))};"
            f"var AF_dataServiceRequests = {json.dumps(entries)};")
    return parse_mapping_from_html(html, f"https://www.google.com{page_path}", {"cache-control": "max-age=60"})


class RecordingClient(GoogleFinanceClient):
    def __init__(self, mapping):
        super().__init__()
        self.mapping = mapping
        self.refreshes = []
        self.calls = []

    async def get_mapping(self, *, page_path=PAGE, force_refresh=False):
        self.refreshes.append((page_path, force_refresh))
        return self.mapping

    async def batch_call(self, requests, **kwargs):
        self.calls.append((requests, kwargs))
        return [{"id": requests[0]["id"], "data": ["raw"]}]


@pytest.mark.anyio
@pytest.mark.parametrize(("endpoint", "rpc_id", "payload"), [
    ("quote_summary", "gCvqoe", [[TUPLE], 1]),
    ("company_profile", "JL8oKc", [[TUPLE]]),
    ("key_statistics", "gXxkFd", [["AAPL", "NASDAQ"]]),
    ("related_securities", "SICF5d", [TUPLE, 4]),
    ("analyst_ratings", "YTM9q", [TUPLE]),
    ("analyst_ratings", "lXoEXd", [TUPLE]),
    ("earnings_history_alts", "XxQsbd", [[TUPLE], 1]),
    ("security_overview_alt", "dlNq8b", [[TUPLE], 1, 1, 1]),
    ("security_news_feed", "kA4MVd", [5, 24, [TUPLE]]),
    ("security_news_feed", "wdVNWe", [5, 12, [TUPLE]]),
    ("financials", "Pr8h2e", [[TUPLE], None, 1]),
])
async def test_semantic_quote_tools_use_live_requests(monkeypatch, endpoint, rpc_id, payload):
    # Deliberately use a ds key absent from both the report and built-in hints.
    client = RecordingClient(mapping_for({"ds:77": {"id": rpc_id, "request": payload}}))
    monkeypatch.setattr(server, "client", client)
    result = await server.call_tool(f"google_finance_{endpoint}", {
        "symbol": "aapl", "exchange": "nasdaq", "hl": "zh-TW", "gl": "tw",
    })
    assert result["id"] == rpc_id
    sent, kwargs = client.calls[0]
    assert sent == [{"id": rpc_id, "request": payload}]
    assert kwargs["source_path"] == PAGE
    assert "FinHubUi" in kwargs["batchexecute_url"]
    assert kwargs["hl"] == "zh-TW"
    assert kwargs["gl"] == "tw"


@pytest.mark.anyio
async def test_rotated_id_uses_live_dataset_hint_and_override():
    client = RecordingClient(mapping_for({"ds:4": {"id": "rotatedProfile", "request": [[TUPLE]]}}))
    result = await call_page_endpoint(client, "company_profile", page_path=PAGE, request_override=[])
    assert result["id"] == "rotatedProfile"
    assert client.calls[0][0] == [{"id": "rotatedProfile", "request": []}]


@pytest.mark.anyio
async def test_unavailable_endpoint_refreshes_without_guessing():
    client = RecordingClient(mapping_for({"ds:19": {"id": "stRW5d", "request": []}}))
    with pytest.raises(QuoteDatasetUnavailable, match="No advertised dataset for earnings_calendar"):
        await call_page_endpoint(client, "earnings_calendar", page_path=PAGE)
    assert client.refreshes == [(PAGE, False), (PAGE, True)]
    assert not client.calls


@pytest.mark.anyio
@pytest.mark.parametrize(("endpoint", "rpc_id", "payload"), [
    ("earnings_calendar", "JFUMjd", []),
    ("featured_stocks", "mysBRb", []),
    ("category_news", "sy8gqe", [3, 0]),
    ("market_news_feed", "kA4MVd", [2, 12, [TUPLE]]),
])
async def test_home_endpoint_tools(monkeypatch, endpoint, rpc_id, payload):
    client = RecordingClient(mapping_for({"ds:60": {"id": rpc_id, "request": payload}}, "/finance/beta"))
    monkeypatch.setattr(server, "client", client)
    result = await server.call_tool(f"google_finance_{endpoint}", {})
    assert result["id"] == rpc_id
    assert client.calls[0][0][0]["request"] == payload
    assert client.calls[0][1]["source_path"] == "/finance/beta"


@pytest.mark.anyio
async def test_chart_enumeration_and_ohlcv_dispatch(monkeypatch):
    points = [[TUPLE], 3]
    candles = [[TUPLE], 1, None, None, None, None, None, 1]
    client = RecordingClient(mapping_for({
        "ds:70": {"id": "c2u4wc", "request": points},
        "ds:71": {"id": "c2u4wc", "request": candles},
        "ds:72": {"id": "c2u4wc", "request": [[TUPLE], 52]},
    }))
    monkeypatch.setattr(server, "client", client)
    charts = chart_datasets(client.mapping)
    assert [(chart["interval"], chart["kind"]) for chart in charts] == [
        ("1m", "points"), ("1d", "ohlcv"), (None, "points"),
    ]
    await server.call_tool("google_finance_intraday_chart", {"symbol": "AAPL", "exchange": "NASDAQ"})
    assert client.calls[0][0][0]["request"] == candles
    await server.call_tool("google_finance_1m_chart", {"symbol": "AAPL", "exchange": "NASDAQ"})
    assert client.calls[1][0][0]["request"] == points
    with pytest.raises(QuoteDatasetUnavailable):
        await server.call_tool("google_finance_5y_chart", {"symbol": "AAPL", "exchange": "NASDAQ"})
    assert len(client.calls) == 2
    enumeration = await server.call_tool("google_finance_enumerate_chart_intervals", {"symbol": "AAPL", "exchange": "NASDAQ"})
    assert enumeration["chart_intervals"] == charts


@pytest.mark.anyio
async def test_discovery_exposes_missing_endpoints_and_dataset_keys():
    client = RecordingClient(mapping_for({"ds:77": {"id": "JL8oKc", "request": [[TUPLE]]}}))
    result = await detect_quote_rpcs_for_symbol(client, "AAPL", "NASDAQ")
    assert result["init_data_keys"] == ["ds:77"]
    assert result["endpoints"]["company_profile"]["key"] == "ds:77"
    assert result["endpoints"]["analyst_ratings"] is None


@pytest.mark.anyio
@pytest.mark.parametrize("interval", list(CHART_MODES))
@pytest.mark.parametrize("kind", ["points", "ohlcv"])
async def test_range_tools_preserve_advertised_mode_and_candle_flags(monkeypatch, interval, kind):
    payload = [[TUPLE], CHART_MODES[interval]]
    if kind == "ohlcv":
        payload.extend([None] * 5 + [1])
    client = RecordingClient(mapping_for({"ds:70": {"id": "c2u4wc", "request": payload}}))
    monkeypatch.setattr(server, "client", client)
    await server.call_tool(f"google_finance_{interval}_chart", {
        "symbol": "AAPL", "exchange": "NASDAQ", "kind": kind,
    })
    assert client.calls[0][0][0]["request"] == payload


@pytest.mark.anyio
async def test_missing_dataset_can_appear_after_refresh():
    stale = mapping_for({})
    fresh = mapping_for({"ds:77": {"id": "JL8oKc", "request": [[TUPLE]]}})

    class RefreshingClient(RecordingClient):
        async def get_mapping(self, *, page_path=PAGE, force_refresh=False):
            if force_refresh:
                self.mapping = fresh
            return self.mapping

    client = RefreshingClient(stale)
    result = await call_page_endpoint(client, "company_profile", page_path=PAGE)
    assert result["id"] == "JL8oKc"


@pytest.mark.anyio
@pytest.mark.parametrize("data", [None, [], [1]])
async def test_diagnostic_distinguishes_empty_data_from_missing_frames(monkeypatch, data):
    class Client:
        async def batch_call(self, requests, **kwargs):
            return [{"id": "test", "data": data}]
    monkeypatch.setattr(server, "client", Client())
    result = await server.call_tool("google_finance_test_rpc", {"rpc_id": "test", "request": []})
    assert result["frame_received"] is True
    assert result["results"][0]["data"] == data


@pytest.mark.anyio
async def test_missing_rpc_frame_diagnostic_and_client_error(monkeypatch):
    class Client(GoogleFinanceClient):
        async def batch_call(self, requests, **kwargs):
            return []
    client = Client()
    monkeypatch.setattr(server, "client", client)
    result = await server.call_tool("google_finance_test_rpc", {"rpc_id": "test", "request": []})
    assert result == {"rpc_id": "test", "frame_received": False, "results": []}
    with pytest.raises(MappingParseError, match="no batchexecute frame for RPC test"):
        await client.call_rpc("test", [])


@pytest.mark.anyio
async def test_new_tools_have_unique_names_and_quote_input_schemas(monkeypatch):
    monkeypatch.setattr(server, "client", RecordingClient(mapping_for({})))
    tools = await server.list_tools()
    names = [tool.name for tool in tools]
    assert len(names) == len(set(names))
    for endpoint in QUOTE_ENDPOINTS:
        tool = next(tool for tool in tools if tool.name == f"google_finance_{endpoint}")
        assert tool.inputSchema["required"] == ["symbol", "exchange"]
    for endpoint in HOME_ENDPOINTS:
        assert f"google_finance_{endpoint}" in names


def test_invalid_chart_selector_and_ticker():
    with pytest.raises(ValueError, match="Unknown chart interval"):
        select_dataset(mapping_for({}), "chart", interval="bogus")
    with pytest.raises(ValueError, match="Unknown chart kind"):
        select_dataset(mapping_for({}), "chart", kind="bogus")
    with pytest.raises(ValueError, match="nonempty ticker components"):
        quote_page_path("AAPL/NASDAQ", "NASDAQ")
    assert quote_page_path("btc", "usd", beta=False) == "/finance/quote/BTC:USD"
