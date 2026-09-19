# AGENTS.md

Guidance for coding agents working in this repository.

## Project

FastA2A is a Python library, built on Starlette and Pydantic, that serves an AI
agent as an A2A (Agent-to-Agent) server. It implements the A2A protocol v1.

## Commands

- `scripts/install` — install dependencies (`uv sync --frozen`)
- `scripts/test` — the tests with coverage (`uv run coverage run -m pytest`);
  pytest arguments pass through, e.g. `scripts/test tests/test_streaming.py`
- `scripts/lint` — fix and format (`uvx ruff check --fix && uvx ruff format`)
- `scripts/check` — what CI runs: ruff format and lint, `pyright`,
  `check-sdist`, `uv lock`

## Layout (`fasta2a/`)

- `applications.py` — `FastA2A`, the Starlette application: the agent card, the
  JSON-RPC endpoint and a docs page (`docs_url`, `/docs` by default)
- `task_manager.py` — `TaskManager`, between the broker and the storage
- `broker.py` — `Broker` schedules tasks; `InMemoryBroker`
- `storage.py` — `Storage` keeps tasks and their context; `InMemoryStorage`
- `worker.py` — `Worker` runs the tasks the broker hands out
- `event_bus.py` — `EventBus`, the task events streaming reads; `InMemoryEventBus`
- `extensions.py` — A2A extensions: the `A2A-Extensions` header and which
  extensions a request activates
- `client.py` — `A2AClient`
- `schema.py` — the A2A protocol types, as Pydantic `TypedDict`s
- `pydantic_ai/` — the Pydantic AI bridge (the `pydantic-ai` extra)

## Endpoints

- `/.well-known/agent-card.json` (GET, HEAD, OPTIONS) — the agent card
- `/` (POST) — JSON-RPC 2.0: `message/send`, `message/stream`, `tasks/get`,
  `tasks/list`, `tasks/cancel`, `tasks/resubscribe` and the push notification
  config methods. `message/stream` and `tasks/resubscribe` answer with
  server-sent events.

## A2A v1 shapes

- Python field names are snake_case; the wire is camelCase, through the
  `to_camel` alias generator — dump with `by_alias=True`.
- A `Part` is flat: exactly one of `text`, `raw` (base64), `url` or `data`.
  Parts, messages and tasks carry no `kind`.
- A `message/send` result is `{"task": …}` or `{"message": …}`.
