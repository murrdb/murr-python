import pyarrow as pa
import pytest
import pytest_asyncio

from murr.client import AsyncClient, ColumnSchema, DType, TableSchema
from murr.server import Config, HttpConfig, MurrServer, ServerConfig, StorageConfig

from conftest import user_batch, user_schema


@pytest_asyncio.fixture
async def client(tmp_path):
    config = Config(
        server=ServerConfig(http=HttpConfig(host="127.0.0.1", port=0)),
        storage=StorageConfig(path=str(tmp_path)),
    )
    server = await MurrServer.start_async(config=config)
    try:
        async with AsyncClient(endpoint=server.endpoint) as c:
            yield c
    finally:
        await server.stop_async()


@pytest.mark.asyncio
async def test_create_and_read_roundtrip(client):
    await client.create(table="users", schema=user_schema())
    await client.write(table="users", batch=user_batch())

    result = await client.read(table="users", keys=["c", "a"], columns=["score"])
    assert result.num_rows == 2
    assert result.column("score").to_pylist() == [3.0, 1.0]


@pytest.mark.asyncio
async def test_read_key_column_rejected(client):
    await client.create(table="users", schema=user_schema())
    await client.write(table="users", batch=user_batch())

    with pytest.raises((RuntimeError, Exception)):
        await client.read(table="users", keys=["b"], columns=["id", "score"])


@pytest.mark.asyncio
async def test_list_tables(client):
    schema = TableSchema(
        key="id",
        columns={"id": ColumnSchema(dtype=DType.UTF8, nullable=False)},
    )
    await client.create(table="t1", schema=schema)

    tables = await client.list_tables()
    assert "t1" in tables
    assert tables["t1"].key == "id"
    assert tables["t1"].columns["id"].dtype == DType.UTF8


@pytest.mark.asyncio
async def test_get_schema(client):
    schema = user_schema()
    await client.create(table="users", schema=schema)

    result = await client.get_schema(table="users")
    assert result == schema


@pytest.mark.asyncio
async def test_create_duplicate_raises(client):
    schema = TableSchema(
        key="id",
        columns={"id": ColumnSchema(dtype=DType.UTF8, nullable=False)},
    )
    await client.create(table="t", schema=schema)
    with pytest.raises(ValueError):
        await client.create(table="t", schema=schema)


@pytest.mark.asyncio
async def test_read_nonexistent_table_raises(client):
    with pytest.raises(FileNotFoundError):
        await client.read(table="nope", keys=["a"], columns=["x"])


@pytest.mark.asyncio
async def test_get_schema_nonexistent_raises(client):
    with pytest.raises(FileNotFoundError):
        await client.get_schema(table="nope")


@pytest.mark.asyncio
async def test_write_pa_table(client):
    await client.create(table="users", schema=user_schema())

    table = pa.table(
        {"id": ["a", "b"], "score": [1.0, 2.0]},
        schema=pa.schema([
            pa.field("id", pa.utf8(), nullable=False),
            pa.field("score", pa.float32(), nullable=True),
        ]),
    )
    await client.write(table="users", batch=table)

    result = await client.read(table="users", keys=["b"], columns=["score"])
    assert result.column("score").to_pylist() == [2.0]
