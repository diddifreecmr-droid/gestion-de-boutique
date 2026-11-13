import { Download, Upload } from "lucide-react";
import { Button, FilePickerButton } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import type { ImportModel } from "./importModels";

/** Formats acceptés : Excel récent et CSV (un `.xls` est refusé par le serveur, IMP-05). */
export const ACCEPTED_FILES =
  ".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";
export const DROP_LABEL = "Déposer le fichier";
export const DOWNLOAD_LABEL = "Télécharger le modèle";

export interface FileStepProps {
  model: ImportModel;
  downloading: boolean;
  reading: boolean;
  failure: string | null;
  onDownload: () => void;
  onFile: (file: File) => void;
}

/** Étape 2 : télécharger le modèle (si besoin), le remplir, le déposer (.xlsx ou .csv). */
export function FileStep(props: FileStepProps) {
  const { model, downloading, reading, failure, onDownload, onFile } = props;
  return (
    <>
      <p className="m-0 text-body text-text-muted">
        Téléchargez le modèle « {model.label} », remplissez-le dans Excel, puis déposez-le ici :
        fichier .xlsx ou .csv, 5 000 lignes au plus. Rien n'est enregistré avant votre accord.
      </p>
      <Button variant="secondary" icon={Download} loading={downloading} onClick={onDownload}>
        {DOWNLOAD_LABEL}
      </Button>
      <FilePickerButton
        label={DROP_LABEL}
        accept={ACCEPTED_FILES}
        icon={Upload}
        variant="primary"
        loading={reading}
        onFile={onFile}
      />
      {failure !== null && <FormMessage text={failure} />}
    </>
  );
}
