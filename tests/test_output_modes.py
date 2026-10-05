"""Output modes: what the card declares, and the modes a request accepts, as the worker sees them."""

from __future__ import annotations as _annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest

from fasta2a import FastA2A
from fasta2a.broker import InMemoryBroker
from fasta2a.schema import (
    Artifact,
    Message,
    StreamResponse,
    TaskIdParams,
    TaskSendParams,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from fasta2a.storage import InMemoryStorage
from fasta2a.worker import Worker

pytestmark = pytest.mark.anyio

NOTEBOOK = 'application/x-ipynb+json'


class RecordingWorker(Worker[Any]):
    """Completes each task, and records the output modes it was accepted in."""

    def __init__(self, broker: InMemoryBroker, storage: InMemoryStorage[Any]) -> None:
        super().__init__(broker=broker, storage=storage)
        self.seen: list[list[str] | None] = []

    async def run_task(self, params: TaskSendParams) -> None:
        self.seen.append(params.get('accepted_output_modes'))
        await self.storage.update_task(params['id'], state='completed')
        await self.broker.event_bus.emit(
            params['id'],
            StreamResponse(
                status_update=TaskStatusUpdateEvent(
                    task_id=params['id'], context_id=params['context_id'], status=TaskStatus(state='completed')
                )
            ),
        )
        await self.broker.event_bus.close(params['id'])

    async def cancel_task(self, params: TaskIdParams) -> None:
        pass

    def build_message_history(self, history: list[Message]) -> list[Any]:
        return []

    def build_artifacts(self, result: Any) -> list[Artifact]:
        return []


def build_app(**card: Any) -> tuple[FastA2A, RecordingWorker]:
    storage: InMemoryStorage[Any] = InMemoryStorage()
    broker = InMemoryBroker()
    worker = RecordingWorker(broker=broker, storage=storage)

    @asynccontextmanager
    async def lifespan(app: FastA2A) -> AsyncIterator[None]:
        async with app.task_manager, worker.run():
            yield

    return FastA2A(storage=storage, broker=broker, lifespan=lifespan, **card), worker


@asynccontextmanager
async def client_for(app: FastA2A) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testclient') as client:
            yield client


def request(method: str, configuration: dict[str, Any] | None) -> dict[str, Any]:
    params: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [{'kind': 'text', 'text': 'hello'}],
            'kind': 'message',
            'messageId': str(uuid.uuid4()),
        }
    }
    if configuration is not None:
        params['configuration'] = configuration
    return {'jsonrpc': '2.0', 'id': str(uuid.uuid4()), 'method': method, 'params': params}


async def test_the_card_declares_the_default_modes_it_is_given():
    app, _ = build_app(default_input_modes=['text/plain'], default_output_modes=['text/markdown', NOTEBOOK])
    async with client_for(app) as client:
        card = (await client.get('/.well-known/agent-card.json')).json()
    assert card['defaultInputModes'] == ['text/plain']
    assert card['defaultOutputModes'] == ['text/markdown', NOTEBOOK]


async def test_unsaid_the_card_keeps_application_json():
    app, _ = build_app()
    async with client_for(app) as client:
        card = (await client.get('/.well-known/agent-card.json')).json()
    assert card['defaultInputModes'] == ['application/json']
    assert card['defaultOutputModes'] == ['application/json']


@pytest.mark.parametrize(
    'modes, refusal',
    [
        ([], 'at least one media type'),
        (['notebook'], 'is not a media type'),
        (['text/plain', 'text/plain'], 'twice'),
        (['text/plain', 'TEXT/PLAIN'], 'twice'),
        (['text/pla\u0131n'], 'is not a media type'),
        (['te\u212axt/plain'], 'is not a media type'),
        ('text/plain', 'not one string'),
    ],
)
def test_a_mode_that_is_not_a_media_type_is_refused(modes: Any, refusal: str):
    with pytest.raises((ValueError, TypeError), match=refusal):
        FastA2A(storage=InMemoryStorage(), broker=InMemoryBroker(), default_output_modes=modes)


@pytest.mark.parametrize('method', ['message/send', 'SendMessage'])
async def test_the_worker_sees_the_modes_a_request_accepts(method: str):
    app, worker = build_app(default_output_modes=['text/markdown', NOTEBOOK])
    async with client_for(app) as client:
        response = await client.post('/', json=request(method, {'acceptedOutputModes': [NOTEBOOK, 'text/markdown']}))
    assert response.status_code == 200
    assert worker.seen == [[NOTEBOOK, 'text/markdown']]


async def test_a_stream_hands_the_modes_to_the_worker_too():
    app, worker = build_app()
    async with client_for(app) as client:
        async with client.stream(
            'POST', '/', json=request('message/stream', {'acceptedOutputModes': [NOTEBOOK]})
        ) as response:
            async for _ in response.aiter_lines():
                pass
    assert worker.seen == [[NOTEBOOK]]


@pytest.mark.parametrize('configuration', [None, {'acceptedOutputModes': []}])
async def test_no_modes_named_leaves_them_unsaid(configuration: dict[str, Any] | None):
    app, worker = build_app()
    async with client_for(app) as client:
        await client.post('/', json=request('message/send', configuration))
    assert worker.seen == [None]
