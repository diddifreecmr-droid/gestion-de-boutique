"""Tirage d'un code provisoire acceptable (H14, UC-SOC-01 étape 3, UC-SOC-04 étape 2).

Le code est tiré au hasard puis vérifié contre la politique (jamais un code simple, jamais la
fin du numéro). Il n'est renvoyé **qu'une fois**, à l'appelant qui le transmet ; seule son
empreinte est stockée.
"""

from app.application.identity.ports import TemporaryPinGenerator
from app.domain.identity.credentials import pin_weakness
from app.domain.identity.phone import PhoneNumber

MAX_DRAWS = 32
"""Tirages au plus avant d'abandonner (un code simple sort environ 1 fois sur 3 000)."""


def draw_temporary_pin(pins: TemporaryPinGenerator, phone: PhoneNumber) -> str:
    for _ in range(MAX_DRAWS):
        candidate = pins.generate()
        if pin_weakness(candidate, phone) is None:
            return candidate
    msg = f"Aucun code provisoire acceptable en {MAX_DRAWS} tirages : générateur défaillant"
    raise RuntimeError(msg)
