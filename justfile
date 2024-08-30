set positional-arguments

TAGS := 'all'
DOCKER_USER := 'bartdorlandt'
NAME := 'mail_groene_maaiers'
VERSION := 'latest'
REMOTE_PATH := '/Volumes/docker/mail_groene_maaiers'

docker_compose_tty := ""
docker_run_tty := "-it"

default:
	@just --list --unsorted --justfile {{justfile()}}

_nox_docker +CMD:
	# docker run --platform linux/amd64 --rm -it -v $(pwd):/src {{DOCKER_USER}}/python_nox_uv {{CMD}} -f src/noxfile.py
	docker run --platform linux/amd64 --rm -it -v $(pwd):/src python_nox_uv uv run {{CMD}} -f src/noxfile.py

test:
	uv run ruff check .
	uv run ruff format --diff .
	uv run mypy . --junit-xml mypy_report.xml
	uv run pytest --cov-report=html

fix:
	uv run ruff check . --fix
	uv run ruff format . -v

[group('nox')]
nox:
	just _nox_docker nox

[group('nox')]
nox_test:
	just _nox_docker nox -s tests

[group('nox')]
nox_lint:
	just _nox_docker nox -s lint

[group('nox')]
nox_typing:
	just _nox_docker nox -s typing

[group('docker')]
build:
	DOCKER_BUILDKIT=1 docker build --tag "{{DOCKER_USER}}/{{NAME}}":"{{VERSION}}" .

[group('docker')]
clean:
	docker rmi "{{DOCKER_USER}}/{{NAME}}":"{{VERSION}}" --force

[group('docker')]
rebuild clean build:

[group('mail')]
mail:
	docker_image="{{DOCKER_USER}}/{{NAME}}"
	docker pull "${docker_image}":"{{VERSION}}"
	docker run {{docker_run_tty}} --rm \
		-v $(pwd)/.env:/app/.env \
		-v $(pwd)/credentials.json:/app/credentials.json \
		"${docker_image}":"{{VERSION}}" main.py

[group('sync')]
sync:
	rsync -avz credentials.json main.py mail_groene_maaiers run env.example --exclude '**/__pycache__' "{{REMOTE_PATH}}"

[group('init')]
install:
	uv sync --no-dev

[group('init')]
install_dev:
	uv sync
