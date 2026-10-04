from enum import Enum

from pydantic import BaseModel, ConfigDict


class DType(str, Enum):
    UTF8 = "utf8"
    BOOL = "bool"
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"


class ColumnSchema(BaseModel):
    """A single table column.

    Key columns must be non-nullable and of a utf8 or integer dtype. A strict
    column only accepts writes which cannot change a value: set `strict=False`
    to allow lossy casts such as float64 into a float32 column.
    """

    model_config = ConfigDict(extra="forbid")

    dtype: DType
    nullable: bool = True
    key: bool = False
    strict: bool = True


class TableSchema(BaseModel):
    """Table columns in order. Several key columns form a compound key."""

    model_config = ConfigDict(extra="forbid")

    columns: dict[str, ColumnSchema]

    @property
    def key_columns(self) -> list[str]:
        return [name for name, column in self.columns.items() if column.key]
