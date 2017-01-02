
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -r dist
	rm -r .cache  # py.test junk

check:
	nosetests3 --stop ./tests/
