
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf .cache  # py.test junk

test:
	# python3 -m pytest --maxfail=1 ./tests/
	nosetests3 --stop ./tests/
