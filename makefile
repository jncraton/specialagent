test:
	uvx pytest

lint:
	uvx black --check .

format:
	uvx black .

clean:
	rm -rf .pytest_cache **/__pycache__
