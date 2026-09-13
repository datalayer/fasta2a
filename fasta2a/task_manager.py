"""This module defines the TaskManager class, which is responsible for managing tasks.

In our structure, we have the following components:

- TaskManager: A class that manages tasks.
- Scheduler: A class that schedules tasks to be sent to the worker.
- Worker: A class that executes tasks.
- Runner: A class that defines how tasks run and how history is structured.
- Storage: A class that stores tasks and artifacts.

Architecture:
```
  +-----------------+
  |   HTTP Server   |
  +-------+---------+
          ^
          | Sends Requests/
          | Receives Results
          v
  +-------+---------+
  |                 |
  |   TaskManager   |<-----------------+
  |  (coordinates)  |                  |
  |                 |                  |
  +-------+---------+                  |
          |                            |
          |  Schedules Tasks           |
          v                            v
  +------------------+         +----------------+
  |                  |         |                |
  |      Broker      | .       |    Storage     |
  |     (queues) .   |         | (persistence)  |
  |                  |         |                |
  +------------------+         +----------------+
          ^                            ^
          |                            |
          | Delegates Execution        |
          v                            |
  +------------------+                 |
  |                  |                 |
  |      Worker      |                 |
  | (implementation) |-----------------+
  |                  |
  +------------------+
```

The flow:
1. The HTTP server sends a task to TaskManager
2. TaskManager stores initial task state in Storage
3. TaskManager passes task to Scheduler
4. Scheduler determines when to send tasks to Worker
5. Worker delegates to Runner for task execution
6. Runner defines how tasks run and how history is structured
7. Worker processes task results from Runner
8. Worker reads from and writes to Storage directly
9. Worker updates task status in Storage as execution progresses
10. TaskManager can also read/write from Storage for task management
11. Client queries TaskManager for results, which reads from Storage
"""

