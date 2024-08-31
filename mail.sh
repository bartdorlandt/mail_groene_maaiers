#/!bin/bash

DOCKER_USER=bartdorlandt
NAME=mail_groene_maaiers
VERSION=latest
# docker_run_tty="-it"

docker_image=${DOCKER_USER}/${NAME}
docker pull "${docker_image}":"${VERSION}"
# docker run {{docker_run_tty}} --rm \
docker run --rm \
    -v $(pwd)/.env:/app/.env \
    -v $(pwd)/credentials.json:/app/credentials.json \
    "${docker_image}":"${VERSION}" main.py