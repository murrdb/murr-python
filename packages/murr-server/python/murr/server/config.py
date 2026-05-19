from __future__ import annotations

import os
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, model_serializer


class MmapBackend(BaseModel):
    """RocksDB PlainTable (mmap) backend. Defaults mirror the Rust crate."""

    model_config = ConfigDict(extra="forbid")

    bloom_bits_per_key: int = 16
    hash_table_ratio: float = 0.75
    index_sparseness: int = 4
    store_index_in_file: bool = False
    huge_page_tlb_size: int = 0
    write_buffer_size: int = 64 * 1024 * 1024
    target_file_size_base: int = 64 * 1024 * 1024
    disable_auto_compactions: bool = True


class BlockBackend(BaseModel):
    """RocksDB BlockBasedTable backend. Defaults mirror the Rust crate."""

    model_config = ConfigDict(extra="forbid")

    bloom_filter_bits_per_key: float | None = None
    whole_key_filtering: bool = True
    block_size: int = 512
    block_cache_mb: int = 0
    cache_index_and_filter_blocks: bool = False
    pin_l0_filter_and_index_blocks: bool = False
    block_restart_interval: int = 8
    data_block_hash_index: bool = True
    data_block_hash_ratio: float = 0.75
    mmap_reads: bool = True
    use_direct_reads: bool = False
    async_io: bool = True
    verify_checksums: bool = False
    write_buffer_size: int = 64 * 1024 * 1024
    target_file_size_base: int = 64 * 1024 * 1024
    disable_auto_compactions: bool = True


BackendConfig = Union[MmapBackend, BlockBackend]


def _backend_tag(backend: BackendConfig) -> str:
    if isinstance(backend, MmapBackend):
        return "mmap"
    if isinstance(backend, BlockBackend):
        return "block"
    raise TypeError(f"unknown backend type: {type(backend).__name__}")


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    path: str
    backend: BackendConfig = Field(default_factory=MmapBackend)

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        # Mirror the Rust StorageConfig serde shape: backend is flattened with
        # its variant name as the key alongside `path`.
        return {
            "path": os.fspath(self.path),
            _backend_tag(self.backend): self.backend.model_dump(),
        }


class HttpConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "0.0.0.0"
    port: int = 8080
    max_payload_size: int = 1024 * 1024 * 1024


class GrpcConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "0.0.0.0"
    port: int = 8081


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    http: HttpConfig = Field(default_factory=HttpConfig)
    grpc: GrpcConfig = Field(default_factory=GrpcConfig)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig
