# syntax=docker/dockerfile:1
# Image de production de l'API (T25, specs § 4.7). Contexte de build : backend/.
#
# - Étape « builder » : uv installe les dépendances verrouillées (uv.lock, sans le groupe dev)
#   dans /opt/venv. Seuls app/, alembic/ et alembic.ini sont copiés : tools/ (données de
#   démonstration) et tests/ ne sont jamais dans l'image (voir aussi .dockerignore).
# - Étape « runtime » : Python seul + /opt/venv + code, utilisateur non-root `app` (uid 10001).
# - Démarrage : `alembic upgrade head` PUIS l'API ; si la migration échoue, l'API ne démarre pas
#   (`&&`), et l'API elle-même refuse de servir sur une base injoignable ou non migrée.

ARG PYTHON_IMAGE=python:3.12.16-slim-trixie

FROM ghcr.io/astral-sh/uv:0.13.8 AS uv

FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN python -m compileall -q app alembic

FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /srv/api
COPY --from=builder /build/alembic.ini ./alembic.ini
COPY --from=builder /build/alembic ./alembic
COPY --from=builder /build/app ./app
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    ENVIRONMENT=prod \
    WEB_CONCURRENCY=1
# Code en lecture seule pour `app` (propriété de root) ; aucun fichier n'est écrit à l'exécution.
USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=4 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]

# --no-proxy-headers : l'adresse du client est lue par l'application elle-même, et seulement
# derrière un proxy de confiance (AUTH_TRUSTED_PROXIES, app/interface/http/client_ip.py).
# WEB_CONCURRENCY (lu par uvicorn) = nombre de processus ; 1 par défaut, car la limitation de
# débit de /auth/* est comptée en mémoire, par processus.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.bootstrap.container:build_app --factory --host 0.0.0.0 --port 8000 --no-proxy-headers --no-server-header"]
