from __future__ import annotations

from datetime import UTC, datetime

from google_finance_mcp.client import (
    build_body,
    cache_policy_from_headers,
    parse_batchexecute_response,
    parse_mapping_from_html,
)


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
