/**
 * Passerelle des pièces jointes (TR-17, RG-T26, UC-CRE-07) : l'écran dépend de cette
 * interface, jamais de `fetch`. Types issus du contrat **généré**.
 *
 * - `upload` : `POST /attachments` (multipart) ; un `id` client rend l'envoi rejouable
 *   (même `id` → même pièce, 200) après une coupure.
 * - `link` : `GET /attachments/{id}/url` ; lien **court** (60 s) vers le contenu, relayé par
 *   l'API (même origine) : à redemander à chaque affichage, jamais à garder.
 *
 * Droits (serveur) : ceux de l'élément lié ; pièce d'identité réservée au propriétaire et au
 * vendeur responsable (sinon 403 ou 404).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Attachment = Schemas["AttachmentResponse"];
export type AttachmentKind = Schemas["AttachmentKind"];
export type OwnerType = Schemas["OwnerType"];
export type FileFormat = Schemas["FileFormat"];
type Receivable = Schemas["ReceivableResponse"];

export interface UploadRequest {
  /** Identifiant UUIDv7 choisi par l'appareil (rejeu idempotent). */
  id: string;
  ownerType: OwnerType;
  /** Élément lié ; obligatoire pour un client (`customer`) ou une créance (`receivable`). */
  ownerId: string | null;
  kind: AttachmentKind;
  file: Blob;
  fileName: string;
}

export interface AttachmentLink {
  /** URL navigateur (balise `<img>`, ouverture d'un PDF), valable jusqu'à `expiresAt`. */
  url: string;
  expiresAt: Date;
  mime: FileFormat;
  kind: AttachmentKind;
}

export interface AttachmentsGateway {
  upload(shopId: string, request: UploadRequest): Promise<Attachment>;
  link(shopId: string, attachmentId: string): Promise<AttachmentLink>;
  /** Photo de la pièce d'identité du client : relit sa `version` puis `PATCH /customers/{id}`. */
  linkToCustomer(shopId: string, customerId: string, attachmentId: string): Promise<void>;
  /** Pièce ajoutée à la créance (UC-CRE-07) : relit la créance puis `PATCH attachment_ids`. */
  linkToReceivable(shopId: string, receivableId: string, attachmentId: string): Promise<Receivable>;
}
