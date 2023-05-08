SHELL=/bin/bash
NAME=groene_maaiers
VERSION=latest

install:
	poetry install --sync

install_dev:
	poetry install --with dev --sync

test:
	ruff .
	mypy . --junit-xml mypy_report.xml
	black --diff --color .
	pytest

build: Dockerfile
	docker build --tag ${NAME}:${VERSION} .

clean: Dockerfile
	docker rmi ${NAME}:${VERSION} --force

rebuild: clean build

fix:
	ruff . --fix
	black .

mail:
	docker run --rm -it -v=.:/local ${NAME}:${VERSION} sh -c 'python3 groene_maaiers.py'
