"""Traduction des erreurs en réponses HTTP `{"error": {"code", "message", "details"}}` (§ 6.1).

- `DomainError` : statut choisi selon le type (héritage compris), corps avec le code stable.
- Validation FastAPI : 400 `VALIDATION_ERROR`, `details.fields` (sans écho des valeurs reçues).
- Erreur HTTP Starlette (route inconnue, méthode refusée) : même enveloppe.
- Toute autre exception : 500 `INTERNAL_ERROR`, **journalisée** avec sa trace, jamais renvoyée.
"""

import logging
from collections.abc import Callable, Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.attachments.ports import LinkExpired, StorageUnavailable
from app.application.audit.access_denied import ACCESS_DENIALS, AccessDenial
from app.application.security.errors import RateLimited
from app.domain.identity.errors import AccountLocked, PinChangeLocked, Unauthenticated
from app.domain.shared.errors import Conflict, DomainError, Forbidden, NotFound, ValidationFailed

logger = logging.getLogger(__name__)

# Statut par type ; une sous-classe hérite du statut de son ancêtre le plus proche.
_STATUS_BY_TYPE: Mapping[type[object], int] = {
    ValidationFailed: HTTPStatus.BAD_REQUEST,
    Unauthenticated: HTTPStatus.UNAUTHORIZED,
    Forbidden: HTTPStatus.FORBIDDEN,
    NotFound: HTTPStatus.NOT_FOUND,
    Conflict: HTTPStatus.CONFLICT,
    AccountLocked: HTTPStatus.LOCKED,
    PinChangeLocked: HTTPStatus.LOCKED,
    RateLimited: HTTPStatus.TOO_MANY_REQUESTS,
    LinkExpired: HTTPStatus.GONE,
    StorageUnavailable: HTTPStatus.SERVICE_UNAVAILABLE,
}
# Règle métier violée (STOCK_INSUFFICIENT, PRICE_BELOW_MINIMUM…) : 422.
_DEFAULT_DOMAIN_STATUS = HTTPStatus.UNPROCESSABLE_ENTITY

_HTTP_CODES: Mapping[int, str] = {
    HTTPStatus.NOT_FOUND: "NOT_FOUND",
    HTTPStatus.METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
}


def status_for(error: DomainError) -> int:
    for klass in type(error).__mro__:
        status = _STATUS_BY_TYPE.get(klass)
        if status is not None:
            return status
    return _DEFAULT_DOMAIN_STATUS


def error_body(code: str, message: str, details: Mapping[str, object]) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "details": dict(details)}}


def _field_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    return [
        {
            "field": ".".join(str(part) for part in err["loc"]),
            "code": str(err["type"]),
            "message": str(err["msg"]),
        }
        for err in exc.errors()
    ]


def register_error_handlers(
    app: FastAPI, on_access_denied: Callable[[AccessDenial], object] | None = None
) -> None:
    """`on_access_denied` : journalise un refus d'accès (RG-D01) avant la réponse 403/404."""

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        if on_access_denied is not None and isinstance(exc, ACCESS_DENIALS):
            await run_in_threadpool(on_access_denied, exc)  # échec → 500 (fail-fast)
        status = status_for(exc)
        # RFC 9110 § 15.5.2 : un 401 annonce le schéma d'authentification attendu.
        headers = {"WWW-Authenticate": "Bearer"} if status == HTTPStatus.UNAUTHORIZED else None
        if isinstance(exc, RateLimited):
            headers = {"Retry-After": str(exc.retry_after)}
        return JSONResponse(
            error_body(exc.code, exc.message, exc.details), status_code=status, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        body = error_body("VALIDATION_ERROR", "Requête invalide", {"fields": _field_errors(exc)})
        return JSONResponse(body, status_code=HTTPStatus.BAD_REQUEST)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        body = error_body(code, str(exc.detail), {})
        return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Erreur inattendue sur %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        body = error_body("INTERNAL_ERROR", "Erreur interne du serveur", {})
        return JSONResponse(body, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
