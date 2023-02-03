SHELL=/bin/bash
PIPREQS=pipreqs

reqs:
	$(PIPREQS) --no-pin .

reqs-force:
	$(PIPREQS) --no-pin --force .

test:
	ruff .
	mypy . --junit-xml mypy_report.xml
	black --diff --color .
	pytest

fix:
	ruff . --fix
	black .
