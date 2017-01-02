
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist
	rm -rf .cache  # py.test junk

check:
	nosetests3 --stop ./tests/
