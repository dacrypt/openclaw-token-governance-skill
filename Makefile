.PHONY: setup lint test ci

setup:
	python3 -m pip install -r requirements-dev.txt

lint:
	ruff check src tests

test:
	pytest

ci: lint test
