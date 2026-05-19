import urllib.request

import pytest

from murr.client import SyncClient
from murr.server import Config, HttpConfig, MurrServer, ServerConfig, StorageConfig

from conftest import user_batch, user_schema


def _config(tmp_path) -> Config:
    return Config(
        server=ServerConfig(http=HttpConfig(host="127.0.0.1", port=0)),
        storage=StorageConfig(path=str(tmp_path)),
    )


def test_start_stop_sync(tmp_path):
    server = MurrServer.start(config=_config(tmp_path))
    assert server.running is True
    assert server.endpoint and server.endpoint.startswith("http://127.0.0.1:")

    resp = urllib.request.urlopen(f"{server.endpoint}/health")
    assert resp.status == 200

    server.stop()
    assert server.running is False


def test_double_stop_is_noop(tmp_path):
    server = MurrServer.start(config=_config(tmp_path))
    server.stop()
    server.stop()  # must not raise


def test_sync_context_manager(tmp_path):
    with MurrServer.start(config=_config(tmp_path)) as server:
        assert server.running is True
        endpoint = server.endpoint
        assert endpoint is not None
    # After exiting the context manager, the server should be stopped.
    assert server.running is False


def test_endpoint_reports_actual_port(tmp_path):
    server = MurrServer.start(config=_config(tmp_path))
    try:
        # port=0 in config; endpoint must reflect the actual bound port
        host_port = server.endpoint.removeprefix("http://")
        port = int(host_port.split(":")[1])
        assert port > 0
    finally:
        server.stop()


def test_persistence_across_restart(tmp_path):
    config = _config(tmp_path)

    server = MurrServer.start(config=config)
    with SyncClient(endpoint=server.endpoint) as c:
        c.create(table="t", schema=user_schema())
        c.write(table="t", batch=user_batch())
    server.stop()

    server = MurrServer.start(config=config)
    try:
        with SyncClient(endpoint=server.endpoint) as c:
            result = c.read(table="t", keys=["c"], columns=["score"])
            assert result.column("score").to_pylist() == [3.0]
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_start_stop_async(tmp_path):
    server = await MurrServer.start_async(config=_config(tmp_path))
    assert server.running is True
    assert server.endpoint and server.endpoint.startswith("http://127.0.0.1:")
    await server.stop_async()
    assert server.running is False


@pytest.mark.asyncio
async def test_double_stop_async_is_noop(tmp_path):
    server = await MurrServer.start_async(config=_config(tmp_path))
    await server.stop_async()
    await server.stop_async()  # must not raise


@pytest.mark.asyncio
async def test_async_context_manager(tmp_path):
    async with await MurrServer.start_async(config=_config(tmp_path)) as server:
        assert server.running is True
    assert server.running is False
