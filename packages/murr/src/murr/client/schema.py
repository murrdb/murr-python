from enum import Enum

from pydantic import BaseModel


class DType(str, Enum):
    UTF8 = "utf8"
    FLOAT32 = "float32"
    FLOAT64 = "float64"


class ColumnSchema(BaseModel):
    dtype: DType
    nullable: bool = True


class TableSchema(BaseModel):
    key: str
    columns: dict[str, ColumnSchema]
