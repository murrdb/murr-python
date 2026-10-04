import os
import uuid

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

from murr.client import Client, TableNotFoundError

HTTP_PORT = 8080
DEFAULT_IMAGE = "ghcr.io/murrdb/murr:0.3.0"


@pytest.fixture(scope="session")
def endpoint():
    """One murr server for the whole test session.

    Set MURR_ENDPOINT to test against an already running server, or MURR_IMAGE
    to start another image.
    """
    external = os.environ.get("MURR_ENDPOINT")
    if external:
        yield external
        return
    image = os.environ.get("MURR_IMAGE", DEFAULT_IMAGE)
    container = (
        DockerContainer(image)
        .with_exposed_ports(HTTP_PORT)
        .waiting_for(HttpWaitStrategy(HTTP_PORT, "/health"))
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(HTTP_PORT)
        yield f"http://{host}:{port}"


@pytest.fixture
async def client(endpoint):
    async with Client(endpoint) as c:
        yield c


@pytest.fixture
async def table(client):
    """A unique table name, the table is dropped after the test."""
    name = f"t_{uuid.uuid4().hex}"
    yield name
    try:
        await client.drop_table(name)
    except TableNotFoundError:
        pass
