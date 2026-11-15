"""Routes des tissus textiles `/shops/{id}/articles/fabrics` (décision client du 2026-11-15).

- `POST /articles/fabrics` (201) : tissu + couleurs → un article par couleur, une transaction.
- `PATCH /articles/fabrics/{fabric}` : prix, seuil, longueur du rouleau, « au mètre seulement »
  appliqués à toutes les couleurs.
- `POST /articles/fabrics/{fabric}/colors` (201) : nouvelles couleurs d'un tissu existant.

Lister ou regrouper : `GET /articles?fabric=<tissu>` (le nom « <Tissu> — <Couleur> » range
déjà les couleurs d'un tissu ensemble). Réponses présentées avec les droits de l'acteur.
"""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, status

from app.application.catalog.fabrics import FabricTerms, FabricView
from app.application.catalog.use_cases.create_fabric import (
    AddFabricColors,
    CreateFabric,
    CreateFabricCommand,
)
from app.application.catalog.use_cases.update_fabric import UpdateFabric
from app.application.security.actor import Actor
from app.domain.catalog.fabric import FabricShape
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.money import Money
from app.interface.http.presenters.catalog import article_response
from app.interface.http.schemas.fabrics import (
    FabricColorsRequest,
    FabricCreateRequest,
    FabricPatch,
    FabricPrices,
    FabricResponse,
)
from app.interface.http.security import AuthGuard

FabricName = Annotated[str, Path(min_length=1, max_length=60)]


@dataclass(frozen=True, slots=True, kw_only=True)
class FabricComponents:
    create: CreateFabric
    add_colors: AddFabricColors
    update: UpdateFabric
    guard: AuthGuard


def _prices(body: FabricPrices) -> ArticlePrices:
    def money(value: int | None) -> Money | None:
        return None if value is None else Money(value)

    return ArticlePrices(
        base_price=money(body.base_price),
        base_price_piece=money(body.base_price_piece),
        min_price=money(body.min_price),
        min_price_piece=money(body.min_price_piece),
    )


def _response(view: FabricView) -> FabricResponse:
    items = [
        article_response(
            article,
            view.visibility,
            min_price_enabled=view.min_price_enabled,
            shop_threshold=view.shop_threshold,
        )
        for article in view.articles
    ]
    return FabricResponse(fabric=view.fabric, items=items)


def _patch(body: FabricPatch) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    given = body.model_fields_set
    if "roll_length_m" in given:
        length = body.roll_length_m
        patch["piece_length_m"] = None if length is None else str(length)
    if "meter_only" in given and body.meter_only is not None:
        patch["sold_by_piece"] = not body.meter_only
    if "alert_threshold" in given:
        patch["alert_threshold"] = body.alert_threshold
    return patch


def build_fabric_router(fabrics: FabricComponents) -> APIRouter:
    router = APIRouter(tags=["catalog"])
    Member = Annotated[Actor, Depends(fabrics.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.post("/shops/{shop_id}/articles/fabrics", status_code=status.HTTP_201_CREATED, **sparse)
    def create_fabric(actor: Member, body: FabricCreateRequest) -> FabricResponse:
        prices = _prices(body)
        terms = FabricTerms(
            shape=FabricShape(roll_length_m=body.roll_length_m, meter_only=body.meter_only),
            alert_threshold=body.alert_threshold,
            prices=prices if prices.set_kinds() else None,
        )
        command = CreateFabricCommand(fabric=body.fabric, colors=tuple(body.colors), terms=terms)
        return _response(fabrics.create.execute(actor, command))

    @router.patch("/shops/{shop_id}/articles/fabrics/{fabric}", **sparse)
    def update_fabric(actor: Member, fabric: FabricName, body: FabricPatch) -> FabricResponse:
        prices = None if body.prices is None else _prices(body.prices)
        return _response(fabrics.update.execute(actor, fabric, _patch(body), prices))

    @router.post(
        "/shops/{shop_id}/articles/fabrics/{fabric}/colors",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def add_colors(actor: Member, fabric: FabricName, body: FabricColorsRequest) -> FabricResponse:
        return _response(fabrics.add_colors.execute(actor, fabric, tuple(body.colors)))

    return router
