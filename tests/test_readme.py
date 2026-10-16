"""Exercise the framework-independent example exactly as documented."""

from __future__ import annotations as _annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest

from .test_applications import create_test_client

pytestmark = pytest.mark.anyio


async def test_readme_worker_example():
    readme = (Path(__file__).parents[1] / 'README.md').read_text(encoding='utf-8')
    code = readme.split('```python', 1)[1].split('```', 1)[0]
    namespace: dict[str, Any] = {}
    exec(compile(code, 'README.md', 'exec'), namespace)

    async with create_test_client(namespace['app']) as client:
        with anyio.fail_after(5):
            response = await client.post(
                '/',
                json={
                    'jsonrpc': '2.0',
                    'id': 'readme',
                    'method': 'message/stream',
                    'params': {
                        'message': {'role': 'user', 'messageId': 'readme-message', 'parts': [{'text': 'hello'}]}
                    },
                },
            )
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        assert events[-1]['result']['statusUpdate']['status']['state'] == 'completed'
        task_id = events[0]['result']['task']['id']
        task = (
            await client.post(
                '/', json={'jsonrpc': '2.0', 'id': 'get', 'method': 'tasks/get', 'params': {'id': task_id}}
            )
        ).json()['result']
        assert task['history'][-1]['parts'] == [{'text': 'Your context is 2 messages long.'}]
        assert task['history'][-1]['role'] == 'agent'