from __future__ import annotations as _annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from .broker import Broker
from .schema import (
    STREAM_ENDING_STATES,
    CancelTaskRequest,
    CancelTaskResponse,
    DeleteTaskPushNotificationConfigRequest,
    DeleteTaskPushNotificationConfigResponse,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    GetTaskRequest,
    GetTaskResponse,
    ListTaskPushNotificationConfigRequest,
    ListTaskPushNotificationConfigResponse,
    ListTasksRequest,
    ListTasksResponse,
    PushNotificationNotSupportedError,
    ResubscribeTaskRequest,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageResult,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    StreamMessageRequest,
    StreamMessageResponse,
    StreamResponse,
    TaskNotFoundError,
    TaskSendParams,
    UnsupportedOperationError,
    stream_message_response_ta,
)
from .storage import Storage


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks."""

    broker: Broker
    storage: Storage[Any]

    _aexit_stack: AsyncExitStack | None = field(default=None, init=False)
    _depth: int = field(default=0, init=False)

    async def __aenter__(self):
        # Entering an already-running task manager is a no-op, so that a lifespan which
        # enters it explicitly can be nested inside the application's default lifespan.
        self._depth += 1
        if self._aexit_stack is not None:
            return self

        self._aexit_stack = AsyncExitStack()
        await self._aexit_stack.__aenter__()
        await self._aexit_stack.enter_async_context(self.broker)

        return self

    @property
    def is_running(self) -> bool:
        return self._aexit_stack is not None

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        if self._aexit_stack is None:
            raise RuntimeError('TaskManager was not properly initialized.')
        self._depth -= 1
        if self._depth > 0:
            return
        await self._aexit_stack.__aexit__(exc_type, exc_value, traceback)
        self._aexit_stack = None

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol."""
        request_id = request['id']
        message = request['params']['message']
        context_id = message.get('context_id', str(uuid.uuid4()))

        task = await self.storage.submit_task(context_id, message)

        broker_params: TaskSendParams = {'id': task['id'], 'context_id': context_id, 'message': message}
        config = request['params'].get('configuration', {})
        history_length = config.get('history_length')
        if history_length is not None:
            broker_params['history_length'] = history_length
        metadata = request['params'].get('metadata')
        if metadata:
            broker_params['metadata'] = metadata

        await self.broker.run_task(broker_params)
        result = SendMessageResult(task=task)
        return SendMessageResponse(jsonrpc='2.0', id=request_id, result=result)

    async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Get a task, and return it to the client.

        No further actions are needed here.
        """
        task_id = request['params']['id']
        history_length = request['params'].get('history_length')
        task = await self.storage.load_task(task_id, history_length)
        if task is None:
            return GetTaskResponse(
                jsonrpc='2.0',
                id=request['id'],
                error=TaskNotFoundError(code=-32001, message='Task not found'),
            )
        return GetTaskResponse(jsonrpc='2.0', id=request['id'], result=task)

    async def cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        await self.broker.cancel_task(request['params'])
        task = await self.storage.load_task(request['params']['id'])
        if task is None:
            return CancelTaskResponse(
                jsonrpc='2.0',
                id=request['id'],
                error=TaskNotFoundError(code=-32001, message='Task not found'),
            )
        return CancelTaskResponse(jsonrpc='2.0', id=request['id'], result=task)

    async def stream_message(self, request: StreamMessageRequest) -> AsyncIterator[bytes]:
        """Stream a message response as SSE events."""
        request_id = request['id']
        message = request['params']['message']
        context_id = message.get('context_id', str(uuid.uuid4()))

        task = await self.storage.submit_task(context_id, message)
        task_id = task['id']

        broker_params: TaskSendParams = {'id': task_id, 'context_id': context_id, 'message': message}
        config = request['params'].get('configuration', {})
        history_length = config.get('history_length')
        if history_length is not None:
            broker_params['history_length'] = history_length
        metadata = request['params'].get('metadata')
        if metadata:
            broker_params['metadata'] = metadata

        async with self.broker.event_bus.subscribe(task_id) as receive_stream:
            await self.broker.run_task(broker_params)

            # Send initial task state
            initial_response = StreamMessageResponse(jsonrpc='2.0', id=request_id, result=StreamResponse(task=task))
            yield self._format_sse_event(initial_response)

            async for event in receive_stream:
                response = StreamMessageResponse(jsonrpc='2.0', id=request_id, result=event)
                yield self._format_sse_event(response)

    async def resubscribe_task(self, request: ResubscribeTaskRequest) -> AsyncIterator[bytes]:
        """Resubscribe to an existing task's event stream."""
        request_id = request['id']
        task_id = request['params']['id']

        task = await self.storage.load_task(task_id)
        if task is None:
            error_response = StreamMessageResponse(
                jsonrpc='2.0',
                id=request_id,
                error=TaskNotFoundError(code=-32001, message='Task not found'),
            )
            yield self._format_sse_event(error_response)
            return

        # Send current task state
        initial_response = StreamMessageResponse(jsonrpc='2.0', id=request_id, result=StreamResponse(task=task))
        yield self._format_sse_event(initial_response)

        # A task at one of these states has ended its stream: nothing more to wait for.
        if task['status']['state'] in STREAM_ENDING_STATES:
            return

        async with self.broker.event_bus.subscribe(task_id) as receive_stream:
            async for event in receive_stream:
                response = StreamMessageResponse(jsonrpc='2.0', id=request_id, result=event)
                yield self._format_sse_event(response)

    @staticmethod
    def _format_sse_event(response: StreamMessageResponse) -> bytes:
        """Format a StreamMessageResponse as an SSE event."""
        data = stream_message_response_ta.dump_json(response, by_alias=True)
        return b'data: ' + data + b'\n\n'

    async def set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        return SetTaskPushNotificationResponse(
            jsonrpc='2.0',
            id=request['id'],
            error=PushNotificationNotSupportedError(code=-32003, message='Push notification not supported'),
        )

    async def get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        return GetTaskPushNotificationResponse(
            jsonrpc='2.0',
            id=request['id'],
            error=PushNotificationNotSupportedError(code=-32003, message='Push notification not supported'),
        )

    async def list_task_push_notification_configs(
        self, request: ListTaskPushNotificationConfigRequest
    ) -> ListTaskPushNotificationConfigResponse:
        return ListTaskPushNotificationConfigResponse(
            jsonrpc='2.0',
            id=request['id'],
            error=PushNotificationNotSupportedError(code=-32003, message='Push notification not supported'),
        )

    async def delete_task_push_notification_config(
        self, request: DeleteTaskPushNotificationConfigRequest
    ) -> DeleteTaskPushNotificationConfigResponse:
        return DeleteTaskPushNotificationConfigResponse(
            jsonrpc='2.0',
            id=request['id'],
            error=PushNotificationNotSupportedError(code=-32003, message='Push notification not supported'),
        )

    async def list_tasks(self, request: ListTasksRequest) -> ListTasksResponse:
        return ListTasksResponse(
            jsonrpc='2.0',
            id=request['id'],
            error=UnsupportedOperationError(code=-32004, message='This operation is not supported'),
        )
