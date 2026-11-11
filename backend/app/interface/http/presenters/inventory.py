"""Présentation d'un inventaire (UC-STK-07, INV-01) : le théorique n'apparaît qu'après validation.

Tant que l'inventaire est en cours, aucune clé `theoretical`, `difference` ni `gap_value` n'est
posée (la ligne de domaine n'a d'ailleurs pas de théorique). `gap_value` exige les coûts.
"""

from typing import Any

from app.application.stock.use_cases.inventories import InventorySheet
from app.domain.stock.inventory import InventoryStatus
from app.domain.stock.inventory_line import InventoryLine
from app.interface.http.presenters.stock import amount
from app.interface.http.schemas.inventory import InventoryLineResponse, InventoryResponse


def sales_message(count: int) -> str | None:
    if count == 0:
        return None
    noun = "vente enregistrée" if count == 1 else "ventes enregistrées"
    return f"{count} {noun} depuis le début du comptage"


def _line(line: InventoryLine, name: str, *, settled: bool, costs: bool) -> InventoryLineResponse:
    extra: dict[str, Any] = {}
    if settled:
        difference = line.difference
        extra["theoretical"] = None if line.theoretical is None else str(line.theoretical)
        extra["difference"] = None if difference is None else str(difference)
        extra["reason"] = line.reason
        if costs:
            extra["gap_value"] = amount(line.gap_value)
    return InventoryLineResponse(
        article_id=str(line.article_id),
        display_name=name,
        stock_unit=line.unit.value,
        counted=None if line.counted is None else str(line.counted),
        **extra,
    )


def inventory_response(sheet: InventorySheet) -> InventoryResponse:
    inventory = sheet.inventory
    settled = inventory.status is InventoryStatus.VALIDATED
    costs = sheet.visibility.costs
    lines = sorted(
        inventory.lines.values(),
        key=lambda line: (sheet.article_names.get(line.article_id, ""), line.article_id),
    )
    extra: dict[str, Any] = {}
    if settled:
        extra["gap_count"] = len(inventory.gaps)
        if costs:
            extra["gap_value"] = amount(inventory.gap_value)
    return InventoryResponse(
        id=str(inventory.id),
        number=str(inventory.number),
        version=inventory.version,
        status=inventory.status.value,
        location_id=str(inventory.location_id),
        location_name=sheet.location_name,
        started_at=inventory.started_at,
        closed_at=inventory.closed_at,
        global_reason=inventory.global_reason,
        sales_since_start=sheet.sales_since_start,
        sales_message=sales_message(sheet.sales_since_start),
        counted_lines=sum(1 for line in lines if line.counted is not None),
        lines=[
            _line(line, sheet.article_names.get(line.article_id, "?"), settled=settled, costs=costs)
            for line in lines
        ],
        **extra,
    )
