from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa

ARROW_IPC_MIME = "application/vnd.apache.arrow.stream"

# schema metadata entry of a fetch request, listing the columns to return
COLUMNS_METADATA = b"columns"


def to_table(data: pa.Table | pa.RecordBatch | Mapping[str, Any]) -> pa.Table:
    if isinstance(data, pa.Table):
        return data
    if isinstance(data, pa.RecordBatch):
        return pa.Table.from_batches([data])
    return pa.table(dict(data))


def fetch_request(keys: pa.Table, columns: Sequence[str]) -> pa.Table:
    metadata = dict(keys.schema.metadata or {})
    metadata[COLUMNS_METADATA] = json.dumps(list(columns)).encode()
    return keys.replace_schema_metadata(metadata)


def table_to_ipc(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()


def ipc_to_table(data: bytes) -> pa.Table:
    return pa.ipc.open_stream(data).read_all()
