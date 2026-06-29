from __future__ import annotations

from datetime import datetime, timezone

import pytest

from google_finance_mcp.client import (
    ApiMapping,
    BATCHEXECUTE_URL,
    CLASSIC_BATCHEXECUTE_URL,
    CachePolicy,
    DataServiceRequest,
    FINHUB_BATCHEXECUTE_URL,
    GoogleFinanceClient,
    build_body,
    cache_policy_from_headers,
    parse_batchexecute_response,
    parse_mapping_from_html,
)
from google_finance_mcp.key_statistics import enrich_key_statistics_result
from google_finance_mcp.rpc_metadata import metadata_for_dataset

UTC = timezone.utc


def test_parse_mapping_from_google_finance_html() -> None:
    html = """
    <script>var AF_initDataKeys = ["ds:0","ds:1"];
    var AF_dataServiceRequests = {'ds:0' : {id:'hgueg',request:[1]},
    'ds:1' : {id:'vNewwe',request:[null,[null,1]]}};
    var AF_initDataChunkQueue = [];</script>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta",
        {"cache-control": "max-age=60", "date": "Tue, 26 May 2026 08:13:05 GMT"},
    )

    assert mapping.init_data_keys == ["ds:0", "ds:1"]
    assert mapping.source_path == "/finance/beta"
    assert mapping.batchexecute_url == FINHUB_BATCHEXECUTE_URL
    assert BATCHEXECUTE_URL == CLASSIC_BATCHEXECUTE_URL
    assert mapping.requests["ds:0"].rpc_id == "hgueg"
    assert mapping.requests["ds:0"].metadata.purpose == "Market overview quotes"
    assert mapping.requests["ds:1"].metadata.purpose == "Equity sectors"
    assert mapping.requests["ds:1"].request == [None, [None, 1]]
    assert mapping.cache_policy.max_age_seconds == 60


def test_parse_mapping_infers_purpose_without_stable_rpc_id() -> None:
    html = """
    <script>var AF_initDataKeys = ["ds:8"];
    var AF_dataServiceRequests = {'ds:8' : {id:'changedHash',request:[[1],6,0]}};
    var AF_initDataChunkQueue = [];</script>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta",
        {"cache-control": "max-age=60"},
    )

    assert mapping.requests["ds:8"].metadata.purpose == "Market movers"
    assert mapping.requests["ds:8"].metadata.current_rpc_id == "changedHash"
    assert mapping.requests["ds:8"].metadata.request_shape == "[[categories], count, offset]"


def test_runtime_beta_dataset_hint_covers_top_finance_articles() -> None:
    html = """
    <script>var AF_initDataKeys = ["ds:6"];
    var AF_dataServiceRequests = {'ds:6' : {id:'MlXU3e',request:[8]}};
    var AF_initDataChunkQueue = [];</script>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta",
        {"cache-control": "max-age=60"},
    )

    assert mapping.requests["ds:6"].metadata.purpose == "Top finance articles"
    assert mapping.requests["ds:6"].metadata.slug == "top_finance_articles"
    assert mapping.requests["ds:6"].metadata.source == "runtime-compiled-beta-dataset-key"


def test_quote_page_mapping_uses_quote_metadata() -> None:
    html = """
    <html><head><script nonce="abc">var AF_initDataKeys = ["ds:2","ds:3"];
    var AF_dataServiceRequests = {'ds:2' : {id:'gCvqoe',request:[[[null,["NVDA","NASDAQ"]]],1]},
    'ds:3' : {id:'JL8oKc',request:[[[null,["NVDA","NASDAQ"]]]]}};
    var AF_initDataChunkQueue = [];</script></head><body>FinHubUi</body></html>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta/quote/NVDA:NASDAQ",
        {"cache-control": "max-age=60"},
    )

    assert mapping.source_path == "/finance/beta/quote/NVDA:NASDAQ"
    assert mapping.requests["ds:2"].metadata.purpose == "Quote summary"
    assert mapping.requests["ds:2"].metadata.source == "runtime-compiled-rpc-id"
    assert mapping.requests["ds:2"].metadata.description == "Main quote payload for the requested security."
    assert mapping.requests["ds:3"].metadata.purpose == "Company profile"
    assert mapping.requests["ds:3"].metadata.description == "Long company/security profile and descriptive fields."


def test_quote_page_mapping_matches_current_shifted_dataset_keys() -> None:
    html = """
    <html><head><script nonce="abc">var AF_initDataKeys = ["ds:5","ds:16","ds:19","ds:20"];
    var AF_dataServiceRequests = {'ds:5' : {id:'YTM9q',request:[[null,["NVDA","NASDAQ"]]]},
    'ds:16' : {id:'Pr8h2e',request:[[[null,["NVDA","NASDAQ"]]],null,1]},
    'ds:19' : {id:'RiQiSd',request:[null,null,25]},
    'ds:20' : {id:'X12h2b',request:[]}};
    var AF_initDataChunkQueue = [];</script></head><body>FinHubUi</body></html>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta/quote/NVDA:NASDAQ",
        {"cache-control": "max-age=60"},
    )

    assert mapping.requests["ds:5"].metadata.purpose == "Analyst ratings and price targets"
    assert mapping.requests["ds:16"].metadata.purpose == "Financials / estimates"
    assert mapping.requests["ds:19"].metadata.purpose == "Empty initialization endpoint"
    assert mapping.requests["ds:19"].metadata.request_shape == "[null, null, 25]"
    assert mapping.requests["ds:20"].metadata.purpose == "Empty initialization endpoint"


def test_runtime_rpc_metadata_overrides_shifted_dataset_hint() -> None:
    html = """
    <html><head><script nonce="abc">var AF_initDataKeys = ["ds:2"];
    var AF_dataServiceRequests = {'ds:2' : {id:'Kcy68c',request:[[[null,["NVDA","NASDAQ"]]],1]}};
    var AF_initDataChunkQueue = [];</script></head><body>FinHubUi</body></html>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta/quote/NVDA:NASDAQ",
        {"cache-control": "max-age=60"},
    )

    assert mapping.requests["ds:2"].metadata.purpose == "Earnings history and estimates"
    assert mapping.requests["ds:2"].metadata.source == "runtime-compiled-rpc-id"
    assert "Live RPC id Kcy68c" in mapping.requests["ds:2"].metadata.justification[0]


