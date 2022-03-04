SHELL=/bin/bash
PIPREQS=pipreqs

reqs:
	$(PIPREQS) --no-pin .

reqs-force:
	$(PIPREQS) --no-pin --force .

test:
	flake8
	mypy . --junit-xml mypy_report.xml
	black --diff --color .
	isort . --check --diff
	pytest

fix:
	isort .
	black .
