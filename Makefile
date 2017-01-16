
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf dist
	rm -rf .cache  # py.test junk

test:
	nosetests3 --stop ./tests/
