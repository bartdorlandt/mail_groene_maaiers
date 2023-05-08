ARG PY_VERSION=3.10
ARG POETRY_VERSION=1.4.2

FROM python:${PY_VERSION}-slim


RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get install curl -y && \
  apt-get autoremove -y && \
  apt-get clean all && \
  rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN curl -sSL https://install.python-poetry.org -o /tmp/install-poetry.py && \
  python /tmp/install-poetry.py --version "${POETRY_VERSION}" && \
  rm -f /tmp/install-poetry.py

# Add poetry install location to the $PATH
ENV PATH="${PATH}:/root/.local/bin"

WORKDIR /local
COPY pyproject.toml poetry.lock /local/

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi
