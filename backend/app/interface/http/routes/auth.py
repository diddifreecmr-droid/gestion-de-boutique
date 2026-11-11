"""Routes `/auth/*` et `/me` (specs § 6.3, § 7.2, § 8.1 ; recette AUTH-01, AUTH-02).

Limitation de débit (T10, T10b, specs § 8.1) : seuil par route, par IP ; la connexion compte
aussi le numéro ; `/auth/logout` n'est pas limité. Au-delà, 429 `RATE_LIMITED` + `Retry-After`
(détail : `interface/http/rate_limit.py`). Sans `throttle` (tests), rien n'est compté. IP :
`X-Forwarded-For` lu seulement derrière un proxy de confiance (`interface/http/client_ip.py`).

Cookie de rafraîchissement : `HttpOnly; Secure; SameSite=Lax; Path=<préfixe>/auth`, durée de
vie = celle de la session (glissante, ou 8 h pour l'admin). Le jeton d'accès est renvoyé dans
le corps, jamais en cookie. Toutes les réponses portent `Cache-Control: no-store`.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Body, Cookie, Depends, Request, Response, status

from app.application.identity.sessions import IssuedSession
from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.application.identity.use_cases.change_pin import ChangePin, ChangePinCommand
from app.application.identity.use_cases.get_me import GetMe
from app.application.identity.use_cases.login import CredentialKind, Login, LoginCommand
from app.application.identity.use_cases.logout import Logout
from app.application.identity.use_cases.refresh_session import RefreshSession
from app.application.ports.clock import Clock
from app.application.security.rate_limit import AuthThrottle
from app.domain.identity.errors import Unauthenticated
from app.domain.shared.ids import DeviceId
from app.interface.http.client_ip import ClientIpResolver, IpNetwork
from app.interface.http.rate_limit import AuthLimits
from app.interface.http.schemas.auth import (
    ChangePinRequest,
    LoginRequest,
    MeResponse,
    ShopMembershipResponse,
    TokenResponse,
)
from app.interface.http.security import AuthGuard, device_id

REFRESH_COOKIE = "refresh_token"

Device = Annotated[DeviceId, Depends(device_id)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthComponents:
    """Cas d'utilisation assemblés par la composition root."""

    login: Login
    refresh: RefreshSession
    logout: Logout
    change_pin: ChangePin
    get_me: GetMe
    guard: AuthGuard
    clock: Clock
    throttle: AuthThrottle | None = None
    trusted_proxies: tuple[IpNetwork, ...] = ()


def build_auth_router(auth: AuthComponents, api_prefix: str) -> APIRouter:
    limits = AuthLimits(auth.throttle, ClientIpResolver(auth.trusted_proxies))
    router = APIRouter(tags=["auth"])
    cookie_path = f"{api_prefix}/auth"

    def no_store(response: Response) -> None:
        response.headers["Cache-Control"] = "no-store"

    def set_refresh_cookie(response: Response, issued: IssuedSession) -> None:
        max_age = int((issued.refresh_expires_at - auth.clock.now()).total_seconds())
        response.set_cookie(
            REFRESH_COOKIE,
            issued.refresh_token,
            max_age=max(max_age, 0),
            path=cookie_path,
            secure=True,
            httponly=True,
            samesite="lax",
        )

    def clear_refresh_cookie(response: Response) -> None:
        response.delete_cookie(
            REFRESH_COOKIE, path=cookie_path, secure=True, httponly=True, samesite="lax"
        )

    def token_response(response: Response, issued: IssuedSession) -> TokenResponse:
        no_store(response)
        set_refresh_cookie(response, issued)
        return TokenResponse(
            access_token=issued.access_token,
            expires_at=issued.access_expires_at,
            must_change_pin=issued.must_change_pin,
        )

    def require_cookie(value: str | None) -> str:
        if not value:
            msg = "Session absente sur cet appareil"
            raise Unauthenticated(msg)
        return value

    @router.post("/auth/login", dependencies=[Depends(limits.login_ip)])
    def login(
        body: LoginRequest, device: Device, request: Request, response: Response
    ) -> TokenResponse:
        limits.login_phone(request, body.phone)
        kind = CredentialKind.PIN if body.pin is not None else CredentialKind.PASSWORD
        secret = body.pin if body.pin is not None else body.password
        if secret is None:  # exclu par LoginRequest : défense en profondeur
            msg = "LoginRequest sans secret"
            raise RuntimeError(msg)
        command = LoginCommand(
            phone=body.phone,
            secret=secret,
            kind=kind,
            device_id=device,
            device_label=body.device_label,
        )
        return token_response(response, auth.login.execute(command))

    @router.post("/auth/refresh", dependencies=[Depends(limits.refresh)])
    def refresh(device: Device, response: Response, cookie: RefreshCookie = None) -> TokenResponse:
        return token_response(response, auth.refresh.execute(require_cookie(cookie), device))

    @router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(device: Device, response: Response, cookie: RefreshCookie = None) -> None:
        auth.logout.execute(require_cookie(cookie), device)
        no_store(response)
        clear_refresh_cookie(response)

    @router.post(
        "/auth/change-pin",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(limits.change_pin)],
    )
    def change_pin(
        identity: Annotated[AuthenticatedUser, Depends(auth.guard.current_user)],
        body: Annotated[ChangePinRequest, Body()],
        response: Response,
    ) -> None:
        command = ChangePinCommand(
            current=body.current_pin, new=body.new_pin, confirmation=body.new_pin_confirmation
        )
        auth.change_pin.execute(identity, command)
        no_store(response)

    @router.get("/me")
    def me(
        identity: Annotated[AuthenticatedUser, Depends(auth.guard.current_user)],
        response: Response,
    ) -> MeResponse:
        view = auth.get_me.execute(identity)
        no_store(response)
        return MeResponse(
            user_id=str(view.user_id),
            name=view.name,
            phone=view.phone,
            is_platform_admin=view.is_platform_admin,
            must_change_pin=view.must_change_pin,
            shops=[
                ShopMembershipResponse(
                    shop_id=str(m.shop_id), shop_name=m.shop_name, role=m.role.value
                )
                for m in view.shops
            ],
        )

    return router
