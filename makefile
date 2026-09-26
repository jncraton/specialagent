test:
	uvx pytest

lint:
	uvx black --check specialagent tests

format:
	uvx black specialagent tests

clean:
	rm -rf .pytest_cache **/__pycache__
