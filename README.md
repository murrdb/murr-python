# murr-python

Async Python client for [murr](https://github.com/murrdb/murr), a RocksDB-based
NVMe/S3 cache for AI inference workloads.

The client is pure Python: it talks to a murr server over HTTP, with Arrow IPC
for data and JSON for schemas. Version `0.3.x` of the client needs a `0.3.x`
server.

## Install

```bash
pip install murr
```

## Quickstart

Start a server:

```bash
docker run -p 8080:8080 ghcr.io/murrdb/murr:0.3.0
```

and then:

```python
import asyncio

import pyarrow as pa
from murr.client import Client, ColumnSchema, DType, TableSchema


async def main():
    async with Client("http://localhost:8080") as db:
        await db.create_table("docs", TableSchema(columns={
            "id":       ColumnSchema(dtype=DType.UTF8, nullable=False, key=True),
            "score":    ColumnSchema(dtype=DType.FLOAT32),
            "category": ColumnSchema(dtype=DType.UTF8),
        }))

        await db.write("docs", pa.table({
            "id":       ["doc_1", "doc_2", "doc_3"],
            "score":    pa.array([0.95, 0.72, 0.68], pa.float32()),
            "category": ["ml", "infra", "ops"],
        }))

        result = await db.read("docs", {"id": ["doc_3", "doc_1"]}, columns=["score", "category"])
        print(result.to_pandas())


asyncio.run(main())
```

`read` returns a `pyarrow.Table` with the requested columns. Row `i` answers
key `i`, and a key which is not in the table gives a row of nulls.

## API

| Method                             | What it does                                  |
|------------------------------------|-----------------------------------------------|
| `create_table(name, schema)`       | Create a table                                |
| `drop_table(name)`                 | Drop a table                                  |
| `list_tables()`                    | All tables as `{name: TableSchema}`           |
| `get_schema(name)`                 | Schema of one table                           |
| `write(table, data)`               | Write a `pa.Table` or `pa.RecordBatch`        |
| `read(table, keys, columns)`       | Read columns for a batch of keys              |
| `compact(table)`                   | Compact a table, returns when it is done      |

All methods are coroutines. There is no blocking client: wrap a call in
`asyncio.run` if you need one.

### Schemas

A column has a `dtype`, and optional `nullable` (default `True`), `key`
(default `False`) and `strict` (default `True`) flags. Supported dtypes are
`utf8`, `bool`, `int8` to `int64`, `uint8` to `uint64`, `float32` and `float64`.

A table needs at least one key column. Key columns must be `nullable=False`
and of a `utf8` or integer dtype. Several key columns form a compound key:

```python
schema = TableSchema(columns={
    "user":  ColumnSchema(dtype=DType.UTF8,  nullable=False, key=True),
    "item":  ColumnSchema(dtype=DType.INT64, nullable=False, key=True),
    "score": ColumnSchema(dtype=DType.FLOAT64),
})

await db.create_table("ratings", schema)
await db.read("ratings", {"user": ["u1", "u2"], "item": [1, 7]}, columns=["score"])
```

### Keys

Keys go to the server as an Arrow table with one column per key column. Pass
a `pa.Table`, a `pa.RecordBatch`, or a `{name: values}` mapping which is turned
into a table with `pa.table()`.

The server widens types (an `int32` array is fine for an `int64` key) but never
narrows them. Python ints become `int64`, so a narrower key column needs a
typed array:

```python
await db.read("events", {"id": pa.array([1, 2], pa.int32())}, columns=["flag"])
```

The same holds for writes, with one addition: writing `float64` values into a
`float32` column rounds them, and is only accepted for a column created with
`strict=False`.

### Errors

Server errors are raised as subclasses of `MurrError`, which carries the HTTP
`status_code` and the server `message`:

| Exception                 | When                                             |
|---------------------------|--------------------------------------------------|
| `TableNotFoundError`      | the table does not exist                         |
| `TableAlreadyExistsError` | `create_table` for an existing name              |
| `InvalidRequestError`     | bad schema, wrong key types, unknown column      |
| `ServerError`             | the server failed to process the request         |

## Development

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

The tests start `ghcr.io/murrdb/murr:0.3.0` in Docker through
[testcontainers](https://testcontainers-python.readthedocs.io). Set `MURR_IMAGE`
to test against another image, or `MURR_ENDPOINT` to use a server which is
already running.

## Releases

Set `version` in `pyproject.toml` and push a matching `v<version>` tag, like
`v0.3.0`. The release workflow runs the tests, checks that the tag matches the
package version, publishes the sdist and wheel to PyPI, and then creates a
GitHub release.

## License

Apache-2.0.
