# murr-python

Python packages for [murr](https://github.com/shuttie/murr) — a columnar
in-memory cache for AI/ML inference workloads.

This repo ships two PyPI distributions that share the `murr` Python namespace
([PEP 420](https://peps.python.org/pep-0420/) implicit namespace packages):

| Distribution  | Import path     | Size  | What it gives you                                  |
|---------------|-----------------|-------|----------------------------------------------------|
| `murr`        | `murr.client`   | small | Pure-Python HTTP client (`AsyncClient`, `SyncClient`) |
| `murr-server` | `murr.server`   | large | Embedded server with native PyO3 bindings (`MurrServer`) |

Both can be installed side-by-side. `murr.server` *depends on* `murr` (for the
shared schema and exception types), but `murr` has no dependency on
`murr-server` — read-only clients get a tiny wheel without the native runtime.

## Install

```bash
pip install murr                 # client only
pip install murr[server]         # client + embedded server
```

## Quickstart — embedded server + sync client

```python
import pyarrow as pa
from murr.client import SyncClient, TableSchema, ColumnSchema, DType
from murr.server import MurrServer, Config, ServerConfig, HttpConfig, StorageConfig

config = Config(
    server=ServerConfig(http=HttpConfig(host="127.0.0.1", port=0)),
    storage=StorageConfig(path="/tmp/murr"),
)

with MurrServer.start(config=config) as server, \
     SyncClient(endpoint=server.endpoint) as client:

    client.create(table="scores", schema=TableSchema(
        key="id",
        columns={
            "id":    ColumnSchema(dtype=DType.UTF8, nullable=False),
            "score": ColumnSchema(dtype=DType.FLOAT32),
        },
    ))

    client.write(table="scores", batch=pa.RecordBatch.from_pydict(
        {"id": ["a", "b"], "score": [1.0, 2.0]},
        schema=pa.schema([
            pa.field("id",    pa.utf8(),    nullable=False),
            pa.field("score", pa.float32(), nullable=True),
        ]),
    ))

    result = client.read(table="scores", keys=["a", "b"], columns=["score"])
    print(result.column("score").to_pylist())  # [1.0, 2.0]
```

## Async API

```python
import asyncio
from murr.client import AsyncClient
from murr.server import MurrServer, Config, StorageConfig

async def main():
    server = await MurrServer.start_async(
        config=Config(storage=StorageConfig(path="/tmp/murr"))
    )
    try:
        async with AsyncClient(endpoint=server.endpoint) as client:
            await client.list_tables()
    finally:
        await server.stop_async()

asyncio.run(main())
```

## Connecting to a remote server

`MurrServer` is only needed for **embedded** use. To talk to a server running
elsewhere (any HTTP-speaking Murr instance):

```python
from murr.client import SyncClient
with SyncClient(endpoint="https://murr.example.com") as client:
    client.list_tables()
```

In this case install only the `murr` package — no native extension required.

## Development

```bash
uv venv .venv --python 3.14
source .venv/bin/activate

# Client (pure Python)
uv pip install -e packages/murr
uv pip install maturin pytest pytest-asyncio

# Server (Rust + Python)
cd packages/murr-server && maturin develop && cd ../..

# Tests
pytest tests/ -v
```

### Working against an unreleased `murr` Rust crate

Check out the upstream `murr` repo as a sibling directory (`../../../murr`
relative to `packages/murr-server`), then uncomment the `[patch.crates-io]`
block at the bottom of `packages/murr-server/Cargo.toml`. Do not commit it
uncommented — CI must resolve `murr` from crates.io.

## Releases

Tag a `v*` release. The release workflow currently creates a GitHub release
only; the wheel-build and PyPI publish steps are stubbed out — see
`.github/workflows/release.yml` for the path to enable.

## License

Apache-2.0.
