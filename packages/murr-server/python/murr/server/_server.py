from __future__ import annotations

from murr.server.config import Config
from murr.server.libmurr import MurrServer as _MurrServer


class MurrServer:
    """Embedded Murr server. Lifecycle only — for CRUD, connect a client to
    ``server.endpoint`` (e.g. ``SyncClient(endpoint=server.endpoint)``)."""

    def __init__(self, _inner: _MurrServer) -> None:
        self._inner = _inner

    @classmethod
    def start(cls, config: Config) -> MurrServer:
        return cls(_MurrServer._start_blocking(config.model_dump()))

    @classmethod
    async def start_async(cls, config: Config) -> MurrServer:
        inner = await _MurrServer._start_async(config.model_dump())
        return cls(inner)

    @property
    def endpoint(self) -> str | None:
        """HTTP endpoint URL, or None if the server has been stopped."""
        return self._inner.endpoint

    @property
    def running(self) -> bool:
        return self._inner.running

    def stop(self) -> None:
        self._inner._stop_blocking()

    async def stop_async(self) -> None:
        await self._inner._stop_async()

    def __enter__(self) -> MurrServer:
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    async def __aenter__(self) -> MurrServer:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.stop_async()
