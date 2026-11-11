"""Routes des fournisseurs (UC-ACH-02) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `GET /suppliers` (inactifs compris), `POST /suppliers` (201, ou 200 si l'`id` client existe
  déjà ; nom en double → 409 `DUPLICATE`), `PATCH /suppliers/{id}` (`version` ; désactiver :
  `active: false` — aucune route `DELETE`, RG-T02).
- `GET /suppliers/{id}?from=&to=` : fiche, achats et total acheté sur la période.

Vendeur et chauffeur : 403 ; fournisseur d'une autre boutique : 404.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.security.actor import Actor
from app.domain.purchasing.ids import SupplierId
from app.domain.purchasing.supplier import SupplierDetails
from app.domain.shared.errors import ValidationFailed
from app.interface.http.presenters.purchasing import sheet_response, supplier_response
from app.interface.http.routes.purchasing_components import PurchasingComponents
from app.interface.http.routes.purchasing_inputs import optional
from app.interface.http.schemas.purchasing import (
    SupplierListResponse,
    SupplierPatch,
    SupplierRequest,
    SupplierResponse,
    SupplierSheetResponse,
)


def build_suppliers_router(purchasing: PurchasingComponents) -> APIRouter:
    router = APIRouter(tags=["purchases"])
    Member = Annotated[Actor, Depends(purchasing.guard.current_actor)]  # noqa: N806
    suppliers = purchasing.suppliers

    @router.get("/shops/{shop_id}/suppliers")
    def list_suppliers(actor: Member) -> SupplierListResponse:
        return SupplierListResponse(items=[supplier_response(s) for s in suppliers.list_all(actor)])

    @router.post("/shops/{shop_id}/suppliers", status_code=status.HTTP_201_CREATED)
    def create_supplier(
        actor: Member, body: SupplierRequest, response: Response
    ) -> SupplierResponse:
        details = SupplierDetails(
            name=body.name, phone=body.phone, city=body.city, country=body.country, note=body.note
        )
        supplier, created = suppliers.create(actor, details, optional(SupplierId, body.id))
        if not created:
            response.status_code = status.HTTP_200_OK
        return supplier_response(supplier)

    @router.get("/shops/{shop_id}/suppliers/{supplier_id}")
    def supplier_sheet(
        actor: Member,
        supplier_id: str,
        first_day: Annotated[date | None, Query(alias="from")] = None,
        last_day: Annotated[date | None, Query(alias="to")] = None,
    ) -> SupplierSheetResponse:
        sheet = suppliers.sheet(actor, SupplierId.parse(supplier_id), first_day, last_day)
        return sheet_response(sheet)

    @router.patch("/shops/{shop_id}/suppliers/{supplier_id}")
    def update_supplier(actor: Member, supplier_id: str, body: SupplierPatch) -> SupplierResponse:
        patch = {name: getattr(body, name) for name in body.model_fields_set - {"version"}}
        if any(patch.get(name, "") is None for name in ("name", "active")):
            msg = "Ce champ ne peut pas être vidé"
            raise ValidationFailed(msg, details={"field": "name"})
        supplier = suppliers.update(actor, SupplierId.parse(supplier_id), patch, body.version)
        return supplier_response(supplier)

    return router
