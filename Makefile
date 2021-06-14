SHELL=/bin/bash
PIPREQS=pipreqs

reqs:
	$(PIPREQS) --no-pin .

reqs-force:
	$(PIPREQS) --no-pin --force .

test:
	flake8 .
	pytest -v test_*
