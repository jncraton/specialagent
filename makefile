all: test

lint:
	uvx black --check specialagent tests

format:
	uvx black specialagent tests

test:
	uvx pytest

clean:
	rm -rf .pytest_cache **/__pycache__
