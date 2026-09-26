all: test

lint:
	uvx black --check specialagent tests

format:
	uvx black specialagent tests

test:
	uvx pytest

clean:
	rm -rf .venv uv.lock .pytest_cache **/__pycache__ build dist *.egg-info
