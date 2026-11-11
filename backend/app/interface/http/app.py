"""Fabrique de l'application FastAPI (adaptateur HTTP entrant).

Ne connaît aucun adaptateur concret : `bootstrap.container` lui fournit ses dépendances.
"""

from fastapi import FastAPI

from app.interface.http.config import HttpConfig
from app.interface.http.errors import register_error_handlers
from app.interface.http.routes import health
from app.interface.http.routes.auth import AuthComponents, build_auth_router


def create_app(config: HttpConfig, auth: AuthComponents) -> FastAPI:
    prefix = config.api_prefix
    expose_docs = config.expose_docs
    app = FastAPI(
        title="Gestion de boutiques",
        version="0.1.0",
        openapi_url=f"{prefix}/openapi.json" if expose_docs else None,
        docs_url=f"{prefix}/docs" if expose_docs else None,
        redoc_url=None,
    )
    register_error_handlers(app)
    app.include_router(health.router, prefix=prefix)
    app.include_router(build_auth_router(auth, prefix), prefix=prefix)
    return app
