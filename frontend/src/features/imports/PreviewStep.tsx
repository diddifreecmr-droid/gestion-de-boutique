import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import type { ImportPreview } from "../../core/gateways/importsContract";
import { formatTime } from "../../shared/format";
import { Button, ListCard } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { CountLine, CountList } from "./CountLine";
import { NOTHING_VALID } from "./importErrors";
import { linesText } from "./importModels";

export const CONFIRM_LABEL = "Importer les lignes valides";
export const OTHER_FILE_LABEL = "Déposer un autre fichier";

export interface PreviewStepProps {
  preview: ImportPreview;
  fileName: string;
  confirming: boolean;
  failure: string | null;
  onConfirm: () => void;
  onOtherFile: () => void;
}

/**
 * Étape 3 : aperçu **sans écriture** (IMP-03, IMP-12) — lignes prêtes, lignes écartées,
 * éléments qui seront créés (`notes` du serveur), erreurs « Ligne 14 : le prix est vide ».
 * Aucune ligne valide : bouton désactivé avec la raison.
 */
export function PreviewStep(props: PreviewStepProps) {
  const { preview, fileName, confirming, failure, onConfirm, onOtherFile } = props;
  const hidden = preview.problems_total - preview.problems.length;
  return (
    <>
      <p className="m-0 text-body text-text-muted">
        Fichier « {fileName} » : {linesText(preview.rows_read)} lues. Rien n'est encore enregistré
        (aperçu valable jusqu'à {formatTime(preview.expires_at)}).
      </p>
      <CountList label="Bilan de l'aperçu">
        <CountLine tone="success">{`${linesText(preview.rows_valid)} prête${plural(preview.rows_valid)}`}</CountLine>
        {preview.rows_ignored > 0 && (
          <CountLine tone="danger">
            {`${linesText(preview.rows_ignored)} écartée${plural(preview.rows_ignored)}`}
          </CountLine>
        )}
        {preview.notes.map((note) => (
          <CountLine key={note} tone="muted">
            {note}
          </CountLine>
        ))}
      </CountList>
      {preview.problems.length > 0 && (
        <section aria-labelledby="import-errors" className="flex flex-col gap-2">
          <h2 id="import-errors" className="m-0 text-title-sm font-semibold text-text">
            Erreurs
          </h2>
          <ListCard label="Erreurs du fichier">
            {preview.problems.map((problem, index) => (
              <li
                key={`${String(problem.line)}-${String(index)}`}
                className="flex items-start gap-2 px-4 py-3 text-body text-danger-text"
              >
                <XCircle aria-hidden="true" className="size-6 shrink-0" />
                <span>{problem.text}</span>
              </li>
            ))}
          </ListCard>
          {hidden > 0 && (
            <p className="m-0 text-body text-text-muted">
              Et {hidden.toLocaleString("fr-FR")} autre{plural(hidden)} erreur{plural(hidden)} :
              corrigez d'abord celles-ci, puis déposez le fichier de nouveau.
            </p>
          )}
        </section>
      )}
      {failure !== null && <FormMessage text={failure} />}
      <Button
        size="lg"
        fullWidth
        icon={CheckCircle2}
        loading={confirming}
        {...(preview.rows_valid === 0 ? { disabledReason: NOTHING_VALID } : {})}
        onClick={onConfirm}
      >
        {CONFIRM_LABEL}
      </Button>
      <Button variant="ghost" icon={RotateCcw} onClick={onOtherFile}>
        {OTHER_FILE_LABEL}
      </Button>
    </>
  );
}

function plural(count: number): string {
  return count > 1 ? "s" : "";
}
