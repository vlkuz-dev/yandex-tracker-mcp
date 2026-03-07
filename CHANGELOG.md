# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.1.1] - 2026-03-07

### Changed

- Refactored `TrackerClient` to use a persistent `httpx.AsyncClient` with connection pooling instead of creating a new client per request.
- Added client lifecycle management (`start`/`stop`) wired into FastMCP lifespan hooks.
- Extracted pagination normalization from `tools.py` into dedicated `pagination.py` module.
- Extracted handler building from `tools.py` into dedicated `handlers.py` module.
- Simplified `tools.py` to orchestration-only role.

### Fixed

- Fixed off-by-one in network error retry logic — `retries` setting now consistently means N retries beyond the initial attempt for both network errors and HTTP status retries.
- Fixed URL-encoded path traversal bypass in raw request validation (`%2e%2e` no longer bypasses `..` check).

## [0.1.0] - 2026-03-06

### Added

- Initial FastMCP server implementation for Yandex Tracker API v3.
- Typed tools generated from an operation registry plus guarded raw v3 request tool.
- `stdio` and `streamable-http` transports.
- Config validation for token + org header modes.
- HTTPX async client with retry/error handling.
- CI for lint, type-check, tests, package build, and Docker build.
- Test suite for config, registry, client behavior, and pagination normalization.
