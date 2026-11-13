/**
 * Passerelle de l'import Excel (UC-IMP-01, UC-IMP-02, specs § 6.3) : l'écran dépend de cette
 * interface, jamais de `fetch`. Types issus du contrat **généré**.
 *
 * - `template` : `GET /imports/templates/{kind}` — modèle `.xlsx` du profil de la boutique.
 * - `preview` : `POST /imports/preview` (multipart `kind`, `file`) — aperçu **sans écriture**,
 *   gardé 30 minutes sous `preview_id`.
 * - `confirm` : `POST /imports` — écrit les lignes valides ; 201 (nouveau lot) ou 200 (même
 *   aperçu déjà confirmé : même lot) ; 410 `IMPORT_PREVIEW_EXPIRED` après 30 minutes.
 *
 * Rien n'est avalé : `ApiError` et `NetworkError` remontent à l'écran, qui choisit le message.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type ImportKind = Schemas["ImportKind"];
export type ImportPreview = Schemas["ImportPreviewResponse"];
export type ImportProblem = Schemas["ImportProblemResponse"];
export type ImportBatch = Schemas["ImportBatchResponse"];
export type ImportedEntity = Schemas["ImportedEntity"];

export interface TemplateFile {
  blob: Blob;
  fileName: string;
}

export interface ImportsGateway {
  template(shopId: string, kind: ImportKind): Promise<TemplateFile>;
  preview(shopId: string, kind: ImportKind, file: File): Promise<ImportPreview>;
  confirm(shopId: string, previewId: string): Promise<ImportBatch>;
}
