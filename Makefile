.PHONY: install format lint test docs-serve docs-build clean

install:
	pip install -e ".[dev]"

format:
	black src/ tests/ demo/

lint:
	ruff check src/ tests/ demo/
	mypy src/

test:
	pytest tests/

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache site/
	find . -type d -name "__pycache__" -exec rm -rf {} +
