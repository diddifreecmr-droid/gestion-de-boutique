import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import type { ImportBatch, ImportPreview } from "../../core/gateways/importsContract";
import { useImports } from "../../core/gateways/httpImports";
import { Button } from "../../shared/ui";
import { asError } from "../expenses/useLoad";
import { FileStep } from "./FileStep";
import { importFailure } from "./importErrors";
import type { ImportModel } from "./importModels";
import { ModelChoice } from "./ModelChoice";
import { PreviewStep } from "./PreviewStep";
import { ReportStep } from "./ReportStep";
import type { SaveFile } from "./saveFile";

type Stage =
  | { step: 1 }
  | { step: 2; model: ImportModel }
  | { step: 3; model: ImportModel; preview: ImportPreview; fileName: string }
  | { step: 4; model: ImportModel; batch: ImportBatch };

type Busy = "download" | "preview" | "confirm" | null;

export interface ImportsPageProps {
  shopId: string;
  models: readonly ImportModel[];
  save: SaveFile;
}

/**
 * Import Excel en 4 étapes sur un seul écran (design-system § 7.7, UC-IMP-01, UC-IMP-02) :
 * modèle → fichier → aperçu (aucune écriture) → rapport `IMP-…`. Aperçu expiré (410) ou devenu
 * inutilisable : retour au dépôt du fichier avec le message. Une erreur imprévue est relancée.
 */
export function ImportsPage({ shopId, models, save }: ImportsPageProps) {
  const gateway = useImports();
  const [stage, setStage] = useState<Stage>({ step: 1 });
  const [busy, setBusy] = useState<Busy>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const go = (next: Stage) => {
    setFailure(null);
    setStage(next);
  };

  const run = async (kind: Busy, work: () => Promise<void>, model: ImportModel) => {
    setBusy(kind);
    setFailure(null);
    try {
      await work();
    } catch (error) {
      try {
        const found = importFailure(error);
        if (found.restart) setStage({ step: 2, model });
        setFailure(found.text);
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(null);
    }
  };

  const title = stage.step === 1 ? "Import Excel" : `Import : ${stage.model.label}`;
  return (
    <>
      {stage.step > 1 && stage.step < 4 && (
        <Button variant="ghost" icon={ArrowLeft} onClick={() => go({ step: 1 })}>
          Changer de modèle
        </Button>
      )}
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      <p className="m-0 text-body text-text-muted">Étape {stage.step} sur 4</p>
      {stage.step === 1 && (
        <ModelChoice models={models} onChoose={(model) => go({ step: 2, model })} />
      )}
      {stage.step === 2 && (
        <FileStep
          model={stage.model}
          downloading={busy === "download"}
          reading={busy === "preview"}
          failure={failure}
          onDownload={() => {
            const { model } = stage;
            void run("download", async () => save(await gateway.template(shopId, model.kind)), model);
          }}
          onFile={(file) => {
            const { model } = stage;
            void run(
              "preview",
              async () => {
                const preview = await gateway.preview(shopId, model.kind, file);
                setStage({ step: 3, model, preview, fileName: file.name });
              },
              model,
            );
          }}
        />
      )}
      {stage.step === 3 && (
        <PreviewStep
          preview={stage.preview}
          fileName={stage.fileName}
          confirming={busy === "confirm"}
          failure={failure}
          onOtherFile={() => go({ step: 2, model: stage.model })}
          onConfirm={() => {
            const { model, preview } = stage;
            void run(
              "confirm",
              async () => {
                const batch = await gateway.confirm(shopId, preview.preview_id);
                setStage({ step: 4, model, batch });
              },
              model,
            );
          }}
        />
      )}
      {stage.step === 4 && <ReportStep batch={stage.batch} onAgain={() => go({ step: 1 })} />}
    </>
  );
}
