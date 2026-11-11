"""Stock de départ de démonstration (**dev uniquement**) pour les six motos de `seed_catalog.py`.

Une « Reprise de départ » par modèle et par lieu, postée par le **vrai** grand livre
(`StockLedger.record_entry`, document lié : un lot d'import fictif), avec son coût unitaire.
Comme le fera l'import de stock (Lot 3), le coût de reprise devient le dernier coût et le CMP
de départ de l'article (`Article.record_costs`, sinon réservé aux Achats) : les écrans de
valeur du stock ont ainsi des chiffres. Appelé par `tools/seed_dev.py` à l'ouverture.
"""

from uuid import uuid4

from app.application.catalog.ports import ArticleRepository
from app.application.security.actor import Actor
from app.application.stock.ledger import StockLedger
from app.application.stock.postings import Posting
from app.application.stock.reading import all_articles, locations_by_id
from app.bootstrap.identity import IdentityModule
from app.domain.shared.doc_number import DocType
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.stock.values import MovementType, SourceRef, SourceType

OPENING = {
    "HJ125-8": (540_000, {"Garoua": 6, "Garoua-Boulaï": 14}),
    "DK150": (690_000, {"Garoua": 3, "Garoua-Boulaï": 5}),
    "Boxer BM150": (610_000, {"Garoua": 4, "Ngaoundéré": 2}),
    "HLX 125": (500_000, {"Garoua": 1}),
    "SL125-7": (450_000, {"Garoua": 5, "Garoua-Boulaï": 10}),
    "NF125-2": (430_000, {}),
}
"""Modèle → (coût unitaire de reprise, quantités par lieu). NF125-2 reste en rupture."""


def seed_opening_stock(identity: IdentityModule, owner: Actor) -> int:
    """Poste le stock de départ ; renvoie le nombre de mouvements créés."""
    if owner.shop_id is None:
        msg = "Stock de démonstration sans boutique"
        raise RuntimeError(msg)
    clock, ledger, created = identity.clock, StockLedger(identity.clock), 0
    with identity.core.shop_uow_factory(owner.shop_id) as uow:
        batch = SourceRef(SourceType.IMPORT, uuid4(), str(uow.numbering.next(DocType.IMPORT)))
        names = {loc.name: loc.id for loc in locations_by_id(uow).values()}
        articles = ArticleRepository.within(uow)
        for article in all_articles(uow):
            cost, quantities = OPENING.get(article.details.fields.model or "", (0, {}))
            for location, quantity in quantities.items():
                ledger.record_entry(
                    uow,
                    Posting(
                        article_id=article.id,
                        location_id=names[location],
                        type=MovementType.OPENING,
                        quantity=Quantity.of(quantity, article.details.fields.stock_unit),
                        source=batch,
                        occurred_at=clock.now(),
                        author_id=owner.user_id,
                        unit_cost=Money(cost),
                    ),
                )
                created += 1
            if quantities:
                article.record_costs(last_cost=Money(cost), wac=Money(cost))
                articles.update(article)
        uow.commit()
    return created
