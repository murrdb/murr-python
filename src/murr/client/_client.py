from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx
import pyarrow as pa

from murr.client._arrow import (
    ARROW_IPC_MIME,
    fetch_request,
    ipc_to_table,
    table_to_ipc,
    to_table,
)
from murr.client.errors import raise_for_status
from murr.client.schema import TableSchema


class Client:
    """Asynchronous client for a Murr server."""

    def __init__(self, endpoint: str, *, timeout: float | httpx.Timeout = 30.0) -> None:
        self._client = httpx.AsyncClient(base_url=endpoint.rstrip("/"), timeout=timeout)

    async def create_table(self, name: str, schema: TableSchema) -> None:
        resp = await self._client.put(
            f"/api/v1/table/{name}",
            content=schema.model_dump_json(),
            headers={"content-type": "application/json"},
        )
        raise_for_status(resp)

    async def drop_table(self, name: str) -> None:
        resp = await self._client.delete(f"/api/v1/table/{name}")
        raise_for_status(resp)

    async def list_tables(self) -> dict[str, TableSchema]:
        resp = await self._client.get("/api/v1/table")
        raise_for_status(resp)
        return {
            name: TableSchema.model_validate(schema)
            for name, schema in resp.json().items()
        }

    async def get_schema(self, name: str) -> TableSchema:
        resp = await self._client.get(f"/api/v1/table/{name}/schema")
        raise_for_status(resp)
        return TableSchema.model_validate(resp.json())

    async def write(self, table: str, data: pa.Table | pa.RecordBatch) -> None:
        """Write rows to a table.

        Columns are matched to the table schema by name, extra columns are
        ignored.
        """
        resp = await self._client.put(
            f"/api/v1/table/{table}/write",
            content=table_to_ipc(to_table(data)),
            headers={"content-type": ARROW_IPC_MIME},
        )
        raise_for_status(resp)

    async def read(
        self,
        table: str,
        keys: pa.Table | pa.RecordBatch | Mapping[str, Any],
        columns: Sequence[str],
    ) -> pa.Table:
        """Read `columns` for a batch of keys.

        `keys` holds one column per key column of the table, either as an Arrow
        table or as a `{name: values}` mapping. Row `i` of the result answers
        row `i` of `keys`, with nulls for keys which are not found.

        The server only widens key types. A mapping of Python ints becomes
        int64, so pass a typed array for a narrower key column:
        `{"id": pa.array([1, 2], pa.int32())}`.
        """
        resp = await self._client.post(
            f"/api/v1/table/{table}/fetch",
            content=table_to_ipc(fetch_request(to_table(keys), columns)),
            headers={"content-type": ARROW_IPC_MIME, "accept": ARROW_IPC_MIME},
        )
        raise_for_status(resp)
        return ipc_to_table(resp.content)

    async def compact(self, table: str) -> None:
        """Compact a table, returning when the compaction is done."""
        resp = await self._client.post(f"/api/v1/table/{table}/compact", timeout=None)
        raise_for_status(resp)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
