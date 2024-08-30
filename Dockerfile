ARG PY_VERSION=3.12

FROM python:${PY_VERSION}-slim as builder
# Required to bring in the variable from outside the FROM

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/mail_groene_maaiers src/mail_groene_maaiers/
RUN touch README.md

# Leverage poetry cache in docker build_kit
# RUN --mount=type=cache,target=$POETRY_CACHE_DIR uv sync
RUN uv sync

FROM python:${PY_VERSION}-slim as runtime

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/mail_groene_maaiers src/mail_groene_maaiers/
COPY main.py .
ENTRYPOINT ["python"]
