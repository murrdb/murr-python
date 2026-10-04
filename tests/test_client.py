import pyarrow as pa
import pytest

from murr.client import (
    ColumnSchema,
    DType,
    InvalidRequestError,
    TableAlreadyExistsError,
    TableNotFoundError,
    TableSchema,
)


def user_schema() -> TableSchema:
    return TableSchema(
        columns={
            "id": ColumnSchema(dtype=DType.UTF8, nullable=False, key=True),
            "score": ColumnSchema(dtype=DType.FLOAT32),
        },
    )


def user_batch() -> pa.RecordBatch:
    return pa.RecordBatch.from_pydict(
        {"id": ["a", "b", "c"], "score": [1.0, 2.0, 3.0]},
        schema=pa.schema([
            pa.field("id", pa.utf8(), nullable=False),
            pa.field("score", pa.float32(), nullable=True),
        ]),
    )


def rating_schema() -> TableSchema:
    return TableSchema(
        columns={
            "user": ColumnSchema(dtype=DType.UTF8, nullable=False, key=True),
            "item": ColumnSchema(dtype=DType.INT64, nullable=False, key=True),
            "score": ColumnSchema(dtype=DType.FLOAT64),
        },
    )


async def test_write_and_read_roundtrip(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())

    result = await client.read(table, {"id": ["c", "a"]}, columns=["score"])
    assert isinstance(result, pa.Table)
    assert result.column_names == ["score"]
    assert result.column("score").to_pylist() == [3.0, 1.0]


async def test_read_with_arrow_table_keys(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())

    keys = pa.table({"id": ["b"]})
    result = await client.read(table, keys, columns=["score"])
    assert result.column("score").to_pylist() == [2.0]


async def test_read_with_record_batch_keys(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())

    keys = pa.RecordBatch.from_pydict({"id": ["b", "c"]})
    result = await client.read(table, keys, columns=["score"])
    assert result.column("score").to_pylist() == [2.0, 3.0]


async def test_read_missing_key_is_null(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())

    result = await client.read(table, {"id": ["a", "nope"]}, columns=["score"])
    assert result.column("score").to_pylist() == [1.0, None]


async def test_compound_key(client, table):
    await client.create_table(table, rating_schema())
    await client.write(
        table,
        pa.table({"user": ["u1", "u1", "u2"], "item": [1, 2, 1], "score": [0.1, 0.2, 0.3]}),
    )

    result = await client.read(
        table, {"user": ["u2", "u1", "u2"], "item": [1, 2, 2]}, columns=["score"]
    )
    assert result.column("score").to_pylist() == [0.3, 0.2, None]


async def test_int32_key_needs_typed_array(client, table):
    schema = TableSchema(
        columns={
            "id": ColumnSchema(dtype=DType.INT32, nullable=False, key=True),
            "flag": ColumnSchema(dtype=DType.BOOL),
        },
    )
    await client.create_table(table, schema)
    await client.write(
        table, pa.table({"id": pa.array([1, 2], pa.int32()), "flag": [True, False]})
    )

    result = await client.read(table, {"id": pa.array([2, 1], pa.int32())}, columns=["flag"])
    assert result.column("flag").to_pylist() == [False, True]

    # python ints are int64, and the server does not narrow key types
    with pytest.raises(InvalidRequestError):
        await client.read(table, {"id": [2, 1]}, columns=["flag"])


async def test_write_multi_batch_table(client, table):
    await client.create_table(table, user_schema())

    more = pa.RecordBatch.from_pydict(
        {"id": ["d", "e"], "score": [4.0, 5.0]}, schema=user_batch().schema
    )
    data = pa.Table.from_batches([user_batch(), more])
    await client.write(table, data)

    result = await client.read(table, {"id": ["a", "e"]}, columns=["score"])
    assert result.column("score").to_pylist() == [1.0, 5.0]


async def test_list_tables(client, table):
    await client.create_table(table, user_schema())

    tables = await client.list_tables()
    assert tables[table] == user_schema()


async def test_get_schema(client, table):
    schema = TableSchema(
        columns={
            "id": ColumnSchema(dtype=DType.UTF8, nullable=False, key=True),
            "score": ColumnSchema(dtype=DType.FLOAT32, strict=False),
        },
    )
    await client.create_table(table, schema)

    result = await client.get_schema(table)
    assert result == schema
    assert result.key_columns == ["id"]


async def test_drop_table(client, table):
    await client.create_table(table, user_schema())
    await client.drop_table(table)

    assert table not in await client.list_tables()
    with pytest.raises(TableNotFoundError):
        await client.get_schema(table)


async def test_compact(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())
    await client.compact(table)

    result = await client.read(table, {"id": ["a"]}, columns=["score"])
    assert result.column("score").to_pylist() == [1.0]


async def test_create_duplicate_raises(client, table):
    await client.create_table(table, user_schema())
    with pytest.raises(TableAlreadyExistsError) as error:
        await client.create_table(table, user_schema())
    assert error.value.status_code == 409


async def test_create_without_key_raises(client, table):
    schema = TableSchema(columns={"score": ColumnSchema(dtype=DType.FLOAT32)})
    with pytest.raises(InvalidRequestError):
        await client.create_table(table, schema)


async def test_read_nonexistent_table_raises(client, table):
    with pytest.raises(TableNotFoundError):
        await client.read(table, {"id": ["a"]}, columns=["x"])


async def test_read_key_column_rejected(client, table):
    await client.create_table(table, user_schema())
    await client.write(table, user_batch())

    with pytest.raises(InvalidRequestError):
        await client.read(table, {"id": ["b"]}, columns=["id", "score"])
