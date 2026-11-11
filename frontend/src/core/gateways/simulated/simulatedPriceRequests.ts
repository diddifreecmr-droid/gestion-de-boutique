/**
 * Demandes d'accord de prix simulées (vitrine `/_ui` et faux serveur des tests) : mêmes règles
 * que T16b. Expiration 30 min après la demande, puis 30 min après l'accord ; statut lu
 * **effectif** à l'horloge ; usage unique ; couvre les lignes de son article à un prix ≥ prix
 * accordé, pour son vendeur. Sinon `PRICE_BELOW_MINIMUM` + `details.price_request`.
 * Seulement si la boutique exige l'accord (`world.settings`, faux par défaut) : sinon la vente
 * sous le minimum passe avec un avertissement et une demande → `PRICE_APPROVAL_DISABLED`.
 */
import { ApiError } from "../../api/errors";
import type { PriceRequest, RecordSaleCommand, SalesGateway, SaleWarning } from "../salesContract";
import { GAROUA } from "./seed";
import { reach, requireArticle, type World } from "./world";

export const PRICE_REQUEST_TTL_MS = 30 * 60_000;
/** Vendeur des demandes quand la simulation ne connaît pas l'utilisateur (vitrine). */
export const SIMULATED_SELLER = "sim-seller";

function effective(request: PriceRequest, now: number): PriceRequest {
  const open =
    request.status === "pending" || (request.status === "accepted" && request.sale_id === null);
  return open && now >= Date.parse(request.expires_at)
    ? { ...request, status: "expired" }
    : request;
}

function find(world: World, id: string): PriceRequest {
  const found = world.priceRequests.get(id);
  if (found === undefined) throw new ApiError(404, "NOT_FOUND", "Demande de prix introuvable");
  return effective(found, Date.now());
}

const userOf = (world: World, shopId: string) => world.options.userIn?.(shopId) ?? SIMULATED_SELLER;

type PriceRequestMethods = Pick<
  SalesGateway,
  "requestPriceApproval" | "listPriceRequests" | "getPriceRequest" | "decidePriceRequest"
>;

export function createSimulatedPriceRequests(world: World): PriceRequestMethods {
  return {
    async requestPriceApproval(shopId, command) {
      await reach(world);
      const article = requireArticle(world, command.article_id);
      const id = command.id ?? `pr-${String(world.priceRequests.size + 1)}`;
      const replay = world.priceRequests.get(id);
      if (replay !== undefined) return effective(replay, Date.now());
      if (!world.settings.minPriceRequiresApproval) {
        throw new ApiError(422, "PRICE_APPROVAL_DISABLED", "Accord du propriétaire non exigé", {
          setting: "min_price_requires_approval",
        });
      }
      if (command.requested_price >= article.min_price) {
        throw new ApiError(400, "VALIDATION_ERROR", "Aucune demande nécessaire", {
          field: "requested_price",
        });
      }
      const now = Date.now();
      const created: PriceRequest = {
        id,
        seller_id: userOf(world, shopId),
        article_id: article.id,
        article_name: article.name,
        location_id: GAROUA.id,
        requested_price: command.requested_price,
        min_price: article.min_price,
        status: "pending",
        requested_at: new Date(now).toISOString(),
        expires_at: new Date(now + PRICE_REQUEST_TTL_MS).toISOString(),
        decided_by: null,
        decided_at: null,
        sale_id: null,
        version: 1,
      };
      world.priceRequests.set(id, created);
      return created;
    },
    async listPriceRequests(shopId) {
      await reach(world);
      const now = Date.now();
      const all = [...world.priceRequests.values()].map((request) => effective(request, now));
      if (world.options.roleIn(shopId) === "owner") {
        return all.filter((request) => request.status === "pending");
      }
      return all.filter((request) => request.seller_id === userOf(world, shopId));
    },
    async getPriceRequest(_shopId, id) {
      await reach(world);
      return find(world, id);
    },
    async decidePriceRequest(shopId, id, decision, version) {
      await reach(world);
      if (world.options.roleIn(shopId) !== "owner") {
        throw new ApiError(403, "FORBIDDEN", "Réservé au propriétaire");
      }
      const current = find(world, id);
      if (current.status !== "pending") {
        throw new ApiError(409, "INVALID_STATE_TRANSITION", "Demande plus en attente", {
          status: current.status,
        });
      }
      if (current.version !== version) {
        throw new ApiError(409, "VERSION_CONFLICT", "Demande modifiée entre-temps");
      }
      const now = Date.now();
      const decided: PriceRequest = {
        ...current,
        status: decision === "accept" ? "accepted" : "refused",
        decided_by: userOf(world, shopId),
        decided_at: new Date(now).toISOString(),
        expires_at:
          decision === "accept"
            ? new Date(now + PRICE_REQUEST_TTL_MS).toISOString()
            : current.expires_at,
        version: current.version + 1,
      };
      world.priceRequests.set(id, decided);
      return decided;
    },
  };
}

