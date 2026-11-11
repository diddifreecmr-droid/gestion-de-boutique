"""Routes des clients (UC-VEN-11) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `GET /customers?q=` : recherche par nom ou téléphone (vendeur : ses clients seulement).
- `POST /customers` : 201, ou 200 si l'`id` client existe déjà ; téléphone pris → 409.
- `GET /customers/{id}` : fiche (client, ventes, total acheté, total dû) ;
  `PATCH /customers/{id}` (`version`). Comptable et chauffeur : 403 (RG-D03).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.security.actor import Actor
from app.domain.catalog.ids import AttachmentId
from app.domain.sales.ids import CustomerId
from app.domain.shared.errors import ValidationFailed
from app.interface.http.presenters.receipts import customer_response, sheet_response
from app.interface.http.routes.sales_components import SalesComponents
from app.interface.http.routes.sales_inputs import optional
from app.interface.http.schemas.customers import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerPatch,
    CustomerResponse,
    CustomerSheetResponse,
)

REQUIRED = frozenset({"name", "phone", "kind"})


def values_of(body: CustomerCreateRequest | CustomerPatch, names: set[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name in names:
        value = getattr(body, name)
        if name == "id_doc_photo_id":
            value = optional(AttachmentId, value)
        values[name] = value
    return values


def build_customers_router(sales: SalesComponents) -> APIRouter:
    router = APIRouter(tags=["customers"])
    Member = Annotated[Actor, Depends(sales.guard.current_actor)]  # noqa: N806
    customers = sales.customers

    @router.get("/shops/{shop_id}/customers")
    def search_customers(
        actor: Member, text: Annotated[str | None, Query(alias="q", max_length=100)] = None
    ) -> CustomerListResponse:
        found = customers.search(actor, text)
        return CustomerListResponse(items=[customer_response(c) for c in found])

    @router.post("/shops/{shop_id}/customers", status_code=status.HTTP_201_CREATED)
    def create_customer(
        actor: Member, body: CustomerCreateRequest, response: Response
    ) -> CustomerResponse:
        names = set(CustomerCreateRequest.model_fields) - {"id"}
        customer, created = customers.create(
            actor, values_of(body, names), optional(CustomerId, body.id)
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return customer_response(customer)

    @router.get("/shops/{shop_id}/customers/{customer_id}", response_model_exclude_unset=True)
    def get_customer(actor: Member, customer_id: str) -> CustomerSheetResponse:
        return sheet_response(customers.sheet(actor, CustomerId.parse(customer_id)))

    @router.patch("/shops/{shop_id}/customers/{customer_id}")
    def update_customer(actor: Member, customer_id: str, body: CustomerPatch) -> CustomerResponse:
        names = body.model_fields_set - {"version"}
        values = values_of(body, set(names))
        cleared = sorted(name for name in REQUIRED if name in values and values[name] is None)
        if cleared:
            msg = "Ce champ ne peut pas être vidé"
            raise ValidationFailed(msg, details={"fields": cleared})
        customer = customers.update(actor, CustomerId.parse(customer_id), values, body.version)
        return customer_response(customer)

    return router
