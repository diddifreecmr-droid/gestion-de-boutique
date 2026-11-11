"""Numéro de téléphone, identifiant de connexion unique sur la plateforme (H14, CDC § 20.1).

Normalisation retenue : **E.164** (`+<indicatif><numéro>`, chiffres seuls). C'est la forme
stockée, comparée et rendue unique ; deux saisies du même numéro donnent la même valeur.

- Séparateurs tolérés à la saisie et supprimés : espaces (y compris insécables), `.`, `-`,
  `(`, `)`.
- `+` ou `00` en tête : numéro international, 8 à 15 chiffres indicatif compris (E.164),
  premier chiffre non nul.
- Sans préfixe : numéro **camerounais**. 9 chiffres (plan national depuis 2014) → `+237…` ; la
  forme `237xxxxxxxxx` (12 chiffres) est aussi lue comme camerounaise.
- Indicatif 237 : exactement 9 chiffres nationaux, commençant par `6` (mobile) ou `2` (fixe).

Tout autre format → `ValidationFailed` (`details.field = "phone"`), sans écho de la saisie.
"""

import re
from dataclasses import dataclass

from app.domain.shared.errors import ValidationFailed

CAMEROON_CODE = "237"
CAMEROON_NATIONAL_LENGTH = 9
_SEPARATORS = re.compile(r"[\s.\-()]")  # \s couvre aussi l'espace insécable
_CAMEROON_NATIONAL = re.compile(r"^[26]\d{8}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def _invalid() -> ValidationFailed:
    return ValidationFailed("Numéro de téléphone invalide", details={"field": "phone"})


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    """Numéro normalisé en E.164 ; construire par `PhoneNumber.parse` depuis une saisie."""

    e164: str

    def __post_init__(self) -> None:
        if not isinstance(self.e164, str) or not _E164.fullmatch(self.e164):
            raise _invalid()
        if self.e164.startswith(f"+{CAMEROON_CODE}") and not _CAMEROON_NATIONAL.fullmatch(
            self.e164[1 + len(CAMEROON_CODE) :]
        ):
            raise _invalid()

    @classmethod
    def parse(cls, text: str) -> "PhoneNumber":
        if not isinstance(text, str):
            msg = f"Un numéro se lit depuis un str, reçu {type(text).__name__}"
            raise TypeError(msg)
        compact = _SEPARATORS.sub("", text)
        if compact.startswith("+"):
            return cls(compact)
        if compact.startswith("00"):
            return cls(f"+{compact[2:]}")
        if not compact.isascii() or not compact.isdigit():
            raise _invalid()
        if len(compact) == CAMEROON_NATIONAL_LENGTH:
            return cls(f"+{CAMEROON_CODE}{compact}")
        if len(compact) == len(CAMEROON_CODE) + CAMEROON_NATIONAL_LENGTH and compact.startswith(
            CAMEROON_CODE
        ):
            return cls(f"+{compact}")
        raise _invalid()

    @property
    def digits(self) -> str:
        """Chiffres sans le `+` (sert à refuser un code égal à la fin du numéro)."""
        return self.e164[1:]

    def __str__(self) -> str:
        return self.e164
