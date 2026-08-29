.PHONY: setup test lint typecheck check

UV := uv

setup:
	$(UV) sync --all-groups

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

typecheck:
	$(UV) run pyright

check: lint typecheck test
