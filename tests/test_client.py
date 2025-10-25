from __future__ import annotations as _annotations

from contextlib import asynccontextmanager

import httpx
import pytest
from asgi_lifespan import LifespanManager

from fasta2a.applications import FastA2A
from fasta2a.broker import InMemoryBroker
from fasta2a.client import A2AClient
from fasta2a.schema import agent_card_ta
from fasta2a.storage import InMemoryStorage

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def create_test_client(app: FastA2A):
    async with LifespanManager(app=app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testclient') as client:
            yield client


async def test_client_basic():
    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker())
    async with create_test_client(app) as http_client:
        client = A2AClient(agent='http://testclient', http_client=http_client)
        assert client.http_client.base_url == 'http://testclient'
        assert client.agent_card is None


async def test_client_fetch_card(monkeypatch: pytest.MonkeyPatch):
    app = FastA2A(
        storage=InMemoryStorage(),
        broker=InMemoryBroker(),
        name='Test Agent',
        description='A test agent for unit tests.',
        url='http://testclient',
    )
    async with create_test_client(app) as http_client:
        card_response = await http_client.get('/.well-known/agent-card.json')
        assert card_response.status_code == 200
        card_json = card_response.json()

        def fake_get(url: str) -> httpx.Response:
            return httpx.Response(200, json=card_json, request=httpx.Request('GET', url))

        monkeypatch.setattr(httpx, 'get', fake_get)

        client = A2AClient(agent='http://testclient', http_client=http_client, fetch_card=True)
        assert client.agent_card is not None
        assert client.agent_card['name'] == 'Test Agent'
        assert client.agent_card['description'] == 'A test agent for unit tests.'
        assert client.http_client.base_url == 'http://testclient'


async def test_client_agent_card_directly():
    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), url='http://testclient')
    async with create_test_client(app) as http_client:
        card_response = await http_client.get('/.well-known/agent-card.json')
        agent_card = agent_card_ta.validate_python(card_response.json())

        client = A2AClient(agent=agent_card, http_client=http_client)
        assert client.agent_card == agent_card
        assert client.http_client.base_url == 'http://testclient'
