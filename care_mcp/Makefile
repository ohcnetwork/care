.PHONY: clean clean-build clean-pyc lint dist install help

help:
	@echo "clean      - remove all build and Python artifacts"
	@echo "lint       - check style with ruff"
	@echo "dist       - build source and wheel packages"
	@echo "install    - install the package to the active Python's site-packages"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

lint:
	ruff check care_mcp --extend-exclude "care_mcp/migrations"
	ruff format --check care_mcp --exclude "care_mcp/migrations"

dist: clean
	python setup.py sdist bdist_wheel
	ls -l dist

install: clean
	pip install .
