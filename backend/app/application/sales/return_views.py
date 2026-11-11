"""Vues des retours pour l'acteur (TR-05, RG-D02) et de ce qu'il reste à rendre.

`show_costs` (`COST_READ`) est le seul interrupteur du présentateur : faux (vendeur), le coût
et la marge du retour et de ses lignes ne sont pas posés. Le comptable n'arrive pas jusqu'ici
(`SALE_READ` refusé, RG-D03). `balances` : par ligne de la vente, quantité vendue, déjà rendue
et encore rendable (EXC-02).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.domain.catalog.ids import ArticleId
from app.domain.sales.return_lines import already_returned
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import SaleReturn


@dataclass(frozen=True, slots=True)
class SaleReturnView:
    sale_return: SaleReturn
    show_costs: bool
    exchange: SaleView | None = None
    """Nouvelle vente d'un échange, à sa création seulement (`POST`)."""


@dataclass(frozen=True, slots=True)
class LineBalance:
    line: int
    article_id: ArticleId
    sold: Decimal
    returned: Decimal

    @property
    def returnable(self) -> Decimal:
        return self.sold - self.returned


@dataclass(frozen=True, slots=True)
class SaleReturnsListing:
    sale: Sale
    returns: list[SaleReturnView]
    balances: list[LineBalance]


def return_view(
    policy: Policy, actor: Actor, made: SaleReturn, exchange: SaleView | None = None
) -> SaleReturnView:
    return SaleReturnView(made, policy.can_read_field(actor, Permission.COST_READ), exchange)


def balances_of(sale: Sale, returns: list[SaleReturn]) -> list[LineBalance]:
    done = already_returned([line for made in returns for line in made.lines])
    return [
        LineBalance(
            line=position,
            article_id=line.article_id,
            sold=line.quantity,
            returned=done[position].quantity if position in done else Decimal(0),
        )
        for position, line in enumerate(sale.content.lines, start=1)
    ]
