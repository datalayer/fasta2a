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

SERVER_HOST = "127.0.0.1"


def get_free_port() -> int:
    """Ask OS for a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def _wait_server(url: str, retries: int = 100, delay: float = 0.1):
    """Wait until the server responds (any response, even 404)."""
    async with httpx.AsyncClient() as client:
        for _ in range(retries):
            try:
                await client.get(url)
                return
            except httpx.RequestError:
                await asyncio.sleep(delay)
        raise RuntimeError(f'Server at {url} did not start in time')


def _start_server_in_thread(app, host: str, port: int):
    """Run uvicorn server in a background thread."""

    def _run_uvicorn():
        uvicorn.run(app, host=host, port=port, log_level='error')

    thread = threading.Thread(target=_run_uvicorn, daemon=True)
    thread.start()


@pytest_asyncio.fixture(scope='function')
async def run_server(request):
    params = getattr(request, 'param', {})
    port = get_free_port()
    url = f'http://{SERVER_HOST}:{port}'

    app = FastA2A(
        storage=InMemoryStorage(),
        broker=InMemoryBroker(),
        url=url,
        name=params.get('name'),
        description=params.get('description'),
    )

    _start_server_in_thread(app, SERVER_HOST, port)
    await _wait_server(url)
    yield url


# ----------------------
# Tests
# ----------------------


@pytest.mark.asyncio
async def test_client_basic(run_server):
    client = A2AClient(agent=run_server)
    assert str(client.http_client.base_url) == run_server


@pytest.mark.asyncio
async def test_client_fetch_card(run_server):
    client = A2AClient(agent=run_server, fetch_card=True)
    assert client._agent_card is not None
    assert client.http_client.base_url == run_server


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'run_server',
    [{'name': 'Test Agent', 'description': 'A test agent for unit tests.'}],
    indirect=True,
)
async def test_client_check_agent_card(run_server):
    client = A2AClient(agent=run_server, fetch_card=True)
    assert client.http_client.base_url == run_server
    assert client._agent_card is not None
    assert client._agent_card['name'] == 'Test Agent'
    assert client._agent_card['description'] == 'A test agent for unit tests.'
