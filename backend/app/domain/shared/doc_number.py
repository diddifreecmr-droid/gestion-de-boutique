"""Numéros de document (RG-T05, RG-T06, TR-10, specs § 6.5).

- Définitif : `<TYPE>-<séquence>` sur 6 chiffres au moins (`V-000124`) ; au-delà de 999 999 le
  numéro s'allonge sans erreur (`V-1000000`). L'attribution continue et sans trou relève du port
  `DocumentNumberAllocator` (infrastructure) ; ce module ne fait que formater et lire.
- Provisoire (saisie hors ligne) : `<TYPE>-HL-<code appareil>-<séquence>`, code = 4 chiffres
  hexadécimaux en majuscules, séquence sur 4 chiffres au moins (`V-HL-3F2A-0007`).

La lecture est stricte pour garantir l'aller-retour `parse(str(n)) == n` : un zéro de tête
au-delà de la largeur minimale (`V-0000124`) est refusé, comme une séquence nulle.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import DeviceId

FINAL_WIDTH = 6
PROVISIONAL_WIDTH = 4
PROVISIONAL_MARKER = "HL"


class DocType(StrEnum):
    SALE = "V"
    RECEIPT = "R"  # versement sur créance
    PURCHASE = "A"
    TRANSFER = "T"  # déplacement entre lieux
    EXPENSE = "D"
    TRIP = "VY"  # voyage
    INVENTORY = "INV"
    IMPORT = "IMP"


_TYPES = "|".join(sorted((t.value for t in DocType), key=len, reverse=True))
_FINAL = re.compile(rf"^(?P<type>{_TYPES})-(?P<seq>\d{{{FINAL_WIDTH}}}|[1-9]\d{{{FINAL_WIDTH},}})$")
_PROVISIONAL = re.compile(
    rf"^(?P<type>{_TYPES})-{PROVISIONAL_MARKER}-(?P<device>[0-9A-F]{{4}})"
    rf"-(?P<seq>\d{{{PROVISIONAL_WIDTH}}}|[1-9]\d{{{PROVISIONAL_WIDTH},}})$"
)
_DEVICE_CODE = re.compile(r"^[0-9A-F]{4}$")


def _invalid(text: str, expected: str) -> InvalidIdentifier:
    return InvalidIdentifier(
        "Numéro de document invalide", details={"value": text[:64], "expected": expected}
    )


def _require_sequence(sequence: object) -> None:
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        msg = f"La séquence doit être un int, reçu {type(sequence).__name__}"
        raise TypeError(msg)
    if sequence < 1:
        msg = "La séquence d'un numéro commence à 1"
        raise InvalidIdentifier(msg, details={"sequence": sequence})


@dataclass(frozen=True, slots=True)
class DocNumber:
    """Numéro définitif, attribué par le serveur (RG-T05)."""

    doc_type: DocType
    sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.doc_type, DocType):
            msg = f"doc_type doit être un DocType, reçu {self.doc_type!r}"
            raise TypeError(msg)
        _require_sequence(self.sequence)

    @classmethod
    def parse(cls, text: str) -> "DocNumber":
        match = _FINAL.fullmatch(text)
        if match is None:
            raise _invalid(text, "V-000124")
        return cls(DocType(match["type"]), int(match["seq"]))

    def __str__(self) -> str:
        return f"{self.doc_type.value}-{self.sequence:0{FINAL_WIDTH}d}"


@dataclass(frozen=True, slots=True)
class ProvisionalDocNumber:
    """Numéro provisoire attribué hors ligne par l'appareil (RG-T06)."""

    doc_type: DocType
    device_code: str
    sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.doc_type, DocType):
            msg = f"doc_type doit être un DocType, reçu {self.doc_type!r}"
            raise TypeError(msg)
        if not isinstance(self.device_code, str) or not _DEVICE_CODE.fullmatch(self.device_code):
            msg = "Code appareil attendu sur 4 chiffres hexadécimaux majuscules"
            raise InvalidIdentifier(msg, details={"device_code": str(self.device_code)[:16]})
        _require_sequence(self.sequence)

    @classmethod
    def for_device(
        cls, doc_type: DocType, device: DeviceId, sequence: int
    ) -> "ProvisionalDocNumber":
        """Code appareil = **4 derniers** chiffres hexadécimaux du `DeviceId`.

        Écart assumé avec specs § 6.5 (« 4 premiers ») : les premiers chiffres d'un UUIDv7 sont
        l'horodatage, identiques pour tous les appareils enregistrés à ~50 jours d'intervalle ;
        les derniers sont aléatoires.
        """
        return cls(doc_type, device.value.hex[-4:].upper(), sequence)

    @classmethod
    def parse(cls, text: str) -> "ProvisionalDocNumber":
        match = _PROVISIONAL.fullmatch(text)
        if match is None:
            raise _invalid(text, "V-HL-3F2A-0007")
        return cls(DocType(match["type"]), match["device"], int(match["seq"]))

    def __str__(self) -> str:
        return (
            f"{self.doc_type.value}-{PROVISIONAL_MARKER}-{self.device_code}"
            f"-{self.sequence:0{PROVISIONAL_WIDTH}d}"
        )


def parse_doc_number(text: str) -> DocNumber | ProvisionalDocNumber:
    """Lit indifféremment un numéro définitif ou provisoire (recherche, RG-T06)."""
    if _PROVISIONAL.fullmatch(text):
        return ProvisionalDocNumber.parse(text)
    if _FINAL.fullmatch(text):
        return DocNumber.parse(text)
    raise _invalid(text, "V-000124 ou V-HL-3F2A-0007")
