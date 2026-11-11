"""Fabrique de l'application FastAPI (adaptateur HTTP entrant).

Ne connaît aucun adaptateur concret : `bootstrap.container` lui fournit ses dépendances.
"""

from fastapi import FastAPI

from app.interface.http.config import HttpConfig
from app.interface.http.errors import register_error_handlers
from app.interface.http.routes import health
from app.interface.http.routes.auth import AuthComponents, build_auth_router
from app.interface.http.routes.journal import JournalComponents, build_journal_router


def create_app(
    config: HttpConfig, auth: AuthComponents, journal: JournalComponents | None = None
) -> FastAPI:
    """`journal` absent : routes du journal et des alertes non montées (outils, tests ciblés)."""
    prefix = config.api_prefix
    expose_docs = config.expose_docs
    app = FastAPI(
        title="Gestion de boutiques",
        version="0.1.0",
        openapi_url=f"{prefix}/openapi.json" if expose_docs else None,
        docs_url=f"{prefix}/docs" if expose_docs else None,
        redoc_url=None,
    )
    register_error_handlers(app, None if journal is None else journal.record_access_denied.execute)
    app.include_router(health.router, prefix=prefix)
    app.include_router(build_auth_router(auth, prefix), prefix=prefix)
    if journal is not None:
        app.include_router(build_journal_router(journal), prefix=prefix)
    return app
