#!/usr/bin/env python3
"""Sync Tracker operations registry from docs pages.

The script is intentionally conservative: it preserves existing operation metadata and
adds newly discovered (method, path) pairs.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

DEFAULT_DOC_URLS = [
    "https://yandex.ru/support/tracker/en/about-api",
]
TRACKER_DOC_HOST = "yandex.ru"
TRACKER_DOC_PATH_PREFIX = "/support/tracker/"
TRACKER_DOC_ALLOWED_SEGMENTS = ("/support/tracker/en/concepts/", "/support/tracker/en/about-api")

METHOD_PATH_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/v3/[A-Za-z0-9_\-./{}]+)", re.IGNORECASE
)
PATH_ONLY_RE = re.compile(r"\b(/v3/[A-Za-z0-9_\-./{}]+)")
DOC_LINK_RE = re.compile(r"""href=["']([^"'#?]+)["']""")


@dataclass(slots=True, frozen=True)
class DiscoveredOperation:
    method: str
    path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="src/yandex_tracker_mcp/operations.json",
        help="Path to operations registry JSON",
    )
    parser.add_argument(
        "--doc-url",
        action="append",
        dest="doc_urls",
        help="Documentation page URL (repeatable)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout seconds",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes to registry file",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=80,
        help="Maximum number of documentation pages to crawl",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry)
    urls = args.doc_urls or DEFAULT_DOC_URLS

    current = load_registry(registry_path)
    discovered = discover_operations(urls, timeout=args.timeout, max_pages=args.max_pages)

    merged, added = merge_registry(current, discovered)

    if args.write:
        registry_path.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"Discovered operations: {len(discovered)}")
    print(f"Existing operations: {len(current)}")
    print(f"Added operations: {added}")
    print(f"Merged operations: {len(merged)}")
    if not args.write:
        print("Dry-run mode. Re-run with --write to persist changes.")

    return 0


def load_registry(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Registry root must be an array")
    return [dict(item) for item in data]


def discover_operations(
    urls: list[str], *, timeout: float, max_pages: int
) -> set[DiscoveredOperation]:
    discovered: set[DiscoveredOperation] = set()

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for url in crawl_doc_pages(client, urls, max_pages=max_pages):
            response = client.get(url)
            if response.status_code >= 400:
                continue
            text = response.text
            method_hits = 0

            for method, path in METHOD_PATH_RE.findall(text):
                discovered.add(
                    DiscoveredOperation(method=method.upper(), path=normalize_path(path))
                )
                method_hits += 1

            # Fallback if method is not present in page snippet: keep GET placeholder.
            if method_hits == 0:
                for path in PATH_ONLY_RE.findall(text):
                    if path.startswith("/v3/"):
                        discovered.add(DiscoveredOperation(method="GET", path=normalize_path(path)))

    return discovered


def crawl_doc_pages(
    client: httpx.Client, seed_urls: list[str], *, max_pages: int
) -> list[str]:
    queue: deque[str] = deque(seed_urls)
    visited: set[str] = set()
    pages: list[str] = []

    while queue:
        if len(pages) >= max_pages:
            break
        current = queue.popleft()
        normalized = normalize_doc_url(current)
        if normalized in visited:
            continue
        visited.add(normalized)

        response = client.get(normalized)
        if response.status_code >= 400:
            continue
        pages.append(normalized)

        for href in DOC_LINK_RE.findall(response.text):
            candidate = normalize_doc_url(urljoin(normalized, href))
            if candidate in visited:
                continue
            if not is_tracker_doc_page(candidate):
                continue
            queue.append(candidate)

    return pages


def merge_registry(
    current: list[dict[str, Any]],
    discovered: set[DiscoveredOperation],
) -> tuple[list[dict[str, Any]], int]:
    existing_pairs = {
        (str(item.get("method", "")).upper(), str(item.get("path", ""))) for item in current
    }

    added = 0
    for operation in sorted(discovered, key=lambda row: (row.path, row.method)):
        pair = (operation.method, operation.path)
        if pair in existing_pairs:
            continue
        generated = build_generated_item(operation)
        current.append(generated)
        existing_pairs.add(pair)
        added += 1

    current.sort(key=lambda item: (str(item["domain"]), str(item["action"]), str(item["path"])))
    return current, added


def build_generated_item(operation: DiscoveredOperation) -> dict[str, Any]:
    domain, action = derive_domain_action(operation.path, operation.method)
    operation_id = build_operation_id(operation.method, operation.path)
    return {
        "operation_id": operation_id,
        "domain": domain,
        "action": action,
        "method": operation.method,
        "path": operation.path,
        "summary": f"Auto-discovered operation {operation.method} {operation.path}",
        "typed_tool": False,
    }


def derive_domain_action(path: str, method: str) -> tuple[str, str]:
    parts = [part for part in path.split("/") if part]
    domain = parts[1] if len(parts) > 1 else "tracker"
    action = method.lower()
    return sanitize_identifier(domain), sanitize_identifier(action)


def build_operation_id(method: str, path: str) -> str:
    payload = f"{method}_{path}".replace("/", "_")
    return sanitize_identifier(payload)


def sanitize_identifier(value: str) -> str:
    normalized = value
    for old, new in (("{", ""), ("}", ""), ("-", "_"), (".", "_")):
        normalized = normalized.replace(old, new)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def normalize_path(path: str) -> str:
    value = path.strip()
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def normalize_doc_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc or TRACKER_DOC_HOST
    path = parsed.path
    path = path.replace("/support/tracker/en/en/", "/support/tracker/en/")
    path = path.replace("/support/tracker/ru/ru/", "/support/tracker/ru/")
    path = path.replace("/support/tracker/en/concepts/en/", "/support/tracker/en/concepts/")
    path = path.replace("/support/tracker/ru/concepts/ru/", "/support/tracker/ru/concepts/")
    return f"{scheme}://{host}{path}"


def is_tracker_doc_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != TRACKER_DOC_HOST:
        return False
    if not parsed.path.startswith(TRACKER_DOC_PATH_PREFIX):
        return False
    return parsed.path.startswith(TRACKER_DOC_ALLOWED_SEGMENTS)


if __name__ == "__main__":
    raise SystemExit(main())
