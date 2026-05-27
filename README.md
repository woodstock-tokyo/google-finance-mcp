# google-finance-mcp

MCP server for Google Finance's internal `batchexecute` RPC endpoint.

The server fetches Google Finance pages such as
`https://www.google.com/finance/beta` or
`https://www.google.com/finance/beta/quote/NVDA:NASDAQ`, extracts
`AF_initDataKeys` and `AF_dataServiceRequests`, and uses each page's cache
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
- `google_finance_refresh_mapping`: force or revalidate a page mapping cache.
- `google_finance_call_dataset`: call any advertised home-page `ds:*` dataset
  by key.
- `google_finance_list_page_rpcs`: return the current mapping for any Google
  Finance page path or URL.
- `google_finance_call_page_dataset`: call any advertised `ds:*` dataset from a
  specific Google Finance page path or URL.
- `google_finance_list_quote_rpcs`: return the quote-page mapping for a ticker
  and exchange. `/finance/quote/...` is also accepted and currently redirects to
  `/finance/beta/quote/...`.
- `google_finance_call_quote_dataset`: call any advertised quote-page `ds:*`
  dataset for a ticker and exchange.
- `google_finance_call_rpc`: call a single RPC ID with an explicit request.
  Explicit RPC calls default to the classic `GoogleFinanceUi` endpoint and can
  opt into `endpoint_family: "finhub"`.
- `google_finance_batch_call`: call multiple RPC IDs in one batchexecute POST.
  Explicit batch calls use the same `endpoint_family` option.
- `google_finance_ds_N_<purpose>`: dynamic tools generated only from the
  current `/finance/beta` home-page mapping, one for each advertised beta
  dataset key. The `ds:N` key is the exported interface identity; the current
  live `id`/hash is read from `AF_dataServiceRequests` whenever the mapping is
  refreshed. Classic and quote-page endpoints are not exposed as generated
  tools; use the page/quote dataset tools or explicit RPC tools for those.

The article's IDs such as `xh8wxf`, `HqGpWd`, and `YtbmEe` are kept only as
reference examples. Calls use the live `id` currently associated with each
`ds:N` entry.

## Generated beta tools

These generated tools are for the Google Finance beta home page only
(`/finance/beta`). The meanings were verified against the live beta page on
2026-05-26. The `id` values below are examples from that run and can change; the
server refreshes them from `AF_dataServiceRequests`.

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

## Quote-page dataset discovery

Classic quote URLs such as `/finance/quote/GOOGL:NASDAQ` are accepted by the
server and currently redirect to `/finance/beta/quote/GOOGL:NASDAQ`. That
redirected quote page advertises `ds:0` through `ds:18`. These are not generated
`google_finance_ds_N_<purpose>` tools; call them with
`google_finance_call_quote_dataset` or `google_finance_call_page_dataset`.

These meanings were discovered from the live quote page and response payloads on
2026-05-27 using `GOOGL:NASDAQ`. The `id` values are examples from that run and
can change.

| Dataset | Example live id | Meaning | Default request shape | Notes |
| --- | --- | --- | --- | --- |
| `ds:0` | `hgueg` | Market overview quotes | `[1]` | Symbol-independent market quote groups. |
| `ds:1` | `vNewwe` | Equity sectors | `[null,[null,1]]` | Sector performance list. |
| `ds:2` | `gCvqoe` | Quote summary | `[[tuple],1]` | Main quote payload for the requested security. |
| `ds:3` | `JL8oKc` | Company profile | `[[tuple]]` | Long company/security profile and descriptive fields. |
| `ds:4` | `SICF5d` | Related securities | `[tuple,4]` | Peer/related quote cards for comparison. |
| `ds:5` | `XxQsbd` | Earnings history and estimates | `[[tuple],1]` | Quarterly rows with actual and estimated revenue/EPS fields. |
| `ds:6` | `dlNq8b` | Security overview card | `[[tuple],1,1,1]` | Price, market cap, industry, logo, and summary quote fields. |
| `ds:7` | `c2u4wc` | Intraday chart points | `[[tuple],1]` | Minute-level price points. |
| `ds:8` | `c2u4wc` | Intraday OHLCV chart | `[[tuple],1,null,null,null,null,null,1]` | Intraday candle rows with open, close, high, low, timestamp, and volume. |
| `ds:9` | `c2u4wc` | One-month chart points | `[[tuple],3]` | Daily price points. |
| `ds:10` | `c2u4wc` | One-month OHLCV chart | `[[tuple],3,null,null,null,null,null,1]` | Daily candle rows with open, close, high, low, timestamp, and volume. |
| `ds:11` | `gXxkFd` | Key statistics / ratios | `[["SYMBOL","EXCHANGE"]]` | Compact numeric ratio vector; individual field labels still need mapping. |
| `ds:12` | `gCvqoe` | Quote summary alternate | `[[tuple]]` | Quote payload without the trailing mode flag. |
| `ds:13` | `Pr8h2e` | Financials / estimates | `[[tuple],null,1]` | Financial statement and estimate arrays. |
| `ds:14` | `kA4MVd` | Market news feed | `[2,12,[tuple]]` | General market or related news list. |
| `ds:15` | `kA4MVd` | Security news feed | `[5,12,[tuple]]` | Company/security-specific article list. |
| `ds:16` | `RiQiSd` | Empty initialization endpoint | `[]` | Observed across equity, ETF, index, crypto, and FX quote pages; returns `[]`. |
| `ds:17` | `X12h2b` | Empty initialization endpoint | `[]` | Observed across equity, ETF, index, crypto, and FX quote pages; returns `[]`. |
| `ds:18` | `vNewwe` | Equity sectors metadata | `[]` | Empty request that returns sector metadata. |

`ds:16` and `ds:17` were specifically crawled across quote pages including
`GOOGL:NASDAQ`, `NVDA:NASDAQ`, `SPY:NYSEARCA`, `.INX:INDEXSP`,
`BTC-USD:CCY`, and `EUR-USD:CCY`. In each case the page advertised the same
request shape, `[]`, and batchexecute returned an empty data array. Market,
search, portfolio, and watchlist routes redirected to the beta home page and did
not expose `ds:16` or `ds:17`.

## Endpoint handling

Classic explicit RPC calls use:

```text
https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute
```

Current beta pages advertise the FinHubUi endpoint, and dataset calls use the
endpoint associated with the page mapping:

```text
https://www.google.com/finance/beta/_/FinHubUi/data/batchexecute
```

Generated `google_finance_ds_N_<purpose>` tools are intentionally limited to the
beta home page. Other pages, including quote pages or classic `/finance/...`
paths, can still be inspected with `google_finance_list_page_rpcs` or
`google_finance_list_quote_rpcs` and called with
`google_finance_call_page_dataset`, `google_finance_call_quote_dataset`,
`google_finance_call_rpc`, or `google_finance_batch_call`.

The request body is a URL-encoded `f.req` value containing batched RPC calls.
Responses are Google batchexecute frames; the server strips the anti-JSON prefix,
decodes `wrb.fr` frames, and returns structured JSON.

Generic `google_finance_call_rpc` and `google_finance_batch_call` accept an
explicit `source_path` plus `endpoint_family: "classic" | "finhub"`. Dataset
calls use the fetched page path and endpoint by default, so the home page and
quote pages can both define `ds:0`, `ds:1`, and so on without sharing meaning.

## Run

```bash
uv pip install -e ".[dev]"
google-finance-mcp
```

By default the server uses MCP stdio transport.
