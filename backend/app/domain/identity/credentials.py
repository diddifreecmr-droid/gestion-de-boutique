"""Politiques des secrets : code à 6 chiffres (H14, UC-SOC-07) et mot de passe admin (§ 15.1).

**Code secret** (`validate_new_pin`) — exactement 6 chiffres ASCII, et refusé (`PinTooSimple`,
`details.reason`) s'il est :

- `repetition` : un seul chiffre répété (`000000`, `111111`) ;
- `sequence` : une suite de pas +1 ou -1, en boucle modulo 10 (`123456`, `654321`, `890123`) ;
- `pattern` : un motif de 2 ou 3 chiffres répété (`121212`, `123123`) ;
- `common` : dans la liste noire `PIN_BLOCKLIST` (codes courants hors des règles ci-dessus :
  rangées et colonnes du pavé numérique, paires montantes, miroirs) ;
- `phone` : égal aux 6 derniers chiffres du numéro de l'utilisateur.

**Mot de passe administrateur** (`validate_new_password`) — politique « longueur d'abord » de
NIST SP 800-63B, sans règle de composition : 10 à 128 caractères (le plafond borne le coût du
hachage), au moins 5 caractères distincts, absent de `PASSWORD_BLOCKLIST` (comparaison sans
casse), et ne contenant pas les 9 derniers chiffres du numéro. Refus → `PasswordTooWeak`.

Une saisie mal formée (pas 6 chiffres, pas une chaîne) → `ValidationFailed` (champ nommé).
"""

from itertools import pairwise

from app.domain.identity.errors import PasswordTooWeak, PinTooSimple
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.errors import ValidationFailed

PIN_LENGTH = 6
PIN_BLOCKLIST: frozenset[str] = frozenset(
    {
        "112233",
        "102030",
        "123321",
        "654456",
        "111222",
        "000111",
        "147258",
        "258369",
        "369258",
        "159753",
        "753951",
        "147852",
        "963852",
        "789456",
        "456123",
        "123654",
    }
)
"""Codes courants que les règles automatiques ne couvrent pas."""

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
PASSWORD_MIN_DISTINCT = 5
PASSWORD_PHONE_DIGITS = 9
PASSWORD_BLOCKLIST: frozenset[str] = frozenset(
    {
        "motdepasse",
        "motdepasse1",
        "motdepasse123",
        "password12",
        "password123",
        "password1234",
        "azertyuiop",
        "qwertyuiop",
        "1234567890",
        "0123456789",
        "0987654321",
        "administrateur",
        "administrator",
        "cameroun237",
        "boutique123",
    }
)
"""Mots de passe courants (comparés en minuscules)."""


def check_pin_format(pin: object, field: str) -> str:
    """Renvoie `pin` s'il compte exactement 6 chiffres ASCII ; `ValidationFailed` sinon."""
    if not isinstance(pin, str) or len(pin) != PIN_LENGTH or not pin.isascii() or not pin.isdigit():
        msg = f"Le code doit compter exactement {PIN_LENGTH} chiffres"
        raise ValidationFailed(msg, details={"field": field})
    return pin


def pin_weakness(pin: str, phone: PhoneNumber | None = None) -> str | None:
    """Raison du refus d'un code bien formé, ou `None` s'il est accepté."""
    digits = [int(char) for char in check_pin_format(pin, "pin")]
    steps = {(b - a) % 10 for a, b in pairwise(digits)}
    if len(set(digits)) == 1:
        return "repetition"
    if steps in ({1}, {9}):
        return "sequence"
    if any(all(pin[i] == pin[i % period] for i in range(PIN_LENGTH)) for period in (2, 3)):
        return "pattern"
    if pin in PIN_BLOCKLIST:
        return "common"
    if phone is not None and phone.digits.endswith(pin):
        return "phone"
    return None


def validate_new_pin(pin: object, phone: PhoneNumber | None = None, *, field: str = "pin") -> str:
    """Code accepté (renvoyé tel quel) ou erreur : `ValidationFailed` puis `PinTooSimple`."""
    checked = check_pin_format(pin, field)
    reason = pin_weakness(checked, phone)
    if reason is not None:
        raise PinTooSimple(reason)
    return checked


def password_weakness(password: str, phone: PhoneNumber | None = None) -> str | None:
    """Raison du refus d'un mot de passe, ou `None` s'il est accepté."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return "too_short"
    if len(password) > PASSWORD_MAX_LENGTH:
        return "too_long"
    if len(set(password)) < PASSWORD_MIN_DISTINCT:
        return "too_few_distinct"
    if password.casefold() in PASSWORD_BLOCKLIST:
        return "common"
    if phone is not None and phone.digits[-PASSWORD_PHONE_DIGITS:] in password:
        return "contains_phone"
    return None


def validate_new_password(
    password: object, phone: PhoneNumber | None = None, *, field: str = "password"
) -> str:
    """Mot de passe accepté (renvoyé tel quel) ou erreur typée."""
    if not isinstance(password, str):
        msg = "Le mot de passe doit être une chaîne"
        raise ValidationFailed(msg, details={"field": field})
    reason = password_weakness(password, phone)
    if reason is not None:
        raise PasswordTooWeak(reason, min_length=PASSWORD_MIN_LENGTH)
    return password
