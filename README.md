# google-finance-mcp

MCP server for Google Finance's internal `batchexecute` RPC endpoint.

The server first fetches `https://www.google.com/finance/beta`, extracts
`AF_initDataKeys` and `AF_dataServiceRequests`, and uses the page's cache
headers to decide when the internal RPC mapping must be refreshed.

## Mapping model

Google Finance embeds dataset entries like this in the beta page:

```js
var AF_initDataKeys = ["ds:0", "ds:1", "..."];
var AF_dataServiceRequests = {
  "ds:1": {id: "vNewwe", request: [null, [null, 1]]}
};
```

This server treats the `ds:N` key as the exported interface identity. The
`id` field is the current live method token/hash used in the `batchexecute`
POST body, and it may change over time. Do not build clients against a hardcoded
`id`; call by `ds:N` or by the generated `google_finance_ds_N_<purpose>` tool.

## Tools

- `google_finance_list_rpcs`: return the current `AF_initDataKeys` and
  `AF_dataServiceRequests` mapping, enriched with inferred purpose metadata.
- `google_finance_list_known_rpc_purposes`: return the article's reference RPC
  ID to purpose table. These IDs are not treated as stable.
- `google_finance_refresh_mapping`: force or revalidate the mapping cache.
- `google_finance_call_dataset`: call any advertised `ds:*` dataset by key.
- `google_finance_call_rpc`: call a single RPC ID with an explicit request.
- `google_finance_batch_call`: call multiple RPC IDs in one batchexecute POST.
- `google_finance_ds_N_<purpose>`: dynamic tools generated from the current
  mapping, one for each advertised dataset key. The `ds:N` key is the exported
  interface identity; the current live `id`/hash is read from
  `AF_dataServiceRequests` whenever the mapping is refreshed.

The article's IDs such as `xh8wxf`, `HqGpWd`, and `YtbmEe` are kept only as
reference examples. Calls use the live `id` currently associated with each
`ds:N` entry.

## Current beta endpoints

These meanings were verified against the live beta page on 2026-05-26. The
`id` values below are examples from that run and can change; the server refreshes
them from `AF_dataServiceRequests`.

| Dataset | Example live id | Generated tool | Meaning | Default request |
| --- | --- | --- | --- | --- |
| `ds:0` | `hgueg` | `google_finance_ds_0_market_overview_quotes` | Market overview quotes | `[1]` |
| `ds:1` | `vNewwe` | `google_finance_ds_1_equity_sectors` | Equity sectors | `[null,[null,1]]` |
| `ds:2` | `RmdyKd` | `google_finance_ds_2_earnings_calendar` | Earnings calendar | `[1,0,2]` |
| `ds:3` | `RmdyKd` | `google_finance_ds_3_earnings_calendar_secondary` | Earnings calendar secondary, currently empty | `[3,1]` |
| `ds:4` | `hgueg` | `google_finance_ds_4_market_overview_charts` | Market overview charts with SVG sparklines | `[0]` |
| `ds:5` | `HacE5d` | `google_finance_ds_5_market_summary_news_clusters` | Market summary news clusters | `["market_summary",1]` |
| `ds:6` | `MlXU3e` | `google_finance_ds_6_top_finance_articles` | Top finance articles | `[8]` |
| `ds:7` | `kA4MVd` | `google_finance_ds_7_market_news` | Market news | `[2,20]` |
| `ds:8` | `YtbmEe` | `google_finance_ds_8_market_movers` | Market movers | `[[2,3,1],4,0]` |
| `ds:9` | `RiQiSd` | `google_finance_ds_9_empty_initialization_endpoint` | Empty initialization endpoint | `[]` |
| `ds:10` | `X12h2b` | `google_finance_ds_10_empty_initialization_endpoint` | Empty initialization endpoint | `[]` |
| `ds:11` | `vNewwe` | `google_finance_ds_11_equity_sectors_metadata` | Equity sectors metadata | `[]` |

## Response handling

All calls go through:

```text
https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute
```

The request body is a URL-encoded `f.req` value containing batched RPC calls.
Responses are Google batchexecute frames; the server strips the anti-JSON prefix,
decodes `wrb.fr` frames, and returns structured JSON.

## Run

```bash
uv pip install -e ".[dev]"
google-finance-mcp
```

By default the server uses MCP stdio transport.
