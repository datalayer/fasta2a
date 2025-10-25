import asyncio
import socket
import threading

import httpx
import pytest
import pytest_asyncio
import uvicorn

from fasta2a.applications import FastA2A
from fasta2a.broker import InMemoryBroker
from fasta2a.client import A2AClient
from fasta2a.storage import InMemoryStorage

SERVER_HOST = '127.0.0.1'


def get_free_port() -> int:
    """Ask OS for a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest_asyncio.fixture(scope='function')
async def run_server_1():
    """Run FastA2A in a background thread and wait until it responds."""
    port = get_free_port()
    url = f'http://{SERVER_HOST}:{port}'
    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), url=url)

    # Start server in background thread
    def _run_uvicorn():
        uvicorn.run(app, host=SERVER_HOST, port=port, log_level='error')

    thread = threading.Thread(target=_run_uvicorn, daemon=True)
    thread.start()
    # Wait until the server responds to requests
    async with httpx.AsyncClient() as client:
        for _ in range(retries):
            try:
                await client.get(url)
                return
            except httpx.RequestError:
                await asyncio.sleep(0.1)  # Server not ready, wait and retry
        else:
            raise RuntimeError('Server did not start in time')
    yield url


@pytest_asyncio.fixture(scope='function')
async def run_server_2():
    """Run FastA2A in a background thread and wait until it responds."""
    port = get_free_port()
    url = f'http://{SERVER_HOST}:{port}'
    app = FastA2A(
        storage=InMemoryStorage(),
        broker=InMemoryBroker(),
        url=url,
        name='Test Agent',
        description='A test agent for unit tests.',
    )

    # Start server in background thread
    def _run_uvicorn():
        uvicorn.run(app, host=SERVER_HOST, port=port, log_level='error')

    thread = threading.Thread(target=_run_uvicorn, daemon=True)
    thread.start()
    # Wait until the server responds to requests
    async with httpx.AsyncClient() as client:
        for _ in range(100):
            try:
                # Ping the root. Any response (even 404) means the server is up.
                # The RequestError exception will catch connection-refused.
                await client.get(url)
                break  # Server is up and responding
            except httpx.RequestError:
                await asyncio.sleep(0.1)  # Server not ready, wait and retry
        else:
            raise RuntimeError('Server did not start in time')
    yield url


# ----------------------
# Tests
# ----------------------


@pytest.mark.asyncio
async def test_client_basic(run_server_1):
    a2a_client = A2AClient(agent=run_server_1)
    assert str(a2a_client.http_client.base_url) == run_server_1


@pytest.mark.asyncio
async def test_client_fetch_card(run_server):
    client = A2AClient(agent=run_server, fetch_card=True)
    assert client._agent_card is not None
    assert client.http_client.base_url == run_server


@pytest.mark.asyncio
async def test_client_check_agent_card(run_server_2):
    a2a_client = A2AClient(agent=run_server_2, fetch_card=True)
    assert a2a_client.http_client.base_url == run_server_2
    assert a2a_client._agent_card is not None
    assert a2a_client._agent_card['name'] == 'Test Agent'
    assert a2a_client._agent_card['description'] == 'A test agent for unit tests.'
