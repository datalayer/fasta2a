from __future__ import annotations as _annotations

from contextlib import asynccontextmanager

import httpx
import pytest
from asgi_lifespan import LifespanManager
from inline_snapshot import snapshot
from starlette.applications import Starlette

from fasta2a.applications import FastA2A
from fasta2a.broker import InMemoryBroker
from fasta2a.storage import InMemoryStorage

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def create_test_client(app: FastA2A):
    async with LifespanManager(app=app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testclient') as client:
            yield client


async def test_agent_card():
    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker())
    async with create_test_client(app) as client:
        response = await client.get('/.well-known/agent-card.json')
        assert response.status_code == 200
        assert response.json() == snapshot(
            {
                'name': 'My Agent',
                'description': 'An AI agent exposed as an A2A agent.',
                'version': '1.0.0',
                'supportedInterfaces': [
                    {
                        'protocolBinding': 'JSONRPC',
                        'url': 'http://localhost:8000',
                        'protocolVersion': '1.0',
                    },
                ],
                'skills': [],
                'defaultInputModes': ['application/json'],
                'defaultOutputModes': ['application/json'],
                'capabilities': {
                    'streaming': True,
                    'pushNotifications': False,
                },
            }
        )


async def test_custom_lifespan_still_starts_task_manager():
    """A user-provided lifespan must not replace the default one. See #37."""
    called = False

    @asynccontextmanager
    async def user_lifespan(app: FastA2A):
        nonlocal called
        called = True
        assert app.task_manager.is_running
        yield

    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), lifespan=user_lifespan)
    async with create_test_client(app):
        assert app.task_manager.is_running
    assert called
    assert not app.task_manager.is_running


async def test_custom_lifespan_entering_task_manager_itself():
    """A lifespan that enters the task manager explicitly keeps working."""

    @asynccontextmanager
    async def user_lifespan(app: FastA2A):
        async with app.task_manager:
            yield

    app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), lifespan=user_lifespan)
    async with create_test_client(app):
        assert app.task_manager.is_running
    assert not app.task_manager.is_running


class TestDocsEndpoint:
    async def test_docs_endpoint_default(self):
        app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker())
        async with create_test_client(app) as client:
            response = await client.get('/docs')
            assert response.status_code == 200
            assert '__FASTA2A_API_ROOT__' not in response.text
            assert 'const apiRoot = "";' in response.text

    async def test_docs_endpoint_custom_url(self):
        app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), docs_url='/custom-docs')
        async with create_test_client(app) as client:
            response = await client.get('/custom-docs')
            assert response.status_code == 200

    async def test_docs_endpoint_mounted_app_uses_root_path(self):
        a2a_app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker())

        @asynccontextmanager
        async def lifespan(_app: Starlette):
            async with a2a_app.router.lifespan_context(a2a_app):
                yield

        app = Starlette(lifespan=lifespan)
        app.mount('/agent', a2a_app)

        async with LifespanManager(app=app) as manager:
            transport = httpx.ASGITransport(app=manager.app)
            async with httpx.AsyncClient(transport=transport, base_url='http://testclient') as client:
                response = await client.get('/agent/docs')
                assert response.status_code == 200
                assert '__FASTA2A_API_ROOT__' not in response.text
                assert 'const apiRoot = "/agent";' in response.text
                assert 'href="/agent/.well-known/agent-card.json"' in response.text

                response = await client.get('/agent/.well-known/agent-card.json')
                assert response.status_code == 200

    async def test_docs_endpoint_disabled(self):
        app = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), docs_url=None)
        async with create_test_client(app) as client:
            response = await client.get('/docs')
            assert response.status_code == 404

    async def test_docs_endpoint_invalid_url(self):
        with pytest.raises(AssertionError, match='must start with'):
            _ = FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), docs_url='http://invalid-url.local')
