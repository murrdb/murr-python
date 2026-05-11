# murr-python

Python bindings for [murr](https://github.com/shuttie/murr) — a columnar in-memory cache for AI/ML inference workloads.

## Install

```bash
pip install murr
```

## Usage

```python
from murr.sync import Murr
from murr.schema import TableSchema, ColumnSchema, DType
import pyarrow as pa

murr = Murr.start_local(cache_dir="/tmp/murr-cache")
schema = TableSchema(
    key="id",
    columns=[
        ColumnSchema(name="id", dtype=DType.UTF8),
        ColumnSchema(name="score", dtype=DType.FLOAT32),
    ],
)
murr.create("scores", schema)

batch = pa.record_batch({"id": ["a", "b"], "score": [1.0, 2.0]})
murr.write("scores", batch)

result = murr.read("scores", keys=["a", "b"], columns=["score"])
```

For the async API: `from murr.aio import Murr`.

For a remote HTTP client: `from murr.http import MurrClientSync` (or `MurrClientAsync`).

## Development

```bash
uv venv .venv --python 3.14
source .venv/bin/activate
uv pip install maturin pytest pytest-asyncio pyarrow pydantic httpx
maturin develop -E dev
pytest tests/ -v
```

### Working against an unreleased `murr` Rust crate

Check out the upstream `murr` repo as a sibling directory (`../murr`), then uncomment the `[patch.crates-io]` block at the bottom of `Cargo.toml`:

```toml
[patch.crates-io]
murr = { path = "../murr" }
```

Do not commit the uncommented form — CI must resolve `murr` from crates.io.

## Releases

Tag a `v*` release on this repo. The `release.yml` workflow builds wheels for Linux/macOS/Windows × Python 3.11–3.14 and publishes them to PyPI as `murr`.

## License

Apache-2.0.
