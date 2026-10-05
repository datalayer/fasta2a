"""A2A 1.0 JSON-RPC: the method names and enum values a 1.0 client speaks."""

from __future__ import annotations as _annotations

import json
from typing import Any

import pytest

from fasta2a.applications import FastA2A
from fasta2a.broker import InMemoryBroker
from fasta2a.jsonrpc_v1 import from_v1_request, to_v1
from fasta2a.storage import InMemoryStorage

from .test_applications import create_test_client
from .test_streaming import create_streaming_app

pytestmark = pytest.mark.anyio


def _v1_message(method: str) -> dict[str, Any]:
    """What `@a2a-js/sdk` 1.x sends."""
    return {
        'jsonrpc': '2.0',
        'id': 1,
        'method': method,
        'params': {
            'tenant': '',
            'message': {'messageId': 'm-1', 'role': 'ROLE_USER', 'parts': [{'text': 'Hello'}]},
            'configuration': {'returnImmediately': False},
        },
    }


def _events(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[len('data: ') :]) for line in body.splitlines() if line.startswith('data: ')]


async def test_a_1_0_stream_is_answered_with_1_0_enums():
    async with create_streaming_app() as client:
        response = await client.post('/', json=_v1_message('SendStreamingMessage'))
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    results = [event['result'] for event in _events(response.text)]
    assert results[0]['task']['status']['state'] == 'TASK_STATE_SUBMITTED'
    assert results[0]['task']['history'][0]['role'] == 'ROLE_USER'
    states = [result['statusUpdate']['status']['state'] for result in results if 'statusUpdate' in result]
    assert states == ['TASK_STATE_WORKING', 'TASK_STATE_COMPLETED']


async def test_a_1_0_send_and_get_are_answered_with_1_0_enums():
    async with create_streaming_app() as client:
        sent = (await client.post('/', json=_v1_message('SendMessage'))).json()
        assert sent['result']['task']['status']['state'] == 'TASK_STATE_SUBMITTED'
        task_id = sent['result']['task']['id']
        got = (
            await client.post('/', json={'jsonrpc': '2.0', 'id': 2, 'method': 'GetTask', 'params': {'id': task_id}})
        ).json()
    assert got['result']['id'] == task_id
    assert got['result']['status']['state'].startswith('TASK_STATE_')


async def test_the_names_this_library_used_are_answered_as_before():
    request = _v1_message('message/send')
    request['params'] = {'message': {'messageId': 'm-1', 'role': 'user', 'parts': [{'text': 'Hello'}]}}
    async with create_streaming_app() as client:
        sent = (await client.post('/', json=request)).json()
    assert sent['result']['task']['status']['state'] == 'submitted'


def test_a_1_0_request_is_read_as_the_method_it_names():
    request = from_v1_request(_v1_message('SendStreamingMessage'))
    assert request is not None
    assert request['method'] == 'message/stream'
    assert request['params']['message']['role'] == 'user'
    assert 'tenant' not in request['params']
    assert request['params']['configuration'] == {'acceptedOutputModes': []}
    assert from_v1_request({'method': 'message/stream', 'params': {}}) is None
    assert from_v1_request(['not', 'a', 'request']) is None


def test_an_answer_is_written_with_1_0_enums():
    assert to_v1({'status': {'state': 'input-required'}, 'history': [{'role': 'agent'}]}) == {
        'status': {'state': 'TASK_STATE_INPUT_REQUIRED'},
        'history': [{'role': 'ROLE_AGENT'}],
    }


def test_application_data_and_metadata_keep_their_values_both_ways():
    data = {'role': 'ROLE_AGENT', 'state': 'working', 'nested': [{'state': 'TASK_STATE_FAILED'}]}
    metadata = {'role': 'agent', 'state': 'TASK_STATE_WORKING'}
    request = from_v1_request(
        {
            'jsonrpc': '2.0',
            'id': '1',
            'method': 'SendMessage',
            'params': {
                'message': {
                    'role': 'ROLE_USER',
                    'messageId': 'm',
                    'parts': [{'kind': 'data', 'data': data, 'metadata': metadata}],
                    'metadata': metadata,
                }
            },
        }
    )
    assert request is not None
    message = request['params']['message']
    assert message['role'] == 'user'
    assert message['parts'][0]['data'] == data
    assert message['parts'][0]['metadata'] == metadata
    assert message['metadata'] == metadata
    answer = to_v1(
        {
            'status': {'state': 'working'},
            'artifacts': [{'parts': [{'kind': 'data', 'data': data, 'metadata': metadata}]}],
            'metadata': metadata,
        }
    )
    assert answer['status'] == {'state': 'TASK_STATE_WORKING'}
    assert answer['artifacts'][0]['parts'][0] == {'kind': 'data', 'data': data, 'metadata': metadata}
    assert answer['metadata'] == metadata


def test_list_tasks_reads_its_status_filter_as_a_task_state():
    request = from_v1_request(
        {'jsonrpc': '2.0', 'id': '1', 'method': 'ListTasks', 'params': {'status': 'TASK_STATE_WORKING'}}
    )
    assert request is not None
    assert request['params']['status'] == 'working'


async def test_the_card_says_how_a_caller_authenticates():
    app = FastA2A(
        storage=InMemoryStorage(),
        broker=InMemoryBroker(),
        security_schemes={'bearer': {'http_auth_security_scheme': {'scheme': 'Bearer', 'bearer_format': 'JWT'}}},
        security_requirements=[{'schemes': {'bearer': []}}],
    )
    async with create_test_client(app) as client:
        card = (await client.get('/.well-known/agent-card.json')).json()
    assert card['securitySchemes'] == {
        'bearer': {'httpAuthSecurityScheme': {'scheme': 'Bearer', 'bearerFormat': 'JWT'}}
    }
    assert card['securityRequirements'] == [{'schemes': {'bearer': []}}]
