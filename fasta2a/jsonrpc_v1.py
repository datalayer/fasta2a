"""A2A 1.0 JSON-RPC method names and enum values.

The agent card says the server speaks A2A 1.0 (`protocolVersion: "1.0"`), and its
objects have the 1.0 shape. The JSON-RPC binding of 1.0 also renamed the methods
(`message/stream` is `SendStreamingMessage`) and writes enums as their proto names
(`working` is `TASK_STATE_WORKING`, `agent` is `ROLE_AGENT`). A 1.0 client, such as
`@a2a-js/sdk` 1.x or `a2a-sdk` 1.x, sends the new names and reads the new values.

The server answers both. A request made with a 1.0 method name is read as the
method it names, its enums read as this library's, and its answer, JSON or event
stream, is written with 1.0's enums. A request made with the names this library
has always used is answered exactly as before.
"""

from __future__ import annotations as _annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

__all__ = (
    'V1_METHODS',
    'from_v1_request',
    'to_v1',
    'to_v1_json',
    'to_v1_sse',
)

V1_METHODS: dict[str, str] = {
    'SendMessage': 'message/send',
    'SendStreamingMessage': 'message/stream',
    'GetTask': 'tasks/get',
    'CancelTask': 'tasks/cancel',
    'SubscribeToTask': 'tasks/resubscribe',
    'ListTasks': 'tasks/list',
}
"""The A2A 1.0 JSON-RPC methods this server answers, by the name it gives them."""

_ROLE_FROM_V1 = {'ROLE_USER': 'user', 'ROLE_AGENT': 'agent'}
_ROLE_TO_V1 = {value: key for key, value in _ROLE_FROM_V1.items()}
_STATES = (
    'submitted',
    'working',
    'input-required',
    'completed',
    'canceled',
    'failed',
    'rejected',
    'auth-required',
)
_STATE_TO_V1 = {state: 'TASK_STATE_' + state.upper().replace('-', '_') for state in _STATES}
_STATE_FROM_V1 = {value: key for key, value in _STATE_TO_V1.items()}


def _object(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value)


def _array(value: Any) -> list[Any]:
    return cast(list[Any], value)


# A part's `data` and any `metadata` are the application's, not the protocol's:
# their `role` or `state` keys are values, copied as they are in both directions.
_APPLICATION_KEYS = frozenset({'data', 'metadata'})


def _enums_from_v1(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in _object(value).items():
            if key in _APPLICATION_KEYS:
                out[key] = item
            elif key == 'role' and isinstance(item, str):
                out[key] = _ROLE_FROM_V1.get(item, item)
            elif key == 'state' and isinstance(item, str):
                out[key] = _STATE_FROM_V1.get(item, item)
            else:
                out[key] = _enums_from_v1(item)
        return out
    if isinstance(value, list):
        return [_enums_from_v1(item) for item in _array(value)]
    return value


def to_v1(value: Any) -> Any:
    """A result of this server with its enums as A2A 1.0 writes them: `ROLE_*` and `TASK_STATE_*`."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in _object(value).items():
            if key in _APPLICATION_KEYS:
                out[key] = item
            elif key == 'role' and isinstance(item, str):
                out[key] = _ROLE_TO_V1.get(item, item)
            elif key == 'state' and isinstance(item, str):
                out[key] = _STATE_TO_V1.get(item, item)
            else:
                out[key] = to_v1(item)
        return out
    if isinstance(value, list):
        return [to_v1(item) for item in _array(value)]
    return value


def from_v1_request(request: Any) -> dict[str, Any] | None:
    """A 1.0 JSON-RPC request as this server reads it, or `None` when it is not one.

    The method is renamed and the enums of its params read as this library's. A
    1.0 request may name a tenant, which an agent served here does not have, and
    its configuration may say `returnImmediately`, which this server does not read
    and which needs `acceptedOutputModes` beside it.
    """
    if not isinstance(request, dict):
        return None
    envelope = _object(request)
    method = envelope.get('method')
    if not isinstance(method, str) or method not in V1_METHODS:
        return None
    params = _object(_enums_from_v1(dict(_object(envelope.get('params') or {}))))
    params.pop('tenant', None)
    # ListTasks filters by `status`, a TaskState rather than a task's status object.
    if method == 'ListTasks' and isinstance(params.get('status'), str):
        params['status'] = _STATE_FROM_V1.get(params['status'], params['status'])
    configuration = params.get('configuration')
    if isinstance(configuration, dict):
        settings = _object(configuration)
        settings.setdefault('acceptedOutputModes', [])
        settings.pop('returnImmediately', None)
    return {**envelope, 'method': V1_METHODS[method], 'params': params}


def to_v1_json(content: bytes) -> bytes:
    """A JSON-RPC answer, its `result` written as 1.0 writes it."""
    answer: Any = json.loads(content)
    if isinstance(answer, dict) and 'result' in answer:
        envelope = _object(answer)
        answer = {**envelope, 'result': to_v1(envelope['result'])}
    return json.dumps(answer, separators=(',', ':')).encode()


async def to_v1_sse(events: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """An event stream of JSON-RPC answers, each one's `result` written as 1.0 writes it."""
    async for event in events:
        if event.startswith(b'data: '):
            yield b'data: ' + to_v1_json(event[len(b'data: ') :].strip()) + b'\n\n'
        else:  # pragma: no cover - the task manager writes only data events
            yield event