/** Raison pour laquelle la demande jointe à la vente ne couvre pas la ligne, ou `null`. */
function problem(
  world: World,
  shopId: string,
  command: RecordSaleCommand,
  articleId: string,
  price: number,
): string | null {
  const id = command.price_request_id;
  const request = id === null || id === undefined ? undefined : world.priceRequests.get(id);
  if (request === undefined) return "not_found";
  if (request.seller_id !== userOf(world, shopId)) return "other_seller";
  if (request.sale_id !== null) return "used";
  const status = effective(request, Date.now()).status;
  if (status !== "accepted") return status;
  if (request.article_id !== articleId) return "other_article";
  return price < request.requested_price ? "price_too_low" : null;
}

/**
 * Vendeur sous le minimum : chaque ligne sous le minimum doit être couverte par la demande
 * jointe (UC-VEN-03). Rend vrai si la demande sert (elle sera alors consommée).
 */
export function checkApproval(world: World, shopId: string, command: RecordSaleCommand): boolean {
  if (world.options.roleIn(shopId) === "owner") return false;
  if (!world.settings.minPriceRequiresApproval) return false;
  const asked = command.price_request_id !== null && command.price_request_id !== undefined;
  let covered = false;
  command.lines.forEach((line, index) => {
    const article = requireArticle(world, line.article_id);
    if (line.unit_price >= article.min_price) return;
    const why = asked ? problem(world, shopId, command, article.id, line.unit_price) : null;
    covered = asked && why === null;
    if (covered) return;
    throw new ApiError(422, "PRICE_BELOW_MINIMUM", "Prix inférieur au minimum", {
      article_id: article.id,
      line: index + 1,
      min_price: article.min_price,
      request_required: true,
      ...(why === null ? {} : { price_request: why }),
    });
  });
  return covered;
}

/** Accord non exigé : un avertissement par ligne d'un vendeur sous le minimum (comme l'API). */
export function minimumWarnings(
  world: World,
  shopId: string,
  command: RecordSaleCommand,
): SaleWarning[] {
  if (world.options.roleIn(shopId) === "owner" || world.settings.minPriceRequiresApproval)
    return [];
  return command.lines.flatMap((line, index) => {
    const article = requireArticle(world, line.article_id);
    if (line.unit_price >= article.min_price) return [];
    const min = String(article.min_price).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return [
      {
        code: "PRICE_BELOW_MINIMUM",
        message: `Prix inférieur au minimum de ${min} FCFA`,
        details: { article_id: article.id, line: index + 1, min_price: article.min_price },
      },
    ];
  });
}

/** La vente enregistrée consomme la demande (usage unique). */
export function consumeApproval(world: World, command: RecordSaleCommand, saleId: string): void {
  const id = command.price_request_id;
  const request = id === null || id === undefined ? undefined : world.priceRequests.get(id);
  if (request !== undefined) world.priceRequests.set(request.id, { ...request, sale_id: saleId });
}
