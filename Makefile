VENV_PATH?=venv

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist build
	rm -rf .pytest_cache
	rm -rf "$(VENV_PATH)"

venv:
	python3 -m venv "$(VENV_PATH)"
	# Docutils is needed for `setup.py check -r -s`
	"$(VENV_PATH)"/bin/pip install --upgrade wheel docutils
	"$(VENV_PATH)"/bin/pip install --upgrade pytest asynctest maxminddb
	"$(VENV_PATH)"/bin/pip install --editable .

test: venv
	. "$(VENV_PATH)"/bin/activate ; \
	"$(VENV_PATH)"/bin/pytest --exitfirst tests
	# Check if README.org converts correctly to rst for PyPI
	python3 setup.py check -r -s >/dev/null

release:
	pyrelease CHANGELOG ./stig/__version__.py
