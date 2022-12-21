FROM python:3.10-slim as base
ENV PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    WORKDIR=/code 
ENV PATH="$POETRY_HOME/bin:$PATH" 
WORKDIR $WORKDIR

FROM base as poetry_installer
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential
ENV POETRY_VERSION=1.2.0
RUN curl -sSL https://install.python-poetry.org | python3 -

FROM base as dev
COPY --from=poetry_installer $POETRY_HOME $POETRY_HOME

FROM base as package_installer
COPY --from=poetry_installer $POETRY_HOME $POETRY_HOME
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry install --without dev 

FROM base as prod
COPY --from=package_installer /usr/local/bin /usr/local/bin
COPY --from=package_installer /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY ./app ./app
CMD uvicorn app.main:app --reload 