def test_runtime_dataset_hint_survives_method_id_change_when_shape_still_matches() -> None:
    html = """
    <html><head><script nonce="abc">var AF_initDataKeys = ["ds:2"];
    var AF_dataServiceRequests = {'ds:2' : {id:'newQuoteId',request:[[[null,["NVDA","NASDAQ"]]],1]}};
    var AF_initDataChunkQueue = [];</script></head><body>FinHubUi</body></html>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/beta/quote/NVDA:NASDAQ",
        {"cache-control": "max-age=60"},
    )

    assert mapping.requests["ds:2"].metadata.purpose == "Quote summary"
    assert mapping.requests["ds:2"].metadata.source == "runtime-compiled-quote-dataset-key"
    assert "Live request matches [[tuple], 1]." in mapping.requests["ds:2"].metadata.justification


def test_classic_page_mapping_uses_google_finance_ui_endpoint() -> None:
    html = """
    <script>var AF_initDataKeys = ["ds:0"];
    var AF_dataServiceRequests = {'ds:0' : {id:'xh8wxf',request:[[[null,["GOOGL","NASDAQ"]]],1]}};
    var AF_initDataChunkQueue = [];</script>
    """

    mapping = parse_mapping_from_html(
        html,
        "https://www.google.com/finance/quote/GOOGL:NASDAQ",
        {"cache-control": "max-age=60"},
    )

    assert mapping.source_path == "/finance/quote/GOOGL:NASDAQ"
    assert mapping.batchexecute_url == CLASSIC_BATCHEXECUTE_URL


def test_no_cache_headers_expire_immediately() -> None:
    policy = cache_policy_from_headers(
        {
            "cache-control": "no-cache, no-store, max-age=0, must-revalidate",
            "date": "Tue, 26 May 2026 08:13:05 GMT",
        }
    )

    assert policy.fetched_at == datetime(2026, 5, 26, 8, 13, 5, tzinfo=UTC)
    assert policy.expires_at == policy.fetched_at
    assert policy.max_age_seconds == 0


def test_build_body_matches_batchexecute_shape() -> None:
    body = build_body([{"id": "abc", "request": [[None, ["GOOGL", "NASDAQ"]], 1]}])

    assert body.startswith("f.req=")
    assert "%22abc%22" in body
    assert "GOOGL" in body


def test_parse_batchexecute_response() -> None:
    raw = """)]}'

123
[["wrb.fr","xh8wxf","[[[\\"quote\\"]]]",null,null,null,"1"]]
"""

    assert parse_batchexecute_response(raw) == [{"id": "xh8wxf", "data": [[["quote"]]]}]


def test_enrich_key_statistics_result_labels_raw_vector() -> None:
    result = {
        "id": "gXxkFd",
        "data": [None, None, [["UUUU", "NYSEAMERICAN"], 0.625, 0.3125, 0.0625, 56.25, 0.4832, 0.3921, 0.1247, 35.85, 4.5, 11, 1.6842105263157894]],
    }

    enriched = enrich_key_statistics_result(result)

    assert enriched["data"] is result["data"]
    labeled = enriched["labeled_data"]
    assert labeled["confidence"] == "best_effort"
    assert labeled["rows"][0]["symbol"] == "UUUU"
    assert labeled["rows"][0]["exchange"] == "NYSEAMERICAN"
    assert labeled["rows"][0]["values"]["primary_bucket_1_ratio"] == 0.625
    assert labeled["rows"][0]["groups"]["primary_distribution"]["bucket_ratio_sum"] == 1.0
    assert labeled["rows"][0]["raw_fields"][4]["raw_index"] == 4


@pytest.mark.anyio
async def test_call_dataset_refreshes_mapping_when_cached_rpc_returns_no_frame() -> None:
    def mapping_for(rpc_id: str) -> ApiMapping:
        request = [1]
        return ApiMapping(
            source_url="https://www.google.com/finance/beta",
            source_path="/finance/beta",
            batchexecute_url=FINHUB_BATCHEXECUTE_URL,
            init_data_keys=["ds:0"],
            requests={
                "ds:0": DataServiceRequest(
                    key="ds:0",
                    rpc_id=rpc_id,
                    request=request,
                    metadata=metadata_for_dataset("ds:0", rpc_id, request),
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

    class RepairingClient(GoogleFinanceClient):
        def __init__(self) -> None:
            self.rpc_ids: list[str] = []

        async def get_mapping(self, *, page_path: str = "/finance/beta", force_refresh: bool = False) -> ApiMapping:
            return mapping_for("newRpc") if force_refresh else mapping_for("oldRpc")

        async def batch_call(self, requests, **kwargs):
            rpc_id = requests[0]["id"]
            self.rpc_ids.append(rpc_id)
            if rpc_id == "oldRpc":
                return []
            return [{"id": rpc_id, "data": [["ok"]]}]

    client = RepairingClient()

    result = await client.call_dataset("ds:0")

    assert result == {"id": "newRpc", "data": [["ok"]]}
    assert client.rpc_ids == ["oldRpc", "newRpc"]
