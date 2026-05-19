from __future__ import annotations

import json
from enum import Enum

import httpx
import pyarrow as pa

from murr.client._common import (
    batch_to_ipc,
    ipc_to_batch,
    parse_table_schemas,
    validate_and_convert_batch,
)
from murr.client._http import ARROW_IPC_MIME, raise_for_status
from murr.client.schema import TableSchema


class Transport(str, Enum):
    HTTP = "http"


class SyncClient:
    """Synchronous client for a Murr server."""

    def __init__(self, endpoint: str, transport: Transport = Transport.HTTP) -> None:
        if transport is not Transport.HTTP:
            raise NotImplementedError(f"transport {transport} not supported yet")
        self._client = httpx.Client(base_url=endpoint.rstrip("/"))

    def create(self, table: str, schema: TableSchema) -> None:
        resp = self._client.put(
            f"/api/v1/table/{table}",
            content=schema.model_dump_json(),
            headers={"content-type": "application/json"},
        )
        raise_for_status(resp)

    def write(self, table: str, batch: pa.RecordBatch | pa.Table) -> None:
        for rb in validate_and_convert_batch(batch):
            resp = self._client.put(
                f"/api/v1/table/{table}/write",
                content=batch_to_ipc(rb),
                headers={"content-type": ARROW_IPC_MIME},
            )
            raise_for_status(resp)

    def read(
        self, table: str, keys: list[str], columns: list[str]
    ) -> pa.RecordBatch:
        resp = self._client.post(
            f"/api/v1/table/{table}/fetch",
            content=json.dumps({"keys": keys, "columns": columns}),
            headers={"content-type": "application/json", "accept": ARROW_IPC_MIME},
        )
        raise_for_status(resp)
        return ipc_to_batch(resp.content)

    def list_tables(self) -> dict[str, TableSchema]:
        resp = self._client.get("/api/v1/table")
        raise_for_status(resp)
        return parse_table_schemas(resp.json())

    def get_schema(self, table: str) -> TableSchema:
        resp = self._client.get(f"/api/v1/table/{table}/schema")
        raise_for_status(resp)
        return TableSchema.model_validate(resp.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SyncClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
