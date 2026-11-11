"""Dépendances FastAPI de limitation de débit des routes `/auth/*` (specs § 8.1, SEC-L09).

| Route | Clés comptées |
| --- | --- |
| `POST /auth/login` | IP (dépendance, avant lecture du corps) **et** numéro E.164 (`login_phone`) |
| `POST /auth/refresh` | IP |
| `POST /auth/change-pin` | IP (avant l'authentification : un jeton deviné est aussi freiné) |
| `POST /auth/logout` | aucune |

Au-delà du seuil : `RateLimited` → 429 `RATE_LIMITED`, `details.retry_after` + `Retry-After`
(`interface/http/errors.py`). Sans `throttle` (tests par défaut), rien n'est compté.
"""

from collections.abc import Callable

from fastapi import Request

from app.application.security.rate_limit import AuthThrottle
from app.interface.http.client_ip import ClientIpResolver


class AuthLimits:
    def __init__(self, throttle: AuthThrottle | None, resolver: ClientIpResolver) -> None:
        self._throttle = throttle
        self._resolver = resolver

    def _ip(self, request: Request, check: Callable[[AuthThrottle, str], None]) -> None:
        if self._throttle is not None:
            check(self._throttle, self._resolver.resolve(request))

    def login_ip(self, request: Request) -> None:
        self._ip(request, AuthThrottle.check_login_ip)

    def refresh(self, request: Request) -> None:
        self._ip(request, AuthThrottle.check_refresh)

    def change_pin(self, request: Request) -> None:
        self._ip(request, AuthThrottle.check_change_pin)

    def login_phone(self, request: Request, phone: str) -> None:
        """Appelée par la route une fois le corps lu (le numéro y est)."""
        if self._throttle is not None:
            self._throttle.check_login_phone(phone, self._resolver.resolve(request))
