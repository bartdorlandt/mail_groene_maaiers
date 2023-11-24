ARG PY_VERSION=3.11
ARG POETRY_VERSION=1.7

FROM python:${PY_VERSION}-slim as builder
# Required to bring in the variable from outside the FROM
ARG POETRY_VERSION

RUN pip install poetry==${POETRY_VERSION}

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN touch README.md

# Leverage poetry cache in docker build_kit
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root


FROM python:${PY_VERSION}-slim as runtime

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY mail_groene_maaiers mail_groene_maaiers/
COPY main.py .
ENTRYPOINT ["python"]
