.PHONY: install dev-install run test coverage type-check lint clean

install:
	pip install .

dev-install:
	pip install ".[dev]"

run:
	python -m src.main

test:
	python -m pytest tests/ -v

coverage:
	python -m pytest tests/ --cov=src --cov=observability --cov=runtime --cov-report=term-missing

type-check:
	mypy --strict src observability runtime resilience

lint:
	python -m compileall src observability runtime resilience

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/
