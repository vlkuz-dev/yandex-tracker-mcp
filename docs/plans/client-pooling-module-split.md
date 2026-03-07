# Client Connection Pooling + Module Split

## Overview
- Refactor TrackerClient to use a persistent httpx.AsyncClient with connection pooling instead of creating a new client per request
- Extract pagination normalization into a dedicated module to reduce tools.py complexity
- Introduce proper client lifecycle management via FastMCP lifespan hooks
- Improve extensibility by cleanly separating concerns across modules

## Context (from discovery)
- Files/components involved:
  - `src/yandex_tracker_mcp/client.py` — async HTTP client, creates new httpx.AsyncClient per request (line 41)
  - `src/yandex_tracker_mcp/tools.py` — monolithic: tool registration + handler building + pagination normalization
  - `src/yandex_tracker_mcp/server.py` — server factory, no lifecycle management
  - `src/yandex_tracker_mcp/models.py` — PaginatedEnvelope used by pagination logic
  - `tests/test_client.py` — 4 async tests using respx mocking
  - `tests/test_tools.py` — 2 tests for _normalize_page
- Related patterns: FastMCP lifespan context, httpx.AsyncClient as context manager
- Dependencies: fastmcp>=2.0.0, httpx>=0.27.0, respx for test mocking

## Development Approach
- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task** — no exceptions
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change
- Maintain backward compatibility

## Testing Strategy
- **Unit tests**: required for every task (see Development Approach above)
- Tests use respx for HTTP mocking and pytest-asyncio for async support
- Run via: `make test` or `uv run pytest`

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with + prefix
- Document issues/blockers with ! prefix
- Update plan if implementation deviates from original scope
- Keep plan in sync with actual work done

## Implementation Steps

### Task 1: Refactor TrackerClient to use persistent httpx.AsyncClient
- [x] Add `_http` attribute to `TrackerClient.__init__` initialized as `None`
- [x] Add `async def start(self)` method that creates `httpx.AsyncClient` with connection pooling settings (limits, timeout, headers)
- [x] Add `async def stop(self)` method that closes the underlying `httpx.AsyncClient`
- [x] Add `__aenter__` / `__aexit__` for context manager support
- [x] Refactor `request()` to use `self._http` instead of creating a new client per call — remove the `async with httpx.AsyncClient(...)` block
- [x] Move shared headers and timeout into client construction (set once, not per request)
- [x] Update tests in `test_client.py` to use start/stop lifecycle
- [x] Write tests for start/stop lifecycle (client usable after start, raises after stop)
- [x] Run tests — must pass before next task

### Task 2: Wire client lifecycle into FastMCP lifespan
- [x] Add lifespan async context manager in `server.py` that starts/stops `TrackerClient`
- [x] Pass lifespan to `FastMCP(...)` constructor
- [x] Remove direct `TrackerClient(settings)` construction — use lifespan-managed instance
- [x] Verify server still starts and tools are registered correctly
- [x] Write test for `create_server()` verifying lifespan is configured
- [x] Run tests — must pass before next task

### Task 3: Extract pagination into dedicated module
- [x] Create `src/yandex_tracker_mcp/pagination.py`
- [x] Move `_normalize_page`, `_to_int`, `_to_optional_str` from `tools.py` to `pagination.py`
- [x] Make `normalize_page` a public function (remove underscore prefix)
- [x] Update `tools.py` imports to use `pagination.normalize_page`
- [x] Move tests from `test_tools.py` to new `tests/test_pagination.py`
- [x] Add tests for `_to_int` edge cases (string digits, non-digit strings, None)
- [x] Add tests for `_to_optional_str` edge cases (None, empty, whitespace, valid string)
- [x] Add test for `normalize_page` with `values`/`total` shape (currently untested)
- [x] Add test for `normalize_page` with unrecognized payload (dict without results/values)
- [x] Run tests — must pass before next task

### Task 4: Clean up tools.py — separate handler building
- [ ] Extract `_build_typed_handler` into a dedicated `handlers.py` module
- [ ] Move typed handler response envelope construction alongside handler building
- [ ] Keep `register_tools()` as the orchestrator in `tools.py` — it calls sub-registration functions
- [ ] Update imports in `tools.py`
- [ ] Write test for `_build_typed_handler` — verify it creates a callable with correct name/doc
- [ ] Write test for non-paginated handler response envelope structure
- [ ] Run tests — must pass before next task

### Task 5: Verify acceptance criteria
- [ ] Verify httpx.AsyncClient is created once and reused across requests (no per-request overhead)
- [ ] Verify pagination logic is isolated in its own module
- [ ] Verify tools.py is simplified (orchestration only, no business logic)
- [ ] Verify handler building is testable independently
- [ ] Run full test suite (unit tests)
- [ ] Run linter (`make lint`)
- [ ] Run type checker (`make typecheck`)
- [ ] Verify all checks pass (`make check`)

### Task 6: [Final] Update documentation
- [ ] Update CHANGELOG.md with refactoring entry under [Unreleased]
- [ ] Update README.md if any public API changed
- [ ] Update CONTRIBUTING.md if new modules affect developer workflow

## Technical Details

### Connection pooling configuration
- `httpx.AsyncClient` with `httpx.Limits(max_connections=10, max_keepalive_connections=5)`
- Timeout set once at client construction: `httpx.Timeout(settings.timeout_seconds)`
- Default headers (Authorization, Accept, User-Agent, org headers) set at construction
- Client created in `start()`, closed in `stop()`

### Module structure after refactoring
```
src/yandex_tracker_mcp/
  client.py        — TrackerClient with persistent connection pool + lifecycle
  config.py        — unchanged
  errors.py        — unchanged
  handlers.py      — NEW: _build_typed_handler + response envelope logic
  models.py        — unchanged
  pagination.py    — NEW: normalize_page + helpers
  registry.py      — unchanged
  server.py        — lifespan context manager added
  tools.py         — simplified to orchestration only
```

### FastMCP lifespan pattern
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    client = TrackerClient(settings)
    await client.start()
    try:
        yield {"client": client}
    finally:
        await client.stop()
```

## Post-Completion
**Manual verification:**
- Test with a real Yandex Tracker instance to verify connection reuse works
- Monitor connection count under sequential tool calls to confirm pooling
