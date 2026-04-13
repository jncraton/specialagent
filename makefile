all: test

lint:
	uv run --with black==24.1.0 python -m black --check sloplint tests

format:
	uv run --with black==24.1.0 python -m black sloplint tests

test:
	uv run --with pytest==7.4.0 python -m pytest

clean:
	rm -rf .venv uv.lock .pytest_cache **/__pycache__ build dist *.egg-info
