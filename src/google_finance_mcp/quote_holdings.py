from __future__ import annotations

from typing import Any

JSONValue = Any

QUOTE_HOLDINGS_RPC_ID = "K5Y6Xb"
QUOTE_HOLDINGS_SCHEMA_VERSION = "google_finance_quote_holdings.v1"

POLITICIAN_HOLDING_FIELDS = (
    "person_id",
    "owner_relation",
    "symbol",
    "asset_type",
    "asset_name",
    "year",
    "lower_amount_bucket",
    "middle_amount_bucket",
    "upper_amount_bucket",
    "display_name",
    "active",
    "first_name",
    "last_name",
    "gender",
    "chamber",
    "party",
    "district_or_state",
)

POLITICIAN_TRANSACTION_FIELDS = (
    "person_id",
    "transaction_date",
    "symbol",
    "transaction_type",
    "amount_range",
    "disclosed_date",
    "honorific_name",
    "display_name",
    "chamber",
    "party",
    "district_or_state",
    "owner_relation",
)

INSIDER_TRANSACTION_FIELDS = (
    "symbol_exchange",
    "row_index",
    "insider_name",
    "insider_hash",
    "position",
    "image_filename",
    "rank_or_score",
    "transaction_type",
    "transaction_code",
    "transaction_date_parts",
    "amount",
    "shares",
    "currency",
    "sec_form4_url",
)


def quote_holdings_request(symbol: str, exchange: str) -> list[JSONValue]:
    return [[None, [symbol.upper(), exchange.upper()]]]


def enrich_quote_holdings_result(result: dict[str, JSONValue]) -> dict[str, JSONValue]:
    data = result.get("data")
    if not isinstance(data, list):
        return result

    labeled_data = {
        "schema_version": QUOTE_HOLDINGS_SCHEMA_VERSION,
        "confidence": "best_effort",
        "caveat": (
            "Google Finance does not advertise this Holdings tab RPC in AF_dataServiceRequests. "
            "Field names are inferred from the rendered UI and observed response structure; "
            "preserve raw_data as the source of truth."
        ),
        "politician_holdings": _label_rows(_slot(data, 0), POLITICIAN_HOLDING_FIELDS),
        "politician_transactions": _label_rows(_slot(data, 1), POLITICIAN_TRANSACTION_FIELDS),
        "insider_transactions": [_label_insider_transaction(row) for row in _rows(_slot(data, 4))],
        "pagination": {
            "politician_holdings_cursor": _slot(data, 6),
            "politician_transactions_cursor": _slot(data, 7),
            "insider_transactions_cursor": _slot(data, 8),
        },
        "raw_slots": {
            "politician_holdings": 0,
            "politician_transactions": 1,
            "insider_transactions": 4,
            "pagination_cursors": [6, 7, 8],
        },
    }

    return {**result, "labeled_data": labeled_data}


def _slot(data: list[JSONValue], index: int) -> JSONValue:
    return data[index] if index < len(data) else None


def _rows(value: JSONValue) -> list[list[JSONValue]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, list)]


def _label_rows(value: JSONValue, fields: tuple[str, ...]) -> list[dict[str, JSONValue]]:
    return [_label_row(row, fields) for row in _rows(value)]


def _label_row(row: list[JSONValue], fields: tuple[str, ...]) -> dict[str, JSONValue]:
    values = {field: row[index] if index < len(row) else None for index, field in enumerate(fields)}
    return {"values": values, "raw_row": row}


def _label_insider_transaction(row: list[JSONValue]) -> dict[str, JSONValue]:
    labeled = _label_row(row, INSIDER_TRANSACTION_FIELDS)
    values = labeled["values"]
    symbol_exchange = values.get("symbol_exchange")
    date_parts = values.get("transaction_date_parts")

    labeled.update(
        {
            "symbol": _symbol_from_tuple(symbol_exchange),
            "exchange": _exchange_from_tuple(symbol_exchange),
            "transaction_date": _date_from_parts(date_parts),
            "insider_name": values.get("insider_name"),
            "position": values.get("position"),
            "transaction_type": values.get("transaction_type"),
            "amount": values.get("amount"),
            "shares": values.get("shares"),
            "currency": values.get("currency"),
            "sec_form4_url": values.get("sec_form4_url"),
        }
    )
    return labeled


def _symbol_from_tuple(value: JSONValue) -> str | None:
    return str(value[0]) if isinstance(value, list) and value else None


def _exchange_from_tuple(value: JSONValue) -> str | None:
    return str(value[1]) if isinstance(value, list) and len(value) > 1 else None


def _date_from_parts(value: JSONValue) -> str | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    year, month, day = value[:3]
    if not all(isinstance(part, int) for part in (year, month, day)):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"
