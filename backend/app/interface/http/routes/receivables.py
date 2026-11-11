"""Routes des créances (UC-CRE-01, 02, 04, 06, 07, 09) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `GET /receivables?status=&seller_id=&band=&reminder_overdue=&quiet=` : en tête (total à
  recevoir, clients débiteurs, versements du jour) et liste par reste décroissant.
- `POST /receivables` : créance ancienne (propriétaire ; 201, ou 200 au rejeu de l'`id`).
- `GET/PATCH /receivables/{id}` (`version` ; responsable : propriétaire seul),
  `POST /receivables/{id}/write-off {reason}` (propriétaire), `POST /receivables/{id}/reminders`,
  `PATCH /reminders/{id}`, `POST /receivables/{id}/guarantors`.

Vendeur : ses créances (vendeur responsable), sinon 404. Comptable, chauffeur : 403.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.receivables.use_cases.follow_up import ReminderChange
from app.application.receivables.use_cases.read_receivables import ReceivableCriteria
from app.application.receivables.use_cases.record_legacy import LegacyReceivableCommand
from app.application.sales.inputs import CustomerInput
from app.application.security.actor import Actor
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables.ids import GuarantorId, ReceivableId, ReminderId
from app.domain.receivables.values import ReceivableStatus, SeniorityBand
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.interface.http.presenters.receivables import listing_response, receivable_response
from app.interface.http.routes.receivables_components import ReceivablesComponents
from app.interface.http.routes.sales_inputs import customer_of, optional
from app.interface.http.schemas import receivables_requests as q
from app.interface.http.schemas.receivables import ReceivableListResponse, ReceivableResponse
from app.interface.http.schemas.sales_requests import SaleCustomerRequest


def customer_input(body: SaleCustomerRequest) -> CustomerInput:
    found = customer_of(body)
    if found is None:  # exclu par le type : défense en profondeur
        msg = "Client obligatoire"
        raise ValidationFailed(msg, details={"field": "customer"})
    return found


def patch_of(body: q.ReceivablePatch) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    sent = body.model_fields_set - {"version"}
    if "responsible_seller_id" in sent:
        patch["responsible_seller_id"] = optional(UserId, body.responsible_seller_id)
    if "terms" in sent:
        patch["terms"] = body.terms
    if "attachment_ids" in sent:
        patch["attachment_ids"] = tuple(AttachmentId.parse(a) for a in body.attachment_ids or ())
    return patch


def build_receivables_router(c: ReceivablesComponents) -> APIRouter:
    router = APIRouter(tags=["receivables"])
    Member = Annotated[Actor, Depends(c.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.get("/shops/{shop_id}/receivables", **sparse)
    def list_receivables(
        actor: Member,
        status_: Annotated[ReceivableStatus | None, Query(alias="status")] = None,
        seller_id: Annotated[str | None, Query(max_length=64)] = None,
        band: SeniorityBand | None = None,
        reminder_overdue: bool = False,
        quiet: bool = False,
    ) -> ReceivableListResponse:
        criteria = ReceivableCriteria(
            status=status_,
            seller_id=optional(UserId, seller_id),
            band=band,
            reminder_overdue=reminder_overdue,
            quiet=quiet,
        )
        return listing_response(c.list.execute(actor, criteria))

    @router.post("/shops/{shop_id}/receivables", status_code=status.HTTP_201_CREATED, **sparse)
    def record_legacy(
        actor: Member, body: q.LegacyReceivableRequest, response: Response
    ) -> ReceivableResponse:
        command = LegacyReceivableCommand(
            customer=customer_input(body.customer),
            amount=body.amount,
            opened_on=body.opened_on,
            description=body.description,
            responsible_seller_id=optional(UserId, body.responsible_seller_id),
            terms=body.terms,
            receivable_id=optional(ReceivableId, body.id),
        )
        view, created = c.record_legacy.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return receivable_response(view)

    @router.get("/shops/{shop_id}/receivables/{receivable_id}", **sparse)
    def get_receivable(actor: Member, receivable_id: str) -> ReceivableResponse:
        return receivable_response(c.get.execute(actor, ReceivableId.parse(receivable_id)))

    @router.patch("/shops/{shop_id}/receivables/{receivable_id}", **sparse)
    def change_receivable(
        actor: Member, receivable_id: str, body: q.ReceivablePatch
    ) -> ReceivableResponse:
        view = c.change.execute(
            actor, ReceivableId.parse(receivable_id), body.version, patch_of(body)
        )
        return receivable_response(view)

    @router.post("/shops/{shop_id}/receivables/{receivable_id}/write-off", **sparse)
    def write_off(actor: Member, receivable_id: str, body: q.ReasonRequest) -> ReceivableResponse:
        view = c.write_off.execute(actor, ReceivableId.parse(receivable_id), body.reason or "")
        return receivable_response(view)

    @router.post(
        "/shops/{shop_id}/receivables/{receivable_id}/reminders",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def schedule_reminder(
        actor: Member, receivable_id: str, body: q.ReminderRequest
    ) -> ReceivableResponse:
        view = c.schedule_reminder.execute(
            actor,
            ReceivableId.parse(receivable_id),
            body.remind_on,
            body.note,
            optional(ReminderId, body.id),
        )
        return receivable_response(view)

    @router.patch("/shops/{shop_id}/reminders/{reminder_id}", **sparse)
    def change_reminder(
        actor: Member, reminder_id: str, body: q.ReminderPatch
    ) -> ReceivableResponse:
        command = ReminderChange(
            reminder_id=ReminderId.parse(reminder_id),
            status=body.status,
            remind_on=body.remind_on,
            note=body.note,
        )
        return receivable_response(c.change_reminder.execute(actor, command))

    @router.post(
        "/shops/{shop_id}/receivables/{receivable_id}/guarantors",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def add_guarantor(
        actor: Member, receivable_id: str, body: q.GuarantorRequest
    ) -> ReceivableResponse:
        details: dict[str, Any] = body.model_dump(exclude={"id", "id_doc_photo_id"})
        details["id"] = optional(GuarantorId, body.id)
        details["id_doc_photo_id"] = optional(AttachmentId, body.id_doc_photo_id)
        view = c.add_guarantor.execute(actor, ReceivableId.parse(receivable_id), details)
        return receivable_response(view)

    return router
