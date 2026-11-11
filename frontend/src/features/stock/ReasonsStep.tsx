import type { Inventory } from "../../core/gateways/stockContract";
import { TextField } from "../../shared/ui";
import { ErrorText, WarningText } from "./Notice";

export interface ReasonsStepProps {
  inventory: Inventory;
  /** Articles en écart, désignés par le serveur (sans quantité théorique). */
  articleIds: readonly string[];
  reasons: Readonly<Record<string, string>>;
  globalReason: string;
  onReason: (articleId: string, text: string) => void;
  onGlobalReason: (text: string) => void;
  error: string | null;
}

/**
 * Motifs des écarts (UC-STK-07, étape 4 ; INV-03) : un motif par écart, ou un motif global
 * qui vaut pour tous les écarts sans motif propre.
 */
export function ReasonsStep(props: ReasonsStepProps) {
  const { inventory, articleIds, reasons, globalReason, onReason, onGlobalReason, error } = props;
  const name = (articleId: string) => {
    const line = inventory.lines.find((candidate) => candidate.article_id === articleId);
    if (line === undefined)
      throw new Error(`Écart sur un article absent de l'inventaire : ${articleId}`);
    return line.display_name;
  };
  return (
    <section aria-label="Motifs des écarts" className="flex flex-col gap-4">
      <h2 className="m-0 text-title-sm font-semibold text-text">Motifs des écarts</h2>
      <WarningText
        text={`${String(articleIds.length)} article(s) en écart : donnez un motif pour chacun, ou un motif global.`}
      />
      {articleIds.map((articleId) => (
        <TextField
          key={articleId}
          label={`Motif — ${name(articleId)}`}
          maxLength={500}
          value={reasons[articleId] ?? ""}
          onChange={(event) => {
            onReason(articleId, event.target.value);
          }}
        />
      ))}
      <TextField
        label="Motif global (pour tous les écarts)"
        maxLength={500}
        value={globalReason}
        onChange={(event) => {
          onGlobalReason(event.target.value);
        }}
      />
      {error !== null && <ErrorText text={error} />}
    </section>
  );
}
