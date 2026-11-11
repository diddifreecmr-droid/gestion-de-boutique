"""Routes de la synchronisation hors connexion (T23, specs § 6.5), sous `/shops/{shop_id}/…`.

- `POST /sync` `{device_id, operations: [...]}` → 200 `{results: [...]}` (un résultat par
  opération, dans l'ordre) ;
- `GET /offline-snapshot?since=` → instantané pour la saisie hors ligne (`Cache-Control:
  no-store`, comme toute réponse de l'API, specs § 7.3).

Les deux exigent le droit d'offre `offline_capture` : **403 `FEATURE_DISABLED` en V1** pour
toute boutique (offre gratuite) ; seule une surcharge de l'administrateur plateforme l'ouvre
(`PATCH /platform/shops/{id}` `{"entitlements": {"offline_capture": true}}`, recette ERR-FEA-04).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import AwareDatetime

from app.application.security.actor import Actor
from app.interface.http.presenters.sync import snapshot_response, sync_response
from app.interface.http.routes.sync_components import SyncComponents
from app.interface.http.routes.sync_inputs import PayloadDecoder, batch_of
from app.interface.http.schemas.sync import OfflineSnapshotResponse, SyncRequest, SyncResponse

NO_STORE = "no-store"


def build_sync_router(sync: SyncComponents) -> APIRouter:
    router = APIRouter(tags=["sync"])
    Member = Annotated[Actor, Depends(sync.guard.current_actor)]  # noqa: N806
    decoder = PayloadDecoder()

    @router.post("/shops/{shop_id}/sync")
    def synchronize(actor: Member, body: SyncRequest, response: Response) -> SyncResponse:
        response.headers["Cache-Control"] = NO_STORE
        return sync_response(sync.sync.execute(actor, batch_of(body), decoder))

    @router.get("/shops/{shop_id}/offline-snapshot")
    def offline_snapshot(
        actor: Member,
        response: Response,
        since: Annotated[AwareDatetime | None, Query()] = None,
    ) -> OfflineSnapshotResponse:
        response.headers["Cache-Control"] = NO_STORE
        return snapshot_response(sync.snapshot.execute(actor, since))

    return router
