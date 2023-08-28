all: check test clean


.PHONY: all

check:
	@echo Linting!
	flake8

test:
	pytest -s

clean:
	rm resigner.db