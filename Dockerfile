FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

# match the host user, so files written into the mounted source don't end up owned by root
ARG UID=1000
ARG GID=1000
RUN groupadd --gid $GID dev && useradd --uid $UID --gid $GID --create-home dev

# the venv lives outside /app, so the source mount doesn't hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH
RUN mkdir /opt/venv /app && chown dev:dev /opt/venv /app

# print right away, otherwise serve's output only shows up once the buffer fills
ENV PYTHONUNBUFFERED=1

USER dev
WORKDIR /app

COPY --chown=dev:dev pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY --chown=dev:dev . .
RUN uv sync --locked

CMD ["hrabal", "--help"]
