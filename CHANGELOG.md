# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Changed

- Refactored `TrackerClient` to use a persistent `httpx.AsyncClient` with connection pooling instead of creating a new client per request.
- Added client lifecycle management (`start`/`stop`) wired into FastMCP lifespan hooks.
- Extracted pagination normalization from `tools.py` into dedicated `pagination.py` module.
- Extracted handler building from `tools.py` into dedicated `handlers.py` module.
- Simplified `tools.py` to orchestration-only role.

## [0.1.0] - 2026-03-06

### Added

- Initial FastMCP server implementation for Yandex Tracker API v3.
- Typed tools generated from an operation registry plus guarded raw v3 request tool.
- `stdio` and `streamable-http` transports.
- Config validation for token + org header modes.
- HTTPX async client with retry/error handling.
- CI for lint, type-check, tests, package build, and Docker build.
- Test suite for config, registry, client behavior, and pagination normalization.
