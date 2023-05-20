all: check #test clean


.PHONY: all

check:
	# Run linter
	@echo Linting!
	flake8

