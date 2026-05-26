from __future__ import annotations

import json
import re
from typing import Any

import anyio
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from .client import GoogleFinanceClient
from .rpc_metadata import ARTICLE_REFERENCE_RPC_PURPOSES, EndpointMetadata

JSONValue = Any

client = GoogleFinanceClient()
server = Server(
    "google-finance-mcp",
    version="0.1.0",
    instructions=(
        "Fetches Google Finance beta page RPC mappings from AF_initDataKeys and "
        "AF_dataServiceRequests, honors the page cache headers, and calls the "
        "Google Finance batchexecute RPC endpoint."
    ),
)


def _schema(properties: dict[str, JSONValue], required: list[str] | None = None) -> dict[str, JSONValue]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


ANY_JSON_SCHEMA: dict[str, JSONValue] = {
    "description": "Any JSON value accepted by Google Finance for this RPC request.",
}

SOURCE_FIELDS: dict[str, JSONValue] = {
    "source_path": {
        "type": "string",
        "default": "/finance/beta",
        "description": "Google Finance page path used in the batchexecute source-path query parameter.",
    },
    "hl": {"type": "string", "default": "en"},
    "gl": {"type": "string", "default": "us"},
}


GENERIC_TOOLS = [
    Tool(
        name="google_finance_refresh_mapping",
        description="Refresh or revalidate the Google Finance AF_dataServiceRequests mapping.",
        inputSchema=_schema(
            {
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Fetch the beta page even if the current cache entry is still fresh.",
                }
            }
        ),
    ),
    Tool(
        name="google_finance_list_rpcs",
        description=(
            "List the current Google Finance beta AF_initDataKeys and AF_dataServiceRequests "
            "mapping, enriched with RPC purpose metadata where known."
        ),
        inputSchema=_schema({}),
    ),
    Tool(
        name="google_finance_list_known_rpc_purposes",
        description=(
            "List the reference RPC ID to purpose mapping from the reverse-engineering article. "
            "These IDs are examples only; live calls use the current id from AF_dataServiceRequests."
        ),
        inputSchema=_schema({}),
    ),
    Tool(
        name="google_finance_call_dataset",
        description="Call any Google Finance dataset key advertised by AF_dataServiceRequests.",
        inputSchema=_schema(
            {
                "dataset_key": {
                    "type": "string",
                    "description": "Dataset key such as ds:0.",
                },
                "request_override": ANY_JSON_SCHEMA,
                **SOURCE_FIELDS,
            },
            required=["dataset_key"],
        ),
    ),
    Tool(
        name="google_finance_call_rpc",
        description="Call a Google Finance RPC ID with an explicit JSON request payload.",
        inputSchema=_schema(
            {
                "rpc_id": {"type": "string", "description": "RPC ID such as YtbmEe."},
                "request": ANY_JSON_SCHEMA,
                **SOURCE_FIELDS,
            },
            required=["rpc_id", "request"],
        ),
    ),
    Tool(
        name="google_finance_batch_call",
        description="Call multiple Google Finance RPCs in one batchexecute request.",
        inputSchema=_schema(
            {
                "requests": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "request": ANY_JSON_SCHEMA,
                        },
                        "required": ["id", "request"],
                        "additionalProperties": False,
                    },
                },
                **SOURCE_FIELDS,
            },
            required=["requests"],
        ),
    ),
]


def dataset_tool_name(dataset_key: str, metadata: EndpointMetadata | None = None) -> str:
    ds_suffix = re.sub(r"[^A-Za-z0-9_-]+", "_", dataset_key).strip("_").lower()
    if metadata is None:
        return f"google_finance_{ds_suffix}"
    if metadata.source == "live-af_dataServiceRequests":
        return f"google_finance_{ds_suffix}"
    return f"google_finance_{ds_suffix}_{metadata.slug}"


def dataset_key_from_tool_name(tool_name: str) -> str | None:
    match = re.fullmatch(r"google_finance_ds_(\d+)(?:_[a-z0-9_]+)?", tool_name)
    if not match:
        return None
    return f"ds:{match.group(1)}"


def _dynamic_tool(dataset_key: str, rpc_id: str, request: JSONValue, metadata: EndpointMetadata) -> Tool:
    return Tool(
        name=dataset_tool_name(dataset_key, metadata),
        description=(
            f"Call Google Finance {metadata.purpose} endpoint {dataset_key}. "
            f"The current live id/hash from AF_dataServiceRequests is {rpc_id}. "
            f"Request shape: {metadata.request_shape}. "
            f"Default request: {json.dumps(request, separators=(',', ':'))}"
        ),
        inputSchema=_schema({"request_override": ANY_JSON_SCHEMA, **SOURCE_FIELDS}),
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    mapping = await client.get_mapping()
    dynamic_tools = [
        _dynamic_tool(dataset_key, request.rpc_id, request.request, request.metadata)
        for dataset_key, request in sorted(mapping.requests.items())
    ]
    return [*GENERIC_TOOLS, *dynamic_tools]


@server.call_tool(validate_input=True)
async def call_tool(name: str, arguments: dict[str, JSONValue]) -> dict[str, JSONValue]:
    if name == "google_finance_refresh_mapping":
        mapping = await client.get_mapping(force_refresh=bool(arguments.get("force", False)))
        return mapping.as_dict()

    if name == "google_finance_list_rpcs":
        mapping = await client.get_mapping()
        return mapping.as_dict()

    if name == "google_finance_list_known_rpc_purposes":
        return {"rpcs": ARTICLE_REFERENCE_RPC_PURPOSES}

    if name == "google_finance_call_dataset":
        return await client.call_dataset(
            str(arguments["dataset_key"]),
            arguments.get("request_override"),
            source_path=str(arguments.get("source_path", "/finance/beta")),
            hl=str(arguments.get("hl", "en")),
            gl=str(arguments.get("gl", "us")),
        )

    if name == "google_finance_call_rpc":
        return await client.call_rpc(
            str(arguments["rpc_id"]),
            arguments["request"],
            source_path=str(arguments.get("source_path", "/finance/beta")),
            hl=str(arguments.get("hl", "en")),
            gl=str(arguments.get("gl", "us")),
        )

    if name == "google_finance_batch_call":
        return {
            "results": await client.batch_call(
                list(arguments["requests"]),
                source_path=str(arguments.get("source_path", "/finance/beta")),
                hl=str(arguments.get("hl", "en")),
                gl=str(arguments.get("gl", "us")),
            )
        }

    dataset_key = dataset_key_from_tool_name(name)
    if dataset_key:
        return await client.call_dataset(
            dataset_key,
            arguments.get("request_override"),
            source_path=str(arguments.get("source_path", "/finance/beta")),
            hl=str(arguments.get("hl", "en")),
            gl=str(arguments.get("gl", "us")),
        )

    raise KeyError(f"Unknown tool: {name}")


async def serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(NotificationOptions(tools_changed=True)),
        )


def main() -> None:
    anyio.run(serve)
