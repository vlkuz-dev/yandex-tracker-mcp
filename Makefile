PYTHON := .venv/bin/python
UV_RUN := uv run --python $(PYTHON) --no-sync

.PHONY: setup lint typecheck test check build

setup:
	uv venv .venv
	uv pip install --python $(PYTHON) -e ".[dev]"

lint:
	$(UV_RUN) ruff check .

typecheck:
	$(UV_RUN) mypy src

test:
	$(UV_RUN) pytest -q

check: lint typecheck test

build:
	$(UV_RUN) python -m build
