"""Erreurs de l'identité (specs § 6.2) ; le statut HTTP est choisi par l'interface selon le type.

| Erreur | Code | HTTP |
| --- | --- | --- |
| `Unauthenticated` | `UNAUTHENTICATED` | 401 — jeton absent, illisible, expiré |
| `InvalidCredentials` | `UNAUTHENTICATED` | 401 — message générique (aucune fuite) |
| `SessionRevoked` | `SESSION_REVOKED` | 401 — appareil déconnecté, jeton réutilisé |
| `AccountLocked` | `ACCOUNT_LOCKED` | 423 — `details.until` (ISO 8601 UTC) |
| `AccountDisabled` | `ACCOUNT_DISABLED` | 403 — code **ajouté** par T08 (recette Q-31) |
| `PinChangeRequired` | `PIN_CHANGE_REQUIRED` | 403 — première connexion ou code provisoire |
| `PinTooSimple` | `PIN_TOO_SIMPLE` | 422 — `details.reason` |
| `PasswordTooWeak` | `PASSWORD_TOO_WEAK` | 422 — code **ajouté** (mot de passe admin, § 15.1) |
"""

from datetime import datetime

from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import DomainError, Forbidden

INVALID_CREDENTIALS_MESSAGE = "Numéro ou code incorrect"
ACCOUNT_DISABLED_MESSAGE = "Compte désactivé, contactez le propriétaire"


class Unauthenticated(DomainError):
    """Aucune identité établie : jeton absent, illisible, expiré, session inconnue."""

    code = "UNAUTHENTICATED"


class InvalidCredentials(Unauthenticated):
    """Numéro inconnu **ou** code faux : même message, aucune fuite d'existence (SEC-L08)."""

    def __init__(self) -> None:
        super().__init__(INVALID_CREDENTIALS_MESSAGE)


class SessionRevoked(Unauthenticated):
    """Session de l'appareil révoquée (déconnexion à distance RG-D07, réutilisation de jeton)."""

    code = "SESSION_REVOKED"

    def __init__(self) -> None:
        super().__init__("Session terminée sur cet appareil : reconnectez-vous")


class AccountLocked(DomainError):
    """Compte bloqué après trop d'essais faux (UC-SOC-02) → 423."""

    code = "ACCOUNT_LOCKED"

    def __init__(self, until: datetime) -> None:
        until_utc = require_aware(until)
        super().__init__(
            "Compte bloqué temporairement après plusieurs essais faux",
            details={"until": until_utc.isoformat()},
        )
        self.until = until_utc


class AccountDisabled(Forbidden):
    """Compte désactivé (RG-D06) : refusé au login, au rafraîchissement et à chaque requête."""

    code = "ACCOUNT_DISABLED"

    def __init__(self) -> None:
        super().__init__(ACCOUNT_DISABLED_MESSAGE)


class PinChangeRequired(Forbidden):
    """Le code provisoire doit être changé avant toute route métier (H14, AUTH-02)."""

    code = "PIN_CHANGE_REQUIRED"

    def __init__(self) -> None:
        super().__init__("Choisissez un nouveau code avant de continuer")


class PinTooSimple(DomainError):
    """Code refusé par la politique des codes (UC-SOC-07) → 422."""

    code = "PIN_TOO_SIMPLE"

    def __init__(self, reason: str) -> None:
        super().__init__("Code trop simple : choisissez-en un autre", details={"reason": reason})


class PasswordTooWeak(DomainError):
    """Mot de passe administrateur refusé par la politique (specs § 15.1) → 422."""

    code = "PASSWORD_TOO_WEAK"

    def __init__(self, reason: str, *, min_length: int) -> None:
        super().__init__(
            "Mot de passe trop faible",
            details={"reason": reason, "min_length": min_length},
        )
