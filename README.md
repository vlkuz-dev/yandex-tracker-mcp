# yandex-tracker-mcp

MCP server for Yandex Tracker API v3 built with `fastmcp` and `httpx`.

## Project status

- Stable MCP tool naming (`tracker_<domain>_<action>`)
- CI checks: lint + typecheck + tests
- Tag-based GitHub release workflow (optional PyPI publish)

## Features

- Hybrid interface:
  - typed tools for common Tracker entities/actions
  - raw v3 request tool for broad coverage
- Supports both auth styles:
  - OAuth/Bearer token
  - `X-Org-ID` or `X-Cloud-Org-ID`
- Unified pagination envelope for list/search typed tools:
  - `results`, `count`, `next`, `prev`
- Multiple MCP transports:
  - `stdio`
  - `streamable-http`

## Installation

```bash
uv pip install yandex-tracker-mcp
```

For development:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]"
make check
```

## Configuration

Required:

- `YANDEX_TRACKER_TOKEN`
- one of:
  - `YANDEX_TRACKER_ORG_ID`
  - `YANDEX_TRACKER_CLOUD_ORG_ID`

Optional:

- `YANDEX_TRACKER_TOKEN_TYPE` (`OAuth` by default, supports `Bearer`)
- `YANDEX_TRACKER_BASE_URL` (default: `https://api.tracker.yandex.net`)
- `YANDEX_TRACKER_TIMEOUT_SECONDS` (default: `30`)
- `YANDEX_TRACKER_RETRIES` (default: `2`)
- `YANDEX_TRACKER_USER_AGENT` (default: `yandex-tracker-mcp/0.1.0`)

## Run

### stdio

```bash
tracker-mcp-stdio
```

or

```bash
tracker-mcp
```

### streamable-http

```bash
tracker-mcp-http --host 0.0.0.0 --port 8000 --path /mcp
```

## MCP client config example

```toml
[mcp_servers.yandex-tracker]
command = "tracker-mcp-stdio"

[mcp_servers.yandex-tracker.env]
YANDEX_TRACKER_TOKEN = "replace_me"
YANDEX_TRACKER_ORG_ID = "replace_me"
```

## Tools

### Typed tools

Typed tools are generated from operation registry and follow this naming:

```text
tracker_<domain>_<action>
```

Examples:

- `tracker_issue_get`
- `tracker_issue_create`
- `tracker_queue_get_metadata`
- `tracker_user_get_current`

Common parameters:

- `path_params`: object for path variables
- `query`: object for query parameters
- `body`: object or array for request body

### Raw tool

`tracker_raw_request` allows direct calls to Tracker v3 while enforcing v3-domain guardrails.

Parameters:

- `method`
- `path`
- `query` (optional)
- `body` (optional)

## Development

```bash
uv run --python .venv/bin/python --no-sync ruff check .
uv run --python .venv/bin/python --no-sync mypy src
uv run --python .venv/bin/python --no-sync pytest
```

## Repository docs

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Release guide](docs/RELEASE.md)
- [Changelog](CHANGELOG.md)

## Operation registry sync

The repository includes `scripts/sync_tracker_operations.py` to refresh operation metadata from
Yandex Tracker docs pages. It updates:

- `src/yandex_tracker_mcp/operations.json`
