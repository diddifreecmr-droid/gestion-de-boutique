/** Demandes de prix posées ou décidées directement dans le monde simulé (tests seulement). */
import type { PriceRequest } from "../core/gateways/salesContract";
import { PRICE_REQUEST_TTL_MS } from "../core/gateways/simulated/simulatedPriceRequests";
import { OWNER_ID, SELLER_ID, type SaleServer } from "./salesServer";

/** Demande en attente du vendeur (Haojue HJ125-8 à 700 000, minimum 720 000), faite maintenant. */
export function seedPriceRequest(
  server: SaleServer,
  overrides: Partial<PriceRequest> = {},
): PriceRequest {
  const now = Date.now();
  const request: PriceRequest = {
    id: `pr-${String(server.world.priceRequests.size + 1)}`,
    seller_id: SELLER_ID,
    article_id: "art-hj125-8",
    article_name: "Haojue HJ125-8",
    location_id: "loc-garoua",
    requested_price: 700_000,
    min_price: 720_000,
    status: "pending",
    requested_at: new Date(now).toISOString(),
    expires_at: new Date(now + PRICE_REQUEST_TTL_MS).toISOString(),
    decided_by: null,
    decided_at: null,
    sale_id: null,
    version: 1,
    ...overrides,
  };
  server.world.priceRequests.set(request.id, request);
  return request;
}

/** Réponse du propriétaire sur un autre téléphone : la seule demande du monde, décidée. */
export function ownerDecides(server: SaleServer, decision: "accepted" | "refused"): PriceRequest {
  const [request, ...others] = [...server.world.priceRequests.values()];
  if (request === undefined || others.length > 0) {
    throw new Error("ownerDecides : il faut exactement une demande dans le monde simulé");
  }
  const now = Date.now();
  const decided: PriceRequest = {
    ...request,
    status: decision,
    decided_by: OWNER_ID,
    decided_at: new Date(now).toISOString(),
    expires_at:
      decision === "accepted"
        ? new Date(now + PRICE_REQUEST_TTL_MS).toISOString()
        : request.expires_at,
    version: request.version + 1,
  };
  server.world.priceRequests.set(decided.id, decided);
  return decided;
}
