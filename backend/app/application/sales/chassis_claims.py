"""Châssis uniques parmi les ventes non annulées (RG-M01 ; ERR-DUP-01 à 03, SCN-06 étape 8).

- `sync_claims` : réserve les châssis de la vente qui ne le sont pas encore et libère ceux
  qu'elle ne porte plus (modification UC-VEN-07). Un châssis présent deux fois dans la vente
  → `DUPLICATE` sans `sale_number` (ERR-DUP-03) ; déjà réservé par une **autre** vente valide
  → `DUPLICATE` avec `sale_number` (« montre la vente concernée »).
- `release_claims` : annulation de la vente → tous ses châssis redeviennent libres.

Deux ventes simultanées du même châssis : la seconde écriture viole `sold_chassis_active`
(`Duplicate`) ; la transaction est rejouée (`with_sale_retry`) et reçoit alors l'erreur
détaillée ci-dessus.
"""

from app.application.ports.uow import UnitOfWork
from app.application.sales.ports import ChassisClaimRepository
from app.domain.sales.chassis import ChassisClaim
from app.domain.sales.errors import ChassisAlreadySold
from app.domain.sales.sale import Sale


def wanted_chassis(sale: Sale) -> dict[str, str]:
    """Clé normalisée → saisie, dans l'ordre des lignes ; doublon interne refusé."""
    found: dict[str, str] = {}
    for line in sale.content.lines:
        for detail in line.details:
            key, value = detail.chassis_key, detail.chassis_number
            if key is None or value is None:
                continue
            if key in found:
                raise ChassisAlreadySold(value, None)
            found[key] = value
    return found


def sync_claims(uow: UnitOfWork, sale: Sale) -> None:
    claims = ChassisClaimRepository.within(uow)
    wanted = wanted_chassis(sale)
    held = {claim.key: claim for claim in claims.for_sale(sale.id) if claim.active}
    for key, claim in held.items():
        if key not in wanted:
            claim.release()
            claims.update(claim)
    for key, value in wanted.items():
        if key in held:
            continue
        other = claims.find_active(key)
        if other is not None:
            raise ChassisAlreadySold(value, other.sale_number)
        claims.add(ChassisClaim.claim(uow.shop_id, value, sale.id, str(sale.number)))


def release_claims(uow: UnitOfWork, sale: Sale) -> None:
    claims = ChassisClaimRepository.within(uow)
    for claim in claims.for_sale(sale.id):
        if claim.active:
            claim.release()
            claims.update(claim)
