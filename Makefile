VENV_PATH?=venv
PYTHON?=python3

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist build
	rm -rf .pytest_cache
	rm -rf .tox
	rm -rf "$(VENV_PATH)"

venv:
	"$(PYTHON)" -m venv "$(VENV_PATH)"
	# Docutils is needed for `setup.py check -r -s`
	"$(VENV_PATH)"/bin/pip install --upgrade wheel docutils
	"$(VENV_PATH)"/bin/pip install --upgrade pytest tox asynctest
	"$(VENV_PATH)"/bin/pip install --editable .

test: venv
	. "$(VENV_PATH)"/bin/activate ; \
	  "$(VENV_PATH)"/bin/pytest --exitfirst tests
	# Check if README.org converts correctly to rst for PyPI
	"$(PYTHON)" setup.py check -r -s >/dev/null

fulltest: venv
	. "$(VENV_PATH)"/bin/activate ; \
	  tox
	flake8 stig tests
	isort --check-only stig/**/*.py tests/**/*.py

release:
	pyrelease CHANGELOG ./stig/__version__.py
