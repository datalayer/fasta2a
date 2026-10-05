from __future__ import annotations as _annotations

import html
import json
import re
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route
from starlette.types import ExceptionHandler, Lifespan, Receive, Scope, Send

from .broker import Broker
from .extensions import (
    A2A_EXTENSIONS_HEADER,
    ACTIVATED_EXTENSIONS_KEY,
    format_extensions_header,
    missing_required_extensions,
    parse_extensions_header,
    select_activated_extensions,
)
from .jsonrpc_v1 import from_v1_request, to_v1_json, to_v1_sse
from .schema import (
    A2ARequest,
    A2AResponse,
    AgentCapabilities,
    AgentCard,
    AgentExtension,
    AgentInterface,
    AgentProvider,
    InvalidRequestError,
    SecurityRequirement,
    SecurityScheme,
    SendMessageResponse,
    Skill,
    a2a_request_ta,
    a2a_response_ta,
    agent_card_ta,
)
from .storage import Storage
from .task_manager import TaskManager


class FastA2A(Starlette):
    """The main class for the FastA2A library."""

    def __init__(
        self,
        *,
        storage: Storage,
        broker: Broker,
        # Agent card
        name: str | None = None,
        url: str = 'http://localhost:8000',
        version: str = '1.0.0',
        description: str | None = None,
        provider: AgentProvider | None = None,
        skills: list[Skill] | None = None,
        extensions: list[AgentExtension] | None = None,
        security_schemes: dict[str, SecurityScheme] | None = None,
        security_requirements: list[SecurityRequirement] | None = None,
        docs_url: str | None = '/docs',
        default_input_modes: Sequence[str] | None = None,
        default_output_modes: Sequence[str] | None = None,
        # Starlette
        debug: bool = False,
        routes: Sequence[Route] | None = None,
        middleware: Sequence[Middleware] | None = None,
        exception_handlers: dict[Any, ExceptionHandler] | None = None,
        lifespan: Lifespan[FastA2A] | None = None,
    ):
        if lifespan is None:
            lifespan = _default_lifespan

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            exception_handlers=exception_handlers,
            lifespan=lifespan,
        )

        self.name = name or 'My Agent'
        self.url = url
        self.version = version
        self.description = description
        self.provider = provider
        self.skills = skills or []
        self.extensions = extensions or []
        # What the card says a caller authenticates with. Said, not enforced:
        # the server checks it in a middleware of its own (`middleware`).
        self.security_schemes = security_schemes
        self.security_requirements = security_requirements
        self.docs_url = docs_url
        # The media types the agent takes and gives unless a skill says otherwise. A client
        # names the ones it accepts in a request (`acceptedOutputModes`), which the worker
        # reads from its task's params (`accepted_output_modes`).
        self.default_input_modes = _media_types('default_input_modes', default_input_modes)
        self.default_output_modes = _media_types('default_output_modes', default_output_modes)

        self.task_manager = TaskManager(broker=broker, storage=storage)

        # Setup
        self._agent_card_json_schema: bytes | None = None
        self.router.add_route(
            '/.well-known/agent-card.json', self._agent_card_endpoint, methods=['HEAD', 'GET', 'OPTIONS']
        )
        self.router.add_route('/', self._agent_run_endpoint, methods=['POST'])

        if self.docs_url is not None:
            self.router.add_route(self.docs_url, self._docs_endpoint, methods=['GET'])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'http' and not self.task_manager.is_running:
            raise RuntimeError('TaskManager was not properly initialized.')
        await super().__call__(scope, receive, send)

    async def _agent_card_endpoint(self, request: Request) -> Response:
        if self._agent_card_json_schema is None:
            agent_card = AgentCard(
                name=self.name,
                description=self.description or 'An AI agent exposed as an A2A agent.',
                version=self.version,
                supported_interfaces=[
                    AgentInterface(protocol_binding='JSONRPC', url=self.url, protocol_version='1.0'),
                ],
                skills=self.skills,
                default_input_modes=self.default_input_modes,
                default_output_modes=self.default_output_modes,
                capabilities=self._capabilities(),
            )
            if self.provider is not None:
                agent_card['provider'] = self.provider
            if self.security_schemes:
                agent_card['security_schemes'] = self.security_schemes
            if self.security_requirements:
                agent_card['security_requirements'] = self.security_requirements
            self._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)
        return Response(content=self._agent_card_json_schema, media_type='application/json')

    def _capabilities(self) -> AgentCapabilities:
        capabilities = AgentCapabilities(streaming=True, push_notifications=False)
        if self.extensions:
            capabilities['extensions'] = list(self.extensions)
        return capabilities

    def _negotiate_extensions(self, request: Request) -> list[str]:
        """The extensions this request activates: the ones it asked for that the agent supports."""
        requested = parse_extensions_header(request.headers.get(A2A_EXTENSIONS_HEADER))
        return select_activated_extensions(self.extensions, requested)

    async def _docs_endpoint(self, request: Request) -> Response:
        """Serve the documentation interface."""
        docs_path = Path(__file__).parent / 'static' / 'docs.html'
        root_path = request.scope.get('root_path', '').rstrip('/')
        content = docs_path.read_text()
        content = content.replace('__FASTA2A_API_ROOT_JSON__', json.dumps(root_path))
        content = content.replace('__FASTA2A_API_ROOT__', html.escape(root_path, quote=True))
        return Response(content=content, media_type='text/html')

    async def _agent_run_endpoint(self, request: Request) -> Response:
        """This is the main endpoint for the A2A server.

        Although the specification allows freedom of choice and implementation, I'm pretty sure about some decisions.

        1. The server will always either send a "submitted" or a "failed" on `message/send`.
            Never a "completed" on the first message.
        2. There are three possible ends for the task:
            2.1. The task was "completed" successfully.
            2.2. The task was "canceled".
            2.3. The task "failed".
        3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
        """
        data = await request.body()
        # A request with an A2A 1.0 method name is read as the method it names,
        # and answered with 1.0's enums (see `jsonrpc_v1`).
        try:
            v1_request = from_v1_request(json.loads(data))
        except ValueError:
            v1_request = None
        if v1_request is not None:
            data = json.dumps(v1_request).encode()
        a2a_request = a2a_request_ta.validate_json(data)
        response = await self._answer(request, a2a_request)
        if v1_request is None:
            return response
        if isinstance(response, StreamingResponse):
            return StreamingResponse(
                to_v1_sse(response.body_iterator),  # type: ignore[arg-type]
                media_type='text/event-stream',
                headers={k: v for k, v in response.headers.items() if k.lower() != 'content-type'},
            )
        return Response(
            content=to_v1_json(bytes(response.body)),
            media_type='application/json',
            headers={k: v for k, v in response.headers.items() if k.lower() not in ('content-length', 'content-type')},
        )

    async def _answer(self, request: Request, a2a_request: A2ARequest) -> Response:
        """Answer one A2A request, as this library names its methods."""

        # Extensions are negotiated per request: the client names the ones it
        # wants in the `A2A-Extensions` header, the agent activates those it
        # supports and says which in the same header on its response. A message
        # that leaves a *required* extension inactive is refused before a task
        # is created for it, and the activated list rides in the message
        # metadata so the worker sees what was agreed.
        activated = self._negotiate_extensions(request)
        headers = {A2A_EXTENSIONS_HEADER: format_extensions_header(activated)} if activated else {}
        # Two comparisons rather than `in`: that is what narrows the request
        # union to the two whose params carry a message and its metadata.
        if a2a_request['method'] == 'message/send' or a2a_request['method'] == 'message/stream':
            missing = missing_required_extensions(self.extensions, activated)
            if missing:
                error_response = SendMessageResponse(
                    jsonrpc='2.0',
                    id=a2a_request['id'],
                    error=InvalidRequestError(
                        code=-32600,
                        message='Request payload validation error',
                        data={'missing_required_extensions': missing},
                    ),
                )
                return Response(
                    content=a2a_response_ta.dump_json(error_response, by_alias=True),
                    media_type='application/json',
                    headers=headers,
                )
            if activated:
                metadata = dict(a2a_request['params'].get('metadata') or {})
                metadata[ACTIVATED_EXTENSIONS_KEY] = activated
                a2a_request['params']['metadata'] = metadata

        jsonrpc_response: A2AResponse
        if a2a_request['method'] == 'message/send':
            jsonrpc_response = await self.task_manager.send_message(a2a_request)
        elif a2a_request['method'] == 'tasks/get':
            jsonrpc_response = await self.task_manager.get_task(a2a_request)
        elif a2a_request['method'] == 'tasks/cancel':
            jsonrpc_response = await self.task_manager.cancel_task(a2a_request)
        elif a2a_request['method'] == 'tasks/pushNotification/set':
            jsonrpc_response = await self.task_manager.set_task_push_notification(a2a_request)
        elif a2a_request['method'] == 'tasks/pushNotification/get':
            jsonrpc_response = await self.task_manager.get_task_push_notification(a2a_request)
        elif a2a_request['method'] == 'tasks/pushNotificationConfig/list':
            jsonrpc_response = await self.task_manager.list_task_push_notification_configs(a2a_request)
        elif a2a_request['method'] == 'tasks/pushNotificationConfig/delete':
            jsonrpc_response = await self.task_manager.delete_task_push_notification_config(a2a_request)
        elif a2a_request['method'] == 'tasks/list':
            jsonrpc_response = await self.task_manager.list_tasks(a2a_request)
        elif a2a_request['method'] == 'message/stream':
            return StreamingResponse(
                self.task_manager.stream_message(a2a_request),
                media_type='text/event-stream',
                headers=headers,
            )
        elif a2a_request['method'] == 'tasks/resubscribe':
            return StreamingResponse(
                self.task_manager.resubscribe_task(a2a_request),
                media_type='text/event-stream',
                headers=headers,
            )
        else:
            raise NotImplementedError(f'Method {a2a_request["method"]} not implemented.')
        return Response(
            content=a2a_response_ta.dump_json(jsonrpc_response, by_alias=True),
            media_type='application/json',
            headers=headers,
        )


@asynccontextmanager
async def _default_lifespan(app: FastA2A) -> AsyncIterator[None]:
    async with app.task_manager:
        yield


def _media_types(name: str, modes: Sequence[str] | None) -> list[str]:
    """The media types the card declares, `application/json` when unsaid; a mode that is not one is refused."""
    if modes is None:
        return ['application/json']
    if isinstance(modes, str):
        raise TypeError(f'{name} is a list of media types, not one string.')
    declared = list(modes)
    if not declared:
        raise ValueError(f'{name} names at least one media type.')
    for mode in declared:
        if not isinstance(mode, str) or not _MEDIA_TYPE.fullmatch(mode):
            raise ValueError(f'{name}: {mode!r} is not a media type (type/subtype).')
    if len(set(declared)) != len(declared):
        raise ValueError(f'{name} names a media type twice.')
    return declared


_MEDIA_TYPE = re.compile(r'[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*', re.IGNORECASE)
