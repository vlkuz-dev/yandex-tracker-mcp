# Contributing

## Development setup

1. Create environment:
   - `uv venv .venv`
2. Install dependencies:
   - `uv pip install --python .venv/bin/python -e ".[dev]"`

## Validate changes

Run before opening a pull request:

- `uv run --python .venv/bin/python --no-sync ruff check .`
- `uv run --python .venv/bin/python --no-sync mypy src`
- `uv run --python .venv/bin/python --no-sync pytest`

## Coding rules

- Keep public MCP tool names stable (`tracker_<domain>_<action>`).
- Preserve backwards compatibility for tool arguments/response shapes in minor releases.
- New list/search tools should return unified pagination envelope:
  - `results`, `count`, `next`, `prev`.
- Raw tool must remain restricted to Tracker API v3 namespaces.

## Pull request checklist

- Change is covered by tests.
- Docs/README updated if behavior changed.
- No secrets or personal tokens in code, logs, or examples.
- Changelog updated under `[Unreleased]` for user-facing changes.
