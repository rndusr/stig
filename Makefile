clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist
	rm -rf .pytest_cache
	rm -rf venv

venv:
	python3 -m venv './venv'
	venv/bin/pip install --upgrade wheel pytest asynctest maxminddb
	venv/bin/pip install --editable .

test:
	test -n $(VIRTUAL_ENV) && python3 -m pytest --tb no tests

release:
	pyrelease CHANGELOG ./stig/__version__.py
