import { FileSpreadsheet } from "lucide-react";
import { EmptyState, ListCard, ListCardRow } from "../../shared/ui";
import type { ImportModel } from "./importModels";

export interface ModelChoiceProps {
  models: readonly ImportModel[];
  onChoose: (model: ImportModel) => void;
}

/** Étape 1 (design-system § 7.7) : un modèle par ligne, selon le rôle et les modules actifs. */
export function ModelChoice({ models, onChoose }: ModelChoiceProps) {
  if (models.length === 0) {
    return <EmptyState icon={FileSpreadsheet} message="Aucun modèle d'import pour votre rôle." />;
  }
  return (
    <>
      <p className="m-0 text-body text-text-muted">
        Choisissez ce que vous voulez reprendre depuis un fichier Excel.
      </p>
      <ListCard label="Modèles d'import">
        {models.map((model) => (
          <ListCardRow
            key={model.kind}
            title={model.label}
            subtitle={model.description}
            onOpen={() => {
              onChoose(model);
            }}
          />
        ))}
      </ListCard>
    </>
  );
}
