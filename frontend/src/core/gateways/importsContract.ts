/**
 * Passerelle de l'import Excel (UC-IMP-01, UC-IMP-02, specs § 6.3) : l'écran dépend de cette
 * interface, jamais de `fetch`. Types issus du contrat **généré**.
 *
 * - `template` : `GET /imports/templates/{kind}` — modèle `.xlsx` du profil de la boutique.
 * - `preview` : `POST /imports/preview` (multipart `kind`, `file`) — aperçu **sans écriture**,
 *   gardé 30 minutes sous `preview_id`.
 * - `confirm` : `POST /imports` — écrit les lignes valides ; 201 (nouveau lot) ou 200 (même
 *   aperçu déjà confirmé : même lot) ; 410 `IMPORT_PREVIEW_EXPIRED` après 30 minutes.
 * - `list` / `detail` : `GET /imports`, `GET /imports/{id}` — lots passés (T45).
 * - `errors` : `GET /imports/{id}/errors.xlsx` — rapport d'erreurs du lot.
 * - `cancel` : `POST /imports/{id}/cancel` — annulation par archivage (propriétaire, 7 jours) ;
 *   422 `IMPORT_CANCEL_BLOCKED` (`details.blocking`), `IMPORT_CANCEL_TOO_LATE`,
 *   `INVALID_STATE_TRANSITION` (déjà annulé).
 *
 * Rien n'est avalé : `ApiError` et `NetworkError` remontent à l'écran, qui choisit le message.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type ImportKind = Schemas["ImportKind"];
export type ImportPreview = Schemas["ImportPreviewResponse"];
export type ImportProblem = Schemas["ImportProblemResponse"];
export type ImportBatch = Schemas["ImportBatchResponse"];
export type ImportBatchDetail = Schemas["ImportBatchDetailResponse"];
export type ImportedEntity = Schemas["ImportedEntity"];

export interface TemplateFile {
  blob: Blob;
  fileName: string;
}

export interface ImportsGateway {
  template(shopId: string, kind: ImportKind): Promise<TemplateFile>;
  preview(shopId: string, kind: ImportKind, file: File): Promise<ImportPreview>;
  confirm(shopId: string, previewId: string): Promise<ImportBatch>;
  list(shopId: string): Promise<ImportBatch[]>;
  detail(shopId: string, batchId: string): Promise<ImportBatchDetail>;
  errors(shopId: string, batchId: string): Promise<TemplateFile>;
  cancel(shopId: string, batchId: string): Promise<ImportBatch>;
}
