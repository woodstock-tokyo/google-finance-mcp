from __future__ import annotations

from datetime import UTC, datetime

import pytest

from google_finance_mcp.client import ApiMapping, CachePolicy, DataServiceRequest
from google_finance_mcp.rpc_metadata import metadata_for_dataset
from google_finance_mcp import server


class FakeClient:
    async def get_mapping(self, *, page_path: str = "/finance/beta", force_refresh: bool = False) -> ApiMapping:
        return ApiMapping(
            source_url="https://www.google.com/finance/beta",
            source_path="/finance/beta",
            batchexecute_url="https://www.google.com/finance/beta/_/FinHubUi/data/batchexecute",
            init_data_keys=["ds:8"],
            requests={
                "ds:8": DataServiceRequest(
                    key="ds:8",
                    rpc_id="changedHash",
                    request=[[1], 6, 0],
                    metadata=metadata_for_dataset("ds:8", "changedHash", [[1], 6, 0]),
                )
            },
            cache_policy=CachePolicy(
                cache_control="max-age=60",
                expires=None,
                date=None,
                fetched_at=datetime(2026, 5, 26, tzinfo=UTC),
                expires_at=datetime(2026, 5, 26, 0, 1, tzinfo=UTC),
            ),
        )

    async def call_dataset(self, dataset_key: str, request_override=None, **kwargs):
        return {"dataset_key": dataset_key, "request_override": request_override}


@pytest.mark.anyio
async def test_dynamic_tool_uses_rpc_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "client", FakeClient())

    tools = await server.list_tools()
    names = [tool.name for tool in tools]

    assert "google_finance_ds_8_market_movers" in names
    tool = next(tool for tool in tools if tool.name == "google_finance_ds_8_market_movers")
    assert "Market movers" in tool.description
    assert "changedHash" in tool.description


@pytest.mark.anyio
async def test_dynamic_purpose_tool_calls_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "client", FakeClient())

    result = await server.call_tool("google_finance_ds_8_market_movers", {})

    assert result == {"dataset_key": "ds:8", "request_override": None}


@pytest.mark.anyio
async def test_quote_dataset_tool_uses_quote_page_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class RecordingClient:
        async def call_dataset(self, dataset_key: str, request_override=None, **kwargs):
            return {"dataset_key": dataset_key, "request_override": request_override, "kwargs": kwargs}

    monkeypatch.setattr(server, "client", RecordingClient())

    result = await server.call_tool(
        "google_finance_call_quote_dataset",
        {"symbol": "nvda", "exchange": "nasdaq", "dataset_key": "ds:12"},
    )

    assert result["dataset_key"] == "ds:12"
    assert result["kwargs"]["page_path"] == "/finance/beta/quote/NVDA:NASDAQ"
    assert result["kwargs"]["source_path"] is None


@pytest.mark.anyio
async def test_call_rpc_defaults_to_classic_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    class RecordingClient:
        async def call_rpc(self, rpc_id: str, request, **kwargs):
            return {"rpc_id": rpc_id, "request": request, "kwargs": kwargs}

    monkeypatch.setattr(server, "client", RecordingClient())

    result = await server.call_tool("google_finance_call_rpc", {"rpc_id": "xh8wxf", "request": [[[None, ["GOOGL", "NASDAQ"]]], 1]})

    assert result["kwargs"]["batchexecute_url"].endswith("/finance/_/GoogleFinanceUi/data/batchexecute")


@pytest.mark.anyio
async def test_call_rpc_can_use_finhub_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    class RecordingClient:
        async def call_rpc(self, rpc_id: str, request, **kwargs):
            return {"rpc_id": rpc_id, "request": request, "kwargs": kwargs}

    monkeypatch.setattr(server, "client", RecordingClient())

    result = await server.call_tool(
        "google_finance_call_rpc",
        {"rpc_id": "gCvqoe", "request": [[[None, ["NVDA", "NASDAQ"]]], 1], "endpoint_family": "finhub"},
    )

    assert result["kwargs"]["batchexecute_url"].endswith("/finance/beta/_/FinHubUi/data/batchexecute")
