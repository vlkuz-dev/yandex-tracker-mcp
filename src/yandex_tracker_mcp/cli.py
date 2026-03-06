"""CLI entry points for stdio and streamable-http transports."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .config import Settings
from .server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracker-mcp")
    subparsers = parser.add_subparsers(dest="transport")

    stdio_parser = subparsers.add_parser("stdio", help="Run server over stdio")
    stdio_parser.set_defaults(transport="stdio")

    http_parser = subparsers.add_parser("http", help="Run server over streamable-http")
    http_parser.add_argument("--host", default="0.0.0.0")
    http_parser.add_argument("--port", default=8000, type=int)
    http_parser.add_argument("--path", default="/mcp")
    http_parser.set_defaults(transport="http")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.transport in (None, "stdio"):
        main_stdio()
        return

    if args.transport == "http":
        main_http(host=args.host, port=args.port, path=args.path)
        return

    parser.error(f"Unsupported transport: {args.transport}")


def main_stdio() -> None:
    settings = Settings.from_env()
    server = create_server(settings)
    server.run(transport="stdio")


def main_http(*, host: str = "0.0.0.0", port: int = 8000, path: str = "/mcp") -> None:
    settings = Settings.from_env()
    server = create_server(settings)
    server.run(transport="streamable-http", host=host, port=port, path=path)

