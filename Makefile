SHELL=/bin/bash
PIPREQS=pipreqs

venv:
	source venv/bin/activate

reqs:
	$(PIPREQS) --no-pin .

reqs-force:
	$(PIPREQS) --no-pin --force .

test:
	pytest -v test_*
	flake8 .
