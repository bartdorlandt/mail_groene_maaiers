SHELL=/bin/bash
PIPREQS=pipreqs

reqs:
	$(PIPREQS) --no-pin .

reqs-force:
	$(PIPREQS) --no-pin --force .

install:
	poetry install --sync

install_dev:
	poetry install --with dev --sync

test:
	ruff .
	mypy . --junit-xml mypy_report.xml
	black --diff --color .
	pytest

fix:
	ruff . --fix
	black .
