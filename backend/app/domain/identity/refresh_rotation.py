"""Verdict d'un jeton de rafraîchissement présenté (specs § 8.1, décision § 15.1 du 2026-11-13).

La rotation reste stricte, avec **une** tolérance : la réponse d'un rafraîchissement peut se
perdre (réseau mobile, rechargements rapides, onglet fermé pendant l'appel) ; le navigateur
garde alors l'ancien cookie. Ce jeton tout juste remplacé est accepté de nouveau pendant
`REFRESH_REPLAY_GRACE`, **depuis le même appareil**, et seulement s'il mène au successeur
actuel (le successeur se déduit du jeton présenté, voir `RefreshSecrets.successor`) : le
serveur renvoie alors ce même successeur, sans rien écrire. Hors de ces conditions, un jeton
périmé est une réutilisation : la session est révoquée et journalisée (SEC-R05).
"""

import hmac
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.shared.business_day import require_aware

REFRESH_REPLAY_GRACE = timedelta(seconds=30)
"""Durée pendant laquelle le jeton qui vient d'être remplacé reste rejouable (même appareil)."""


class RefreshVerdict(StrEnum):
    CURRENT = "current"
    """Jeton valide : rotation normale."""
    REPLAY = "replay"
    """Jeton tout juste remplacé, même appareil, dans la fenêtre : renvoyer le successeur."""
    REUSE = "reuse"
    """Jeton périmé (hors fenêtre, ou présenté par un autre appareil) : révoquer la session."""
    FOREIGN = "foreign"
    """Autre appareil sans preuve de possession d'un jeton de la session : refus simple."""


def _same(left: str | None, right: str) -> bool:
    return left is not None and hmac.compare_digest(left, right)


def judge_refresh(
    *,
    current_hash: str,
    previous_hash: str | None,
    rotated_at: datetime | None,
    presented_hash: str,
    successor_hash: str,
    same_device: bool,
    now: datetime,
) -> RefreshVerdict:
    """Comparaisons à temps constant ; `successor_hash` = empreinte du successeur déduit."""
    instant = require_aware(now)
    stale = _same(previous_hash, presented_hash)
    if not same_device:
        # Un jeton périmé présenté ailleurs prouve une copie du cookie : c'est un vol.
        return RefreshVerdict.REUSE if stale else RefreshVerdict.FOREIGN
    if hmac.compare_digest(current_hash, presented_hash):
        return RefreshVerdict.CURRENT
    in_window = rotated_at is not None and instant - rotated_at <= REFRESH_REPLAY_GRACE
    if stale and in_window and hmac.compare_digest(current_hash, successor_hash):
        return RefreshVerdict.REPLAY
    return RefreshVerdict.REUSE
