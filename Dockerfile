FROM docker-registry.ebrains.eu/hdc-services-image/base-image:python-3.10.14-v1 AS upload-image

ENV PYTHONDONTWRITEBYTECODE=true \
    PYTHONIOENCODING=UTF-8 \
    POETRY_VERSION=1.3.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

ENV PATH="${POETRY_HOME}/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y vim-tiny less libmagic1 apt-utils && \
    ln -s /usr/bin/vim.tiny /usr/bin/vim && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml ./
COPY app ./app
RUN poetry install --no-dev --no-root --no-interaction

RUN chown -R app:app /app
USER app

CMD ["python3", "-m", "app"]
