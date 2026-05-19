import pyarrow as pa
import pytest

from murr.client import ColumnSchema, DType, SyncClient, TableSchema
from murr.server import Config, HttpConfig, MurrServer, ServerConfig, StorageConfig

from conftest import user_batch, user_schema


@pytest.fixture
def client(tmp_path):
    config = Config(
        server=ServerConfig(http=HttpConfig(host="127.0.0.1", port=0)),
        storage=StorageConfig(path=str(tmp_path)),
    )
    with MurrServer.start(config=config) as server:
        with SyncClient(endpoint=server.endpoint) as c:
            yield c


def test_create_and_read_roundtrip(client):
    client.create(table="users", schema=user_schema())
    client.write(table="users", batch=user_batch())

    result = client.read(table="users", keys=["c", "a"], columns=["score"])
    assert result.num_rows == 2
    assert result.column("score").to_pylist() == [3.0, 1.0]


def test_read_key_column_rejected(client):
    client.create(table="users", schema=user_schema())
    client.write(table="users", batch=user_batch())

    with pytest.raises((RuntimeError, Exception)):
        client.read(table="users", keys=["b"], columns=["id", "score"])


def test_list_tables(client):
    schema = TableSchema(
        key="id",
        columns={"id": ColumnSchema(dtype=DType.UTF8, nullable=False)},
    )
    client.create(table="t1", schema=schema)

    tables = client.list_tables()
    assert "t1" in tables
    assert tables["t1"].key == "id"
    assert tables["t1"].columns["id"].dtype == DType.UTF8


def test_get_schema(client):
    schema = user_schema()
    client.create(table="users", schema=schema)

    result = client.get_schema(table="users")
    assert result == schema


def test_create_duplicate_raises(client):
    schema = TableSchema(
        key="id",
        columns={"id": ColumnSchema(dtype=DType.UTF8, nullable=False)},
    )
    client.create(table="t", schema=schema)
    with pytest.raises(ValueError):
        client.create(table="t", schema=schema)


def test_read_nonexistent_table_raises(client):
    with pytest.raises(FileNotFoundError):
        client.read(table="nope", keys=["a"], columns=["x"])


def test_get_schema_nonexistent_raises(client):
    with pytest.raises(FileNotFoundError):
        client.get_schema(table="nope")


def test_write_pa_table(client):
    client.create(table="users", schema=user_schema())

    table = pa.table(
        {"id": ["a", "b"], "score": [1.0, 2.0]},
        schema=pa.schema([
            pa.field("id", pa.utf8(), nullable=False),
            pa.field("score", pa.float32(), nullable=True),
        ]),
    )
    client.write(table="users", batch=table)

    result = client.read(table="users", keys=["b"], columns=["score"])
    assert result.column("score").to_pylist() == [2.0]
